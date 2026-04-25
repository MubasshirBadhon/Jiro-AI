"""Response Combiner - Merges Groq + Gemini outputs for best quality."""

import logging
from typing import Optional

logger = logging.getLogger("jiro.ai.combiner")


class ResponseCombiner:
    """Combines responses from multiple AI providers for best quality."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager

    async def combine(self, response_a: str, response_b: str) -> str:
        """Combine two AI responses into one coherent response."""
        if response_a and response_b:
            if len(response_a) > len(response_b) * 2:
                return response_a
            if len(response_b) > len(response_a) * 2:
                return response_b

            api_key = ""
            if self._api_keys:
                api_key = self._api_keys.get_key("groq")
            if not api_key:
                api_key = self._config.get("api_keys", {}).get("groq", "")

            if api_key:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {api_key}",
                                     "Content-Type": "application/json"},
                            json={
                                "model": "llama-3.1-8b-instant",
                                "messages": [{
                                    "role": "user",
                                    "content": (
                                        "Combine these two AI responses into one natural response. "
                                        "Take the best parts. Keep it conversational. "
                                        "Respond as Jiro AI (never mention other AIs).\n\n"
                                        f"Response A:\n{response_a[:1500]}\n\n"
                                        f"Response B:\n{response_b[:1500]}"
                                    ),
                                }],
                                "max_tokens": 2048, "temperature": 0.5,
                            },
                        )
                        if resp.status_code == 200:
                            return resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    logger.warning("Combine failed, using best single: %s", e)

            return response_a if len(response_a) >= len(response_b) else response_b

        return response_a or response_b or ""
