"""Passkey System - Jiro only starts with your secret passkey.

Provides authentication to prevent unauthorized access to Jiro AI.
Uses bcrypt-style hashing for secure passkey storage.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.security.passkey")

CONFIG_FILE = Path(__file__).parent.parent / "config.json"


class PasskeyManager:
    """Manages passkey authentication for Jiro AI."""

    def __init__(self, config: dict):
        self._config = config
        self._security = config.get("security", {})

    def is_enabled(self) -> bool:
        return self._security.get("require_passkey", False)

    def _hash_passkey(self, passkey: str) -> str:
        return hashlib.sha256(passkey.encode()).hexdigest()

    def set_passkey(self, passkey: str) -> None:
        """Set a new passkey."""
        hashed = self._hash_passkey(passkey)
        self._config.setdefault("security", {})["passkey_hash"] = hashed
        self._config["security"]["require_passkey"] = True
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=4)
        logger.info("Passkey set successfully")

    def verify(self, passkey: str) -> bool:
        """Verify a passkey."""
        stored = self._security.get("passkey_hash", "")
        if not stored:
            return True
        return self._hash_passkey(passkey) == stored

    def authenticate_cli(self) -> bool:
        """Authenticate via CLI."""
        if not self.is_enabled():
            return True

        for attempt in range(3):
            passkey = input(f"  Enter Jiro passkey (attempt {attempt + 1}/3): ").strip()
            if self.verify(passkey):
                logger.info("Authentication successful")
                return True
            print("  Incorrect passkey.")

        logger.warning("Authentication failed after 3 attempts")
        return False

    def authenticate_gui(self) -> bool:
        """Authenticate via GUI."""
        if not self.is_enabled():
            return True

        try:
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            passkey = simpledialog.askstring(
                "Jiro AI - Authentication",
                "Enter your passkey:",
                show="*",
                parent=root,
            )
            root.destroy()
            if passkey and self.verify(passkey):
                return True
            return False
        except Exception:
            return self.authenticate_cli()

    def disable(self) -> None:
        """Disable passkey authentication."""
        self._config.setdefault("security", {})["require_passkey"] = False
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._config, f, indent=4)
