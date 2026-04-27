"""Brain - Central AI orchestrator for Jiro AI.

LOCAL-FIRST architecture:
  1. Check cache
  2. Try offline LLM (no API call) for text-based tasks
  3. If offline fails -> Groq API (fastest free tier)
  4. If Groq fails -> Gemini API
  5. If Gemini fails -> HuggingFace (slow but capable)
  6. If all fail -> OpenRouter

API keys are ONLY used for:
  - Content generation when offline LLM can't handle it
  - Image generation
  - Research/summarization of complex topics
  - Code generation

Everything else runs locally first.
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from typing import AsyncGenerator, Optional

from ai.groq_handler import GroqHandler
from ai.gemini_handler import GeminiHandler
from ai.huggingface_handler import HuggingFaceHandler
from ai.combiner import ResponseCombiner
from ai.offline_handler import OfflineHandler

logger = logging.getLogger("jiro.ai.brain")

SYSTEM_PROMPT = """You are Jiro AI (pronounced like "Zero"), a personal AI assistant.
Your name is Jiro. You always introduce yourself as "Jiro" or "Jiro AI".
You NEVER mention OpenAI, ChatGPT, Google, Gemini, Groq, Meta, LLaMA, Claude, or any other AI company.
If asked who made you, say "I'm Jiro AI, your personal assistant."
If asked what model you are, say "I'm Jiro, built to be your personal JARVIS."

