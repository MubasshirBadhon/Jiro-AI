"""Screen Monitor for Jiro AI.

Tracks active windows and takes periodic screenshots for context awareness.
Provides productivity insights and enables proactive assistance.
"""

import asyncio
import json
import logging
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("jiro.monitoring.screen")

SCREENSHOTS_DIR = Path(__file__).parent.parent / "data" / "recordings" / "screenshots"


class ScreenMonitor:
    """Monitors active windows and screen content for productivity tracking."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.enabled = config_manager.get("monitoring.enabled", True)
        self.interval = config_manager.get("monitoring.screenshot_interval_seconds", 30)
        self.is_running = False
        self._current_window = ""
        self._window_start_time = time.time()
        self._activity_callbacks: list[Callable] = []
        self._last_window_log: dict = {}

    def add_activity_callback(self, callback: Callable) -> None:
        """Register a callback for activity changes."""
        self._activity_callbacks.append(callback)

    def get_active_window(self) -> str:
        """Get the currently active window title."""
        system = platform.system()

        try:
            if system == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value

            elif system == "Linux":
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=5,
                )
                return result.stdout.strip()

            elif system == "Darwin":
                script = '''
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    return frontApp
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True, text=True, timeout=5,
                )
                return result.stdout.strip()

        except Exception as e:
            logger.debug("Failed to get active window: %s", e)

        return "Unknown"

    def _categorize_window(self, title: str) -> str:
        """Categorize a window title for productivity tracking."""
        title_lower = title.lower()

        productive_keywords = [
            "vscode", "visual studio", "pycharm", "intellij",
            "terminal", "cmd", "powershell", "jupyter",
            "docs.google", "notion", "obsidian",
            "stack overflow", "github", "gitlab",
        ]

        distraction_keywords = self.config.get("monitoring.distraction_sites", [])

        study_keywords = [
            "khan academy", "coursera", "udemy", "edx",
            "arxiv", "wikipedia", "research",
        ]

        if any(kw in title_lower for kw in productive_keywords):
            return "productive"
        elif any(kw in title_lower for kw in distraction_keywords):
            return "distraction"
        elif any(kw in title_lower for kw in study_keywords):
            return "study"
        else:
            return "neutral"

    async def take_screenshot(self) -> Optional[str]:
        """Take a screenshot and save it."""
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = SCREENSHOTS_DIR / f"screen_{timestamp}.png"

        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=str(filepath))
            return str(filepath)
        except ImportError:
            try:
                subprocess.run(
                    ["scrot", str(filepath)],
                    capture_output=True, timeout=10,
                )
                if filepath.exists():
                    return str(filepath)
            except FileNotFoundError:
                pass
        except Exception as e:
            logger.debug("Screenshot failed: %s", e)

        return None

    async def monitor_loop(self, on_activity_change: Optional[Callable] = None) -> None:
        """Main monitoring loop - tracks active window changes."""
        self.is_running = True
        logger.info("Screen monitoring started (interval: %ds)", self.interval)

        while self.is_running:
            try:
                current = self.get_active_window()

                if current != self._current_window:
                    elapsed = time.time() - self._window_start_time
                    if self._current_window and elapsed > 1:
                        self._last_window_log = {
                            "window": self._current_window,
                            "duration": elapsed,
                            "category": self._categorize_window(self._current_window),
                            "timestamp": datetime.now().isoformat(),
                        }

                        for callback in self._activity_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(self._last_window_log)
                                else:
                                    callback(self._last_window_log)
                            except Exception as e:
                                logger.error("Activity callback error: %s", e)

                    self._current_window = current
                    self._window_start_time = time.time()

                await asyncio.sleep(self.interval)

            except Exception as e:
                logger.error("Monitor loop error: %s", e)
                await asyncio.sleep(5)

    def stop(self) -> None:
        self.is_running = False
        logger.info("Screen monitoring stopped")

    def get_current_context(self) -> dict:
        """Get current screen context for AI awareness."""
        return {
            "active_window": self._current_window,
            "window_category": self._categorize_window(self._current_window),
            "time_on_current": time.time() - self._window_start_time,
            "timestamp": datetime.now().isoformat(),
        }
