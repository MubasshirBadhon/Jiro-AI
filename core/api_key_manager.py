"""API Key Manager - Fetches and manages API keys from Supabase and local config.

Handles secure API key storage, retrieval from Supabase backend,
rotation, and validation. Smart key selection based on rate limits.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.api_keys")

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


class APIKeyManager:
    """Manages API keys from config.json and Supabase."""

    def __init__(self, config: dict):
        self._config = config
        self._keys: dict = config.get("api_keys", {})
        self._usage_count: dict = {}

    def get_key(self, provider: str) -> str:
        key = self._keys.get(provider, "")
        if key:
            self._usage_count[provider] = self._usage_count.get(provider, 0) + 1
        return key

    def set_key(self, provider: str, key: str, save: bool = True) -> None:
        self._keys[provider] = key
        self._config["api_keys"] = self._keys
        if save:
            self._save_config()

    def _save_config(self) -> None:
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=4)

    async def fetch_from_supabase(self) -> bool:
        """Fetch API keys from Supabase backend."""
        backend_url = self._config.get("supabase", {}).get("backend_url", "")
        anon_key = self._config.get("supabase", {}).get("anon_key", "")

        if not backend_url or not anon_key:
            logger.info("Supabase not configured, using local keys only")
            return False

        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{backend_url}/rest/v1/jiro_config",
                    headers={
                        "apikey": anon_key,
                        "Authorization": f"Bearer {anon_key}",
                    },
                    params={"select": "*", "limit": 1},
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        for key, val in data[0].items():
                            if key not in ("id", "created_at", "updated_at") and val:
                                self._keys[key] = val
                        logger.info("API keys loaded from Supabase")
                        return True
        except Exception as e:
            logger.warning("Supabase fetch failed: %s", e)
        return False

    async def validate_key(self, provider: str) -> dict:
        """Validate a single API key."""
        key = self.get_key(provider)
        if not key:
            return {"provider": provider, "status": "not_configured"}

        validators = {
            "groq": self._validate_groq,
            "gemini": self._validate_gemini,
            "nvidia": self._validate_nvidia,
            "huggingface": self._validate_hf,
            "openrouter": self._validate_openrouter,
        }

        validator = validators.get(provider)
        if validator:
            return await validator(key)
        return {"provider": provider, "status": "unknown"}

    async def validate_all(self) -> dict:
        """Validate all configured API keys."""
        import asyncio
        results = {}
        tasks = []
        providers = []
        for provider in self._keys:
            if self._keys[provider]:
                providers.append(provider)
                tasks.append(self.validate_key(provider))

        if tasks:
            done = await asyncio.gather(*tasks, return_exceptions=True)
            for provider, result in zip(providers, done):
                if isinstance(result, Exception):
                    results[provider] = {"status": "error", "message": str(result)}
                else:
                    results[provider] = result
        return results

    async def _validate_groq(self, key: str) -> dict:
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.groq.com/openai/v1/models",
                            headers={"Authorization": f"Bearer {key}"})
            ok = r.status_code == 200
            return {"provider": "groq", "status": "valid" if ok else "invalid"}

    async def _validate_gemini(self, key: str) -> dict:
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://generativelanguage.googleapis.com/v1beta/models",
                            params={"key": key})
            ok = r.status_code == 200
            return {"provider": "gemini", "status": "valid" if ok else "invalid"}

    async def _validate_nvidia(self, key: str) -> dict:
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post("https://integrate.api.nvidia.com/v1/chat/completions",
                             headers={"Authorization": f"Bearer {key}",
                                      "Content-Type": "application/json"},
                             json={"model": "meta/llama-3.1-8b-instruct",
                                   "messages": [{"role": "user", "content": "hi"}],
                                   "max_tokens": 5})
            ok = r.status_code == 200
            return {"provider": "nvidia", "status": "valid" if ok else "invalid"}

    async def _validate_hf(self, key: str) -> dict:
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://huggingface.co/api/whoami-v2",
                            headers={"Authorization": f"Bearer {key}"})
            ok = r.status_code == 200
            return {"provider": "huggingface", "status": "valid" if ok else "invalid"}

    async def _validate_openrouter(self, key: str) -> dict:
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://openrouter.ai/api/v1/models",
                            headers={"Authorization": f"Bearer {key}"})
            ok = r.status_code == 200
            return {"provider": "openrouter", "status": "valid" if ok else "invalid"}

    def get_available_providers(self) -> list:
        return [p for p, k in self._keys.items() if k]

    def get_usage_stats(self) -> dict:
        return dict(self._usage_count)
