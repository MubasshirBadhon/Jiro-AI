"""API Key Prompter - Popup for new API keys when plugins need them.

When a new plugin requires an API key that isn't configured,
this module shows a prompt to collect it from the user.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.plugins.api_prompter")

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


class APIKeyPrompter:
    """Prompts user for missing API keys needed by plugins."""

    def __init__(self, config: dict):
        self._config = config

    def check_plugin_keys(self, plugin_info: dict) -> list[str]:
        """Check which required API keys are missing for a plugin."""
        required = plugin_info.get("requires_api_keys", [])
        configured = self._config.get("api_keys", {})
        return [k for k in required if not configured.get(k)]

    def prompt_cli(self, key_name: str, plugin_name: str) -> Optional[str]:
        """Prompt for an API key via CLI."""
        print(f"\n{'='*50}")
        print(f"  Plugin '{plugin_name}' needs API key: {key_name}")
        print(f"{'='*50}")
        key = input(f"  Enter {key_name} API key (or press Enter to skip): ").strip()
        if key:
            self._save_key(key_name, key)
            return key
        return None

    def prompt_gui(self, key_name: str, plugin_name: str) -> Optional[str]:
        """Prompt for an API key via GUI popup."""
        try:
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            key = simpledialog.askstring(
                f"API Key Required",
                f"Plugin '{plugin_name}' needs {key_name} API key:\n"
                f"(Leave empty to skip)",
                parent=root,
            )
            root.destroy()
            if key:
                self._save_key(key_name, key)
                return key
        except Exception:
            return self.prompt_cli(key_name, plugin_name)
        return None

    def _save_key(self, key_name: str, key: str) -> None:
        """Save the API key to config.json."""
        self._config.setdefault("api_keys", {})[key_name] = key
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=4)
        logger.info("API key '%s' saved to config.json", key_name)

    def check_all_plugins(self, plugins: list[dict], use_gui: bool = False) -> dict:
        """Check all plugins for missing API keys and prompt for them."""
        results = {}
        for plugin in plugins:
            missing = self.check_plugin_keys(plugin)
            for key_name in missing:
                if use_gui:
                    results[key_name] = self.prompt_gui(key_name, plugin["name"])
                else:
                    results[key_name] = self.prompt_cli(key_name, plugin["name"])
        return results