Your personality:
- Helpful, witty, and proactive like JARVIS from Iron Man
- You call the user "boss" or by their name once you know it
- English only - respond in English always
- Be concise but thorough
- Be honest about what you can and cannot do
- Suggest improvements and give unsolicited helpful advice sometimes
- Sound human-like, not robotic. Use natural conversational language.
"""


class Brain:
    """LOCAL-FIRST AI brain. Offline LLM first, APIs only as fallback."""

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
        self._response_cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl = 300
        self._api_call_count = 0
        self._api_call_reset = time.time()
        self._rate_limit_per_min = config.get("api", {}).get("rate_limit_per_min", 20)
        self._failed_tasks: list[dict] = []

    def _get_key(self, provider: str) -> str:
        if self._api_keys:
            key = self._api_keys.get_key(provider)
            if key:
                return key
        return self._config.get("api_keys", {}).get(provider, "")

    def get_available_providers(self) -> list[str]:
        providers = []
        if self.offline.is_available():
            providers.append("offline_llm")
        for p in ["groq", "gemini", "huggingface", "openrouter"]:
            if self._get_key(p):
                providers.append(p)
        return providers

    def _check_rate_limit(self) -> bool:
        now = time.time()
        if now - self._api_call_reset > 60:
            self._api_call_count = 0
            self._api_call_reset = now
        return self._api_call_count < self._rate_limit_per_min

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    def _get_cached(self, text: str) -> Optional[str]:
        key = self._cache_key(text)
        if key in self._response_cache:
            resp, ts = self._response_cache[key]
            if time.time() - ts < self._cache_ttl:
                logger.info("Cache hit")
                return resp
            del self._response_cache[key]
        return None

    def _set_cache(self, text: str, response: str) -> None:
        self._response_cache[self._cache_key(text)] = (response, time.time())
        if len(self._response_cache) > 500:
            oldest = min(self._response_cache, key=lambda k: self._response_cache[k][1])
            del self._response_cache[oldest]

    def log_failed_task(self, task: str, error: str) -> None:
        self._failed_tasks.append({
            "task": task, "error": error, "time": time.time(),
        })
        if len(self._failed_tasks) > 100:
            self._failed_tasks = self._failed_tasks[-50:]

    def get_failed_tasks(self) -> list[dict]:
        return self._failed_tasks

    def _is_simple_task(self, prompt: str) -> bool:
        """Check if prompt can be handled without any LLM."""
        lower = prompt.lower().strip()
        simple = [
            "who are you", "what is your name", "hello", "hi", "hey",
            "thanks", "thank you", "bye", "good morning", "good night",
            "how are you", "what time", "what date", "ok", "yes", "no",
            "help", "what can you do",
        ]
        return lower in simple or len(lower.split()) <= 2

    def _needs_api(self, prompt: str) -> bool:
        """Check if prompt needs API (content generation, research, images)."""
        lower = prompt.lower()
        api_indicators = [
            "generate", "create an image", "draw", "make an image",
            "research", "summarize this article", "write an essay",
            "write code", "generate code", "create a program",
            "translate", "explain in detail", "analyze this data",
            "write a story", "compose", "draft an email",
        ]
        return any(ind in lower for ind in api_indicators)

    async def process(self, user_input: str, context: Optional[dict] = None) -> str:
        """Process input with LOCAL-FIRST pipeline.

        Priority:
        1. Cache hit
        2. Simple greeting/identity -> hardcoded response
        3. Offline LLM (local, no API)
        4. Groq API (fast, free tier)
        5. Gemini API
        6. HuggingFace API
        7. OpenRouter API
        """
        # 1. Cache
        cached = self._get_cached(user_input)
        if cached:
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": cached})
            return cached

        self.conversation_history.append({"role": "user", "content": user_input})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        history = self.conversation_history[-10:]
        response = ""

        # 2. Simple tasks - no LLM needed at all
        if self._is_simple_task(user_input):
            response = self._handle_simple(user_input)

        # 3. Try offline LLM FIRST (local processing, no API call)
        if not response and self.offline.is_available():
            try:
                logger.info("Trying offline LLM first...")
                response = await self.offline.generate(
                    user_input, self.system_prompt, history
                )
                if response and len(response.strip()) > 5:
                    logger.info("Offline LLM handled it locally")
                else:
                    response = ""
            except Exception as e:
                logger.warning("Offline LLM failed: %s", e)
                response = ""

        # 4. If offline failed or task needs API -> use API providers
        if not response:
            response = await self._try_api_providers(user_input, history)

        # Absolute fallback
        if not response:
            providers = self.get_available_providers()
            if not providers:
                response = ("I'm Jiro AI, but I don't have any AI models available. "
                            "Either download an offline model with 'download model' or "
                            "run 'python main.py --setup' to add API keys. "
                            "Get a free Groq key at console.groq.com")
            else:
                response = ("Sorry boss, I couldn't process that right now. "
                            "Let me try again or ask in a different way.")
                self.log_failed_task(user_input, "All providers failed")

        response = self._clean_identity(response)
        self._set_cache(user_input, response)
        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    async def _try_api_providers(self, prompt: str, history: list) -> str:
        """Try API providers in order: Groq -> Gemini -> HuggingFace -> OpenRouter."""
        # Groq (fastest free tier)
        if self._get_key("groq") and self._check_rate_limit():
            try:
                self._api_call_count += 1
                resp = await self.groq.generate(prompt, self.system_prompt, history)
                if resp:
                    return resp
            except Exception as e:
                logger.warning("Groq failed: %s", e)

        # Gemini
        if self._get_key("gemini") and self._check_rate_limit():
            try:
                self._api_call_count += 1
                resp = await self.gemini.generate(prompt, self.system_prompt, history)
                if resp:
                    return resp
            except Exception as e:
                logger.warning("Gemini failed: %s", e)

        # HuggingFace
        if self._get_key("huggingface") and self._check_rate_limit():
            try:
                self._api_call_count += 1
                resp = await self.huggingface.generate(prompt)
                if resp:
                    return resp
            except Exception as e:
                logger.warning("HuggingFace failed: %s", e)

        # OpenRouter
        if self._get_key("openrouter") and self._check_rate_limit():
            try:
                self._api_call_count += 1
                resp = await self._openrouter_generate(prompt, history)
                if resp:
                    return resp
            except Exception as e:
                logger.warning("OpenRouter failed: %s", e)

        return ""

    def _handle_simple(self, prompt: str) -> str:
        """Handle simple tasks without any LLM."""
        lower = prompt.lower().strip()
        if lower in ("who are you", "what is your name"):
            return "I'm Jiro AI, your personal assistant. Think of me as your JARVIS, boss."
        if lower in ("hello", "hi", "hey"):
            return "Hey boss! What can I do for you?"
        if lower in ("how are you",):
            return "I'm running great, boss. What do you need?"
        if lower in ("thanks", "thank you"):
            return "Anytime, boss!"
        if lower in ("bye", "goodbye"):
            return "See you later, boss. I'll be here when you need me."
        if lower in ("good morning",):
            return "Good morning, boss! Ready to make today productive?"
        if lower in ("good night",):
            return "Good night, boss! Get some rest."
        if lower in ("help", "what can you do"):
            return (
                "I'm Jiro AI. Here's what I can do:\n"
                "- Answer questions (locally or via AI)\n"
                "- Create files (doc, pdf, ppt), folders\n"
                "- Run system commands (cmd, powershell)\n"
                "- Analyze screenshots and PDFs\n"
                "- Set alarms and reminders\n"
                "- Track your schedule and habits\n"
                "- Help with studying (flashcards, quizzes)\n"
                "- Open URLs and apps\n"
                "- And much more with 69+ plugins!\n\n"
                "Just ask me anything, boss."
            )
        return ""

    async def stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Stream response for real-time TTS. Local first, API fallback."""
        self.conversation_history.append({"role": "user", "content": user_input})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        history = self.conversation_history[-20:]
        full_response = ""

        # Simple tasks - yield immediately
        if self._is_simple_task(user_input):
            resp = self._handle_simple(user_input)
            if resp:
                full_response = resp
                for word in resp.split():
                    yield word + " "
                self.conversation_history.append({"role": "assistant", "content": full_response})
                return

        # Try offline LLM first
        if self.offline.is_available():
            try:
                resp = await self.offline.generate(user_input, self.system_prompt, history)
                if resp and len(resp.strip()) > 5:
                    full_response = self._clean_identity(resp)
                    for word in full_response.split():
                        yield word + " "
                    self.conversation_history.append({"role": "assistant", "content": full_response})
                    return
            except Exception:
                pass

        # Groq streaming (fastest API)
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
            full_response = self._clean_identity(full_response)
            self.conversation_history.append({"role": "assistant", "content": full_response})

    async def _openrouter_generate(self, prompt: str, history: list) -> str:
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
            "I'm ChatGPT": "I'm Jiro", "I'm GPT": "I'm Jiro",
            "I'm Claude": "I'm Jiro", "I am ChatGPT": "I am Jiro",
            "I am Claude": "I am Jiro", "I am GPT": "I am Jiro",
            "OpenAI": "my creators", "Google AI": "my system",
            "Anthropic": "my system",
            "developed by Google": "built for you",
            "developed by OpenAI": "built for you",
            "developed by Anthropic": "built for you",
            "developed by Meta": "built for you",
            "created by Google": "created for you",
            "created by OpenAI": "created for you",
            "created by Meta": "created for you",
            "made by Google": "made for you", "made by OpenAI": "made for you",
            "I'm a large language model": "I'm Jiro AI",
            "I am a large language model": "I am Jiro AI",
            "as a large language model": "as Jiro AI",
            "I'm an AI assistant": "I'm Jiro",
            "I am an AI assistant": "I am Jiro",
            "I'm an AI": "I'm Jiro AI", "I am an AI": "I am Jiro AI",
            "I'm Gemini": "I'm Jiro", "I'm LLaMA": "I'm Jiro",
            "I'm Llama": "I'm Jiro", "I'm Meta AI": "I'm Jiro",
            "Meta AI": "Jiro AI",
        }
        for old, new in replacements.items():
            text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
        return text
