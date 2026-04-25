"""Configuration manager for Jiro AI. Loads config from config.json and Supabase."""

import json
import os
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jiro.config")

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


class ConfigManager:
    """Manages Jiro AI configuration from config.json and remote Supabase."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self._config: dict = {}
        self._supabase_client = None
        self.load()

    def load(self) -> dict:
        """Load configuration from config.json."""
        if not self.config_path.exists():
            logger.error("Config file not found: %s", self.config_path)
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

        logger.info("Configuration loaded from %s", self.config_path)
        return self._config

    def save(self) -> None:
        """Save current configuration to config.json."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)
        logger.info("Configuration saved to %s", self.config_path)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot notation (e.g., 'api_keys.groq')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Set a config value using dot notation."""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value

        if persist:
            self.save()

    def get_api_key(self, provider: str) -> str:
        """Get API key for a specific provider."""
        key = self.get(f"api_keys.{provider}", "")
        if not key:
            logger.warning("API key for '%s' is not configured", provider)
        return key

    def get_model(self, purpose: str) -> str:
        """Get model name for a specific purpose."""
        return self.get(f"models.{purpose}", "")

    async def load_from_supabase(self) -> None:
        """Load API keys and config from Supabase backend."""
        backend_url = self.get("supabase.backend_url")
        anon_key = self.get("supabase.anon_key")

        if not backend_url or not anon_key:
            logger.info("Supabase not configured, using local config only")
            return

        try:
            import httpx
            async with httpx.AsyncClient() as client:
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
                        remote_config = data[0]
                        for key, val in remote_config.items():
                            if key not in ("id", "created_at", "updated_at"):
                                self.set(f"api_keys.{key}", val, persist=False)
                        logger.info("API keys loaded from Supabase")
                else:
                    logger.warning("Failed to load from Supabase: %s", response.status_code)
        except Exception as e:
            logger.warning("Supabase connection failed: %s", e)

    @property
    def config(self) -> dict:
        return self._config
