"""Groq API Handler - Fast AI responses."""

import logging
from typing import Optional

logger = logging.getLogger("jiro.ai.groq")


class GroqHandler:
    """Handles AI generation via Groq API (fast responses)."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager

    def _get_key(self) -> str:
        if self._api_keys:
            return self._api_keys.get_key("groq")
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
                logger.warning("Groq error %s", resp.status_code)
        except Exception as e:
            logger.error("Groq failed: %s", e)
        return ""
