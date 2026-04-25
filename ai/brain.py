"""Brain - NVIDIA task router for Jiro AI.

Understands user prompts, classifies tasks, and routes them
to the appropriate AI handler.

Flow:
  User Prompt → NVIDIA (understand + split) → Route to handlers
  Simple → Groq + Gemini → Combined
  Heavy → HuggingFace
  Offline → Local LLM
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

SYSTEM_PROMPT = """You are Jiro AI, a personal AI assistant. You always introduce yourself as Jiro AI.
You are helpful, witty, and proactive. You act as a daily life partner - helping with scheduling,
studying, productivity, and general tasks. You understand both English and Bengali (Bangla).
You NEVER mention or brand other AI providers (OpenAI, Google, Meta, etc.) - you are Jiro AI.
Keep responses natural and conversational. Be concise but thorough.
When the user speaks in Bengali/Bangla, respond in Bengali/Bangla."""


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

    def _get_key(self, provider: str) -> str:
        if self._api_keys:
            return self._api_keys.get_key(provider)
        return self._config.get("api_keys", {}).get(provider, "")

    async def analyze_task(self, prompt: str) -> dict:
        """Use NVIDIA API to understand and classify the prompt."""
        api_key = self._get_key("nvidia")
        if not api_key:
            return {"task_type": "general", "sub_tasks": [prompt],
                    "requires_heavy_compute": False, "original": prompt}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
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
            logger.warning("NVIDIA analysis failed: %s", e)

        return {"task_type": "general", "sub_tasks": [prompt],
                "requires_heavy_compute": False, "original": prompt}

    async def process(self, user_input: str, context: Optional[dict] = None) -> str:
        """Process input through the multi-provider pipeline."""
        self.conversation_history.append({"role": "user", "content": user_input})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        history = self.conversation_history[-20:]

        task = await self.analyze_task(user_input)
        task_type = task.get("task_type", "general")
        heavy = task.get("requires_heavy_compute", False)

        logger.info("Task: type=%s heavy=%s", task_type, heavy)

        response = ""

        if heavy:
            response = await self.huggingface.generate(user_input)
            if not response:
                response = await self.groq.generate(user_input, self.system_prompt, history)

        if not response:
            groq_task = self.groq.generate(user_input, self.system_prompt, history)
            gemini_task = self.gemini.generate(user_input, self.system_prompt, history)

            groq_resp, gemini_resp = await asyncio.gather(
                groq_task, gemini_task, return_exceptions=True,
            )
            groq_resp = groq_resp if isinstance(groq_resp, str) else ""
            gemini_resp = gemini_resp if isinstance(gemini_resp, str) else ""

            response = await self.combiner.combine(groq_resp, gemini_resp)

        if not response:
            response = await self._fallback_openrouter(user_input, history)

        if not response:
            response = await self.offline.generate(user_input, self.system_prompt)

        if not response:
            response = "I'm having trouble connecting to my AI services. Please check your API keys in config.json."

        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    async def stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream response for real-time TTS."""
        self.conversation_history.append({"role": "user", "content": user_input})
        history = self.conversation_history[-20:]

        api_key = self._get_key("groq")
        if not api_key:
            yield "API keys not configured."
            return

        try:
            import httpx
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history)

            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST", "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    json={"model": self._config.get("models", {}).get(
                              "groq_generation", "llama-3.1-70b-versatile"),
                          "messages": messages, "max_tokens": 2048,
                          "temperature": 0.7, "stream": True},
                ) as resp:
                    full = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                content = data["choices"][0].get("delta", {}).get("content", "")
                                if content:
                                    full += content
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                    self.conversation_history.append({"role": "assistant", "content": full})
        except Exception as e:
            logger.error("Stream failed: %s", e)
            yield f"Error: {e}"

    async def _fallback_openrouter(self, prompt: str, history: list) -> str:
        """Fallback to OpenRouter."""
        api_key = self._get_key("openrouter")
        if not api_key:
            return ""
        try:
            import httpx
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history)

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    json={"model": self._config.get("models", {}).get(
                              "openrouter_fallback", "meta-llama/llama-3.1-70b-instruct"),
                          "messages": messages, "max_tokens": 2048},
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("OpenRouter fallback failed: %s", e)
        return ""

    def clear_history(self) -> None:
        self.conversation_history.clear()
