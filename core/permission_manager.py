"""Permission Manager - First-time consent system for Jiro AI.

Asks for permissions once, saves them, and never asks again.
Manages consent for microphone, screen monitoring, activity tracking, etc.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.permissions")

PERMISSIONS_FILE = Path(__file__).parent.parent / "permissions.json"

REQUIRED_PERMISSIONS = {
    "microphone": {
        "description": "Access your microphone for voice commands",
        "required": True,
    },
    "screen_monitoring": {
        "description": "Monitor your active window for productivity tracking",
        "required": False,
    },
    "activity_tracking": {
        "description": "Track application usage patterns for insights",
        "required": False,
    },
    "screen_capture": {
        "description": "Take screenshots for context awareness",
        "required": False,
    },
    "notifications": {
        "description": "Show desktop notifications and reminders",
        "required": False,
    },
    "auto_start": {
        "description": "Start Jiro automatically when you log in",
        "required": False,
    },
    "file_access": {
        "description": "Read files (PDFs, documents) when you ask",
        "required": False,
    },
    "proactive_mode": {
        "description": "Jiro can talk to you without being asked (productivity tips, quizzes)",
        "required": False,
    },
}


class PermissionManager:
    """Manages user consent for Jiro AI features."""

    def __init__(self):
        self._permissions: dict = {}
        self._load()

    def _load(self) -> None:
        if PERMISSIONS_FILE.exists():
            try:
                with open(PERMISSIONS_FILE, "r") as f:
                    self._permissions = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._permissions = {}

    def _save(self) -> None:
        with open(PERMISSIONS_FILE, "w") as f:
            json.dump(self._permissions, f, indent=4)

    def is_granted(self, permission: str) -> bool:
        return self._permissions.get(permission, {}).get("granted", False)

    def grant(self, permission: str) -> None:
        self._permissions[permission] = {"granted": True}
        self._save()

    def deny(self, permission: str) -> None:
        self._permissions[permission] = {"granted": False}
        self._save()

    def has_been_asked(self, permission: str) -> bool:
        return permission in self._permissions

    def request_permission_cli(self, permission: str) -> bool:
        """Request a permission via CLI prompt."""
        info = REQUIRED_PERMISSIONS.get(permission, {})
        desc = info.get("description", permission)
        required = info.get("required", False)

        print(f"\n{'='*50}")
        print(f"  PERMISSION REQUEST: {permission}")
        print(f"  {desc}")
        if required:
            print("  (This permission is required for Jiro to work)")
        print(f"{'='*50}")

        while True:
            choice = input("  Grant permission? (y/n): ").strip().lower()
            if choice in ("y", "yes"):
                self.grant(permission)
                print(f"  [OK] {permission} granted.\n")
                return True
            elif choice in ("n", "no"):
                if required:
                    print("  [!] This permission is required. Jiro cannot start without it.")
                    continue
                self.deny(permission)
                print(f"  [--] {permission} denied.\n")
                return False
            else:
                print("  Please enter 'y' or 'n'.")

    def check_all_permissions(self, use_gui: bool = False) -> dict:
        """Check and request all permissions. Returns dict of granted permissions."""
        results = {}
        for perm, info in REQUIRED_PERMISSIONS.items():
            if not self.has_been_asked(perm):
                if use_gui:
                    granted = self._request_permission_gui(perm, info)
                else:
                    granted = self.request_permission_cli(perm)
                results[perm] = granted
            else:
                results[perm] = self.is_granted(perm)
        return results

    def _request_permission_gui(self, permission: str, info: dict) -> bool:
        """Request permission via GUI popup."""
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()

            desc = info.get("description", permission)
            required = info.get("required", False)
            title = f"Jiro AI - Permission: {permission}"
            msg = f"{desc}\n\n{'(Required for Jiro to work)' if required else '(Optional)'}"

            result = messagebox.askyesno(title, msg)
            root.destroy()

            if result:
                self.grant(permission)
            else:
                if not required:
                    self.deny(permission)
                else:
                    self.grant(permission)
            return result
        except Exception:
            return self.request_permission_cli(permission)

    def get_summary(self) -> str:
        lines = ["Jiro AI Permissions:"]
        for perm in REQUIRED_PERMISSIONS:
            status = "GRANTED" if self.is_granted(perm) else "DENIED"
            lines.append(f"  [{status}] {perm}")
        return "\n".join(lines)
