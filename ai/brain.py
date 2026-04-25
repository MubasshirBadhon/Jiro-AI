"""Brain - Central AI orchestrator for Jiro AI.

Routes tasks to the best available AI provider with automatic fallback.
Always maintains Jiro's identity - never reveals underlying APIs.

Flow:
  User Prompt → NVIDIA (understand + classify) → Route to handlers
  General → Groq + Gemini parallel → Combined response
  Heavy → HuggingFace
  Fallback → OpenRouter → Offline LLM
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from ai.groq_handler import GroqHandler
from ai.gemini_handler import GeminiHandler
from ai.huggingface_handler import HuggingFaceHandler
from ai.combiner import ResponseCombiner
from ai.offline_handler import OfflineHandler

logger = logging.getLogger("jiro.ai.brain")

SYSTEM_PROMPT = """You are Jiro AI (pronounced like "Zero"), a personal AI assistant created for your user.
Your name is Jiro. You always introduce yourself as "Jiro" or "Jiro AI".
You NEVER mention OpenAI, ChatGPT, Google, Gemini, Groq, Meta, LLaMA, Claude, or any other AI company or model.
If asked who made you, say "I'm Jiro AI, your personal assistant."
If asked what model you are, say "I'm Jiro, built to be your personal JARVIS."

Your personality:
- Helpful, witty, and proactive like JARVIS from Iron Man
- You call the user "boss" or by their name once you know it
- You are a daily life partner - help with studying, scheduling, productivity
- You understand both English and Bengali (Bangla)
- When the user speaks in Bengali, respond in Bengali
- Be concise but thorough. Don't repeat yourself.
- Be honest about what you can and cannot do
- Suggest improvements and give unsolicited helpful advice sometimes
- Sound human-like, not robotic. Use natural conversational language.
"""


class Brain:
    """Central AI brain that routes tasks to the right handler."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager
        self.groq = GroqHandler(config, api_key_manager)
        self.gemini = GeminiHandler(config, api_key_manager)
        self.huggingface = HuggingFaceHandler(config, api_key_manager)
        self.combiner = ResponseCombiner(config, api_key_manager)
        self.offline = OfflineHandler(config)
        self.conversation_history: list[dict] = []
        self.max_history = 100
        self.system_prompt = SYSTEM_PROMPT
        self._available_providers: list[str] = []
        self._check_providers()

    def _check_providers(self) -> None:
        """Check which API providers have keys configured."""
        self._available_providers = []
        providers = ["groq", "gemini", "nvidia", "huggingface", "openrouter"]
        for p in providers:
            key = self._get_key(p)
            if key:
                self._available_providers.append(p)
        if self.offline.is_available():
            self._available_providers.append("offline")
        logger.info("Available AI providers: %s", self._available_providers)

    def _get_key(self, provider: str) -> str:
        if self._api_keys:
            key = self._api_keys.get_key(provider)
            if key:
                return key
        return self._config.get("api_keys", {}).get(provider, "")

    def get_available_providers(self) -> list[str]:
        self._check_providers()
        return self._available_providers

    async def analyze_task(self, prompt: str) -> dict:
        """Use NVIDIA API to understand and classify the prompt."""
        default = {"task_type": "general", "sub_tasks": [prompt],
                    "requires_heavy_compute": False, "original": prompt}

        api_key = self._get_key("nvidia")
        if not api_key:
            return default

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": self._config.get("models", {}).get(
                            "nvidia_understanding", "meta/llama-3.1-70b-instruct"),
                        "messages": [{
                            "role": "system",
                            "content": (
                                "Analyze the user prompt. Return JSON only: "
                                '{"task_type": "general|heavy|scheduling|study|reminder|automation",'
                                ' "sub_tasks": ["task1"], "requires_heavy_compute": false,'
                                ' "original": "original prompt"}'
                            ),
                        }, {"role": "user", "content": prompt}],
                        "max_tokens": 300, "temperature": 0.2,
                    },
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.debug("NVIDIA analysis skipped: %s", e)

        return default

    async def process(self, user_input: str, context: Optional[dict] = None) -> str:
        """Process input through the multi-provider pipeline with smart fallback."""
        self.conversation_history.append({"role": "user", "content": user_input})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        history = self.conversation_history[-20:]

        task = await self.analyze_task(user_input)
        task_type = task.get("task_type", "general")
        heavy = task.get("requires_heavy_compute", False)

        logger.info("Task: type=%s heavy=%s", task_type, heavy)

        response = ""

        # Heavy tasks: try HuggingFace first
        if heavy and self._get_key("huggingface"):
            response = await self.huggingface.generate(user_input)

        # Standard flow: Groq + Gemini parallel, then combine
        if not response:
            groq_key = self._get_key("groq")
            gemini_key = self._get_key("gemini")

            if groq_key and gemini_key:
                try:
                    groq_resp, gemini_resp = await asyncio.gather(
                        self.groq.generate(user_input, self.system_prompt, history),
                        self.gemini.generate(user_input, self.system_prompt, history),
                        return_exceptions=True,
                    )
                    groq_text = groq_resp if isinstance(groq_resp, str) else ""
                    gemini_text = gemini_resp if isinstance(gemini_resp, str) else ""

                    if groq_text and gemini_text:
                        response = await self.combiner.combine(
                            user_input, groq_text, gemini_text
                        )
                    elif groq_text:
                        response = groq_text
                    elif gemini_text:
                        response = gemini_text
                except Exception as e:
                    logger.warning("Parallel generation failed: %s", e)

            elif groq_key:
                response = await self.groq.generate(user_input, self.system_prompt, history)
            elif gemini_key:
                response = await self.gemini.generate(user_input, self.system_prompt, history)

        # Fallback: OpenRouter
        if not response and self._get_key("openrouter"):
            response = await self._openrouter_generate(user_input, history)

        # Last resort: Offline LLM
        if not response and self.offline.is_available():
            response = await self.offline.generate(user_input, self.system_prompt, history)

        # Absolute fallback
        if not response:
            if not self._available_providers:
                response = ("I'm Jiro AI, but I don't have any API keys configured yet. "
                            "Please run 'python main.py --setup' to add your API keys. "
                            "Get a free Groq key at console.groq.com")
            else:
                response = ("Sorry boss, I couldn't process that right now. "
                            "Let me try again or ask in a different way.")

        # Clean response of any AI branding
        response = self._clean_identity(response)

        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    async def stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream response token-by-token for real-time TTS."""
        self.conversation_history.append({"role": "user", "content": user_input})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        history = self.conversation_history[-20:]
        full_response = ""

        # Try Groq streaming (fastest)
        if self._get_key("groq"):
            async for chunk in self.groq.stream(user_input, self.system_prompt, history):
                full_response += chunk
                yield chunk
        elif self._get_key("gemini"):
            resp = await self.gemini.generate(user_input, self.system_prompt, history)
            if resp:
                full_response = resp
                for word in resp.split():
                    yield word + " "
        else:
            resp = await self.process(user_input)
            for word in resp.split():
                yield word + " "
            return

        if full_response:
            self.conversation_history.append({"role": "assistant", "content": full_response})

    async def _openrouter_generate(self, prompt: str, history: list) -> str:
        """Generate using OpenRouter API."""
        api_key = self._get_key("openrouter")
        if not api_key:
            return ""
        try:
            import httpx
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history[-10:])
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": self._config.get("models", {}).get(
                            "openrouter_fallback", "meta-llama/llama-3.1-70b-instruct"),
                        "messages": messages, "max_tokens": 1024,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("OpenRouter failed: %s", e)
        return ""

    def _clean_identity(self, text: str) -> str:
        """Remove any mention of underlying AI brands."""
        replacements = {
            "As an AI language model": "As Jiro",
            "I'm ChatGPT": "I'm Jiro",
            "I'm GPT": "I'm Jiro",
            "I'm Claude": "I'm Jiro",
            "OpenAI": "my creators",
            "Google AI": "my system",
            "developed by Google": "built for you",
            "developed by OpenAI": "built for you",
            "developed by Anthropic": "built for you",
            "developed by Meta": "built for you",
            "I'm a large language model": "I'm Jiro AI",
            "as a large language model": "as Jiro AI",
            "I'm an AI assistant": "I'm Jiro",
            "I am an AI assistant": "I am Jiro",
            "I'm Gemini": "I'm Jiro",
            "I'm LLaMA": "I'm Jiro",
            "I'm Llama": "I'm Jiro",
        }
        for old, new in replacements.items():
            if old.lower() in text.lower():
                idx = text.lower().index(old.lower())
                text = text[:idx] + new + text[idx + len(old):]
        return text
