"""Gemini API Handler - Deep AI responses."""

import logging
from typing import Optional

logger = logging.getLogger("jiro.ai.gemini")


class GeminiHandler:
    """Handles AI generation via Google Gemini API (deep responses)."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager

    def _get_key(self) -> str:
        if self._api_keys:
            return self._api_keys.get_key("gemini")
        return self._config.get("api_keys", {}).get("gemini", "")

    async def generate(self, prompt: str, system_prompt: str = "",
                       history: Optional[list] = None) -> str:
        api_key = self._get_key()
        if not api_key:
            return ""

        try:
            import httpx
            history_text = ""
            if history:
                history_text = "\n".join(
                    f"{m['role']}: {m['content']}" for m in history[-20:]
                )

            full_prompt = f"{system_prompt}\n\n{history_text}\n\nUser: {prompt}" if system_prompt else prompt

            model = self._config.get("models", {}).get("gemini_generation", "gemini-2.0-flash")

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": api_key},
                    json={
                        "contents": [{"parts": [{"text": full_prompt}]}],
                        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                logger.warning("Gemini error %s", resp.status_code)
        except Exception as e:
            logger.error("Gemini failed: %s", e)
        return ""
