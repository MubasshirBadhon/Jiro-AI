"""HuggingFace API Handler - Heavy compute tasks."""

import logging
from typing import Optional

logger = logging.getLogger("jiro.ai.huggingface")


class HuggingFaceHandler:
    """Handles heavy compute tasks via HuggingFace API (image gen, etc.)."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager

    def _get_key(self) -> str:
        if self._api_keys:
            return self._api_keys.get_key("huggingface")
        return self._config.get("api_keys", {}).get("huggingface", "")

    async def generate(self, prompt: str, model: Optional[str] = None) -> str:
        api_key = self._get_key()
        if not api_key:
            return ""

        model = model or self._config.get("models", {}).get(
            "huggingface_heavy", "mistralai/Mistral-7B-Instruct-v0.3")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"inputs": prompt, "parameters": {"max_new_tokens": 1024}},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        return data[0].get("generated_text", str(data))
                    return str(data)
                logger.warning("HuggingFace error %s", resp.status_code)
        except Exception as e:
            logger.error("HuggingFace failed: %s", e)
        return ""

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """Generate an image using HuggingFace."""
        api_key = self._get_key()
        if not api_key:
            return None

        model = self._config.get("models", {}).get(
            "huggingface_image", "stabilityai/stable-diffusion-xl-base-1.0")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"inputs": prompt},
                )
                if resp.status_code == 200:
                    return resp.content
                logger.warning("Image gen error %s", resp.status_code)
        except Exception as e:
            logger.error("Image gen failed: %s", e)
        return None
