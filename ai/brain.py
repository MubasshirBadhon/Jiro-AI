"""Brain - Central AI orchestrator for Jiro AI.

Routes tasks to the best available AI provider with smart fallback.
Always maintains Jiro's identity - never reveals underlying APIs.
Uses API keys conservatively - caches, skips analysis for simple tasks.

Flow:
  Simple tasks → Local plugins (no API call)
  General → Single best provider (Groq OR Gemini, not both)
  Heavy/complex → Parallel Groq+Gemini → Combined
  Fallback → OpenRouter → Offline LLM
"""

import asyncio
import hashlib
import json
import logging
import time
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
        self._response_cache: dict[str, tuple[str, float]] = {}
        self._cache_ttl = 300  # 5 min cache
        self._api_call_count = 0
        self._api_call_reset = time.time()
        self._rate_limit_per_min = config.get("api", {}).get("rate_limit_per_min", 20)
        self._failed_tasks: list[dict] = []
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

    def _check_rate_limit(self) -> bool:
        """Check if we're within API rate limits. Returns True if OK to call."""
        now = time.time()
        if now - self._api_call_reset > 60:
            self._api_call_count = 0
            self._api_call_reset = now
        return self._api_call_count < self._rate_limit_per_min

    def _cache_key(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    def _get_cached(self, text: str) -> Optional[str]:
        """Get cached response if available and not expired."""
        key = self._cache_key(text)
        if key in self._response_cache:
            resp, ts = self._response_cache[key]
            if time.time() - ts < self._cache_ttl:
                logger.info("Cache hit - saved API call")
                return resp
            del self._response_cache[key]
        return None

    def _set_cache(self, text: str, response: str) -> None:
        self._response_cache[self._cache_key(text)] = (response, time.time())
        if len(self._response_cache) > 500:
            oldest = min(self._response_cache, key=lambda k: self._response_cache[k][1])
            del self._response_cache[oldest]

    def log_failed_task(self, task: str, error: str) -> None:
        """Log a failed task for self-improvement learning."""
        self._failed_tasks.append({
            "task": task, "error": error, "time": time.time(),
        })
        if len(self._failed_tasks) > 100:
            self._failed_tasks = self._failed_tasks[-50:]

    def get_failed_tasks(self) -> list[dict]:
        return self._failed_tasks

    def _is_simple_task(self, prompt: str) -> bool:
        """Check if a prompt is simple enough to skip NVIDIA analysis."""
        lower = prompt.lower().strip()
        simple_patterns = [
            "who are you", "what is your name", "hello", "hi", "hey",
            "thanks", "thank you", "bye", "good morning", "good night",
            "how are you", "what time", "what date", "ok", "yes", "no",
        ]
        if lower in simple_patterns or len(lower.split()) <= 3:
            return True
        return False

    async def analyze_task(self, prompt: str) -> dict:
        """Classify the prompt. Skips API for simple tasks to save quota."""
        default = {"task_type": "general", "sub_tasks": [prompt],
                    "requires_heavy_compute": False, "original": prompt}

        # Skip analysis for simple/short prompts
        if self._is_simple_task(prompt):
            return default

        # Check rate limit before API call
        if not self._check_rate_limit():
            logger.info("Rate limit reached, skipping NVIDIA analysis")
            return default

        api_key = self._get_key("nvidia")
        if not api_key:
            return default

        try:
            import httpx
            self._api_call_count += 1
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
        """Process input through the multi-provider pipeline with smart API usage.

        Smart API strategy for free tier:
        - Check cache first (avoid duplicate calls)
        - Use single provider for simple tasks (not parallel)
        - Only use parallel for complex/important queries
        - Track rate limits and back off when needed
        """
        # Check cache first
        cached = self._get_cached(user_input)
        if cached:
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": cached})
            return cached

        self.conversation_history.append({"role": "user", "content": user_input})
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        # Use limited history to save tokens
        history = self.conversation_history[-10:]

        # Skip NVIDIA analysis for simple tasks to save API calls
        is_simple = self._is_simple_task(user_input)
        if is_simple:
            task_type = "general"
            heavy = False
        else:
            task = await self.analyze_task(user_input)
            task_type = task.get("task_type", "general")
            heavy = task.get("requires_heavy_compute", False)

        logger.info("Task: type=%s heavy=%s simple=%s", task_type, heavy, is_simple)

        response = ""

        # Heavy tasks: try HuggingFace first
        if heavy and self._get_key("huggingface"):
            if self._check_rate_limit():
                self._api_call_count += 1
                response = await self.huggingface.generate(user_input)

        # Smart provider selection: use SINGLE provider for most tasks
        if not response:
            groq_key = self._get_key("groq")
            gemini_key = self._get_key("gemini")

            # For complex prompts (long, multi-part): try parallel if both available
            use_parallel = (not is_simple and len(user_input.split()) > 20
                           and groq_key and gemini_key and self._check_rate_limit())

            if use_parallel:
                try:
                    self._api_call_count += 2
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

            # Single provider for normal tasks (saves API quota)
            elif groq_key and self._check_rate_limit():
                self._api_call_count += 1
                response = await self.groq.generate(user_input, self.system_prompt, history)
            elif gemini_key and self._check_rate_limit():
                self._api_call_count += 1
                response = await self.gemini.generate(user_input, self.system_prompt, history)

        # Fallback: OpenRouter
        if not response and self._get_key("openrouter") and self._check_rate_limit():
            self._api_call_count += 1
            response = await self._openrouter_generate(user_input, history)

        # Last resort: Offline LLM (no API call needed)
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
                self.log_failed_task(user_input, "All providers failed")

        # Clean response of any AI branding
        response = self._clean_identity(response)

        # Cache the response
        self._set_cache(user_input, response)

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
