"""Tab Controller - Auto close distracting tabs/windows.

Can close browser tabs or minimize windows that are categorized
as distractions when the user has been on them too long.
"""

import logging
import platform
import subprocess
from typing import Optional

logger = logging.getLogger("jiro.automation.tabs")


class TabController:
    """Controls browser tabs and windows for productivity."""

    def __init__(self, config: dict):
        self._config = config
        self._auto_close = config.get("monitoring", {}).get("auto_close_distractions", False)
        self._distraction_sites = config.get("monitoring", {}).get(
            "distraction_sites", [])

    def is_distraction(self, window_title: str) -> bool:
        title_lower = window_title.lower()
        return any(site in title_lower for site in self._distraction_sites)

    def close_active_tab(self) -> bool:
        """Close the currently active browser tab."""
        system = platform.system()
        try:
            if system == "Windows":
                import ctypes
                ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                ctypes.windll.user32.keybd_event(0x57, 0, 0, 0)  # W down
                ctypes.windll.user32.keybd_event(0x57, 0, 2, 0)  # W up
                ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                logger.info("Closed active tab")
                return True
            elif system == "Linux":
                subprocess.run(["xdotool", "key", "ctrl+w"], timeout=5)
                return True
        except Exception as e:
            logger.error("Failed to close tab: %s", e)
        return False

    def minimize_window(self) -> bool:
        """Minimize the currently active window."""
        system = platform.system()
        try:
            if system == "Windows":
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                ctypes.windll.user32.ShowWindow(hwnd, 6)
                return True
            elif system == "Linux":
                subprocess.run(["xdotool", "key", "super+d"], timeout=5)
                return True
        except Exception as e:
            logger.error("Failed to minimize: %s", e)
        return False

    async def handle_distraction(self, window_title: str, duration_seconds: float) -> Optional[str]:
        """Handle a detected distraction."""
        if not self._auto_close:
            threshold = self._config.get("monitoring", {}).get(
                "distraction_threshold_minutes", 15)
            if duration_seconds / 60 >= threshold:
                return (
                    f"You've been on '{window_title}' for "
                    f"{int(duration_seconds / 60)} minutes. "
                    f"Want me to close it? Say 'yes' or 'close it'."
                )
            return None

        threshold = self._config.get("monitoring", {}).get(
            "distraction_threshold_minutes", 15)
        if duration_seconds / 60 >= threshold:
            self.close_active_tab()
            return f"I closed '{window_title}' because you spent too long on it. Let's be productive!"

        return None
