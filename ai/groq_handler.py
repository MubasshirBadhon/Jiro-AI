"""Groq API Handler - Fast AI responses with streaming support."""

import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger("jiro.ai.groq")


class GroqHandler:
    """Handles AI generation via Groq API (fast responses + streaming)."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager

    def _get_key(self) -> str:
        if self._api_keys:
            key = self._api_keys.get_key("groq")
            if key:
                return key
        return self._config.get("api_keys", {}).get("groq", "")

    async def generate(self, prompt: str, system_prompt: str = "",
                       history: Optional[list] = None) -> str:
        api_key = self._get_key()
        if not api_key:
            return ""

        try:
            import httpx
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if history:
                messages.extend(history[-20:])
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": self._config.get("models", {}).get(
                            "groq_generation", "llama-3.1-70b-versatile"),
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                logger.warning("Groq error %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.error("Groq failed: %s", e)
        return ""

    async def stream(self, prompt: str, system_prompt: str = "",
                     history: Optional[list] = None) -> AsyncGenerator[str, None]:
        """Stream tokens for real-time TTS."""
        api_key = self._get_key()
        if not api_key:
            return

        try:
            import httpx
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if history:
                messages.extend(history[-20:])
            messages.append({"role": "user", "content": prompt})

            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": self._config.get("models", {}).get(
                            "groq_generation", "llama-3.1-70b-versatile"),
                        "messages": messages,
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "stream": True,
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk["choices"][0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except Exception:
                                continue
        except Exception as e:
            logger.error("Groq stream failed: %s", e)
