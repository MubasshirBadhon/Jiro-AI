"""Screen Monitor - Captures screen + tracks active windows.

Tracks what the user is doing, categorizes activities,
and provides context for the proactive assistant.
"""

import asyncio
import logging
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("jiro.monitor.screen")

SCREENSHOTS_DIR = Path(__file__).parent.parent / "data" / "recordings" / "screenshots"


class ScreenMonitor:
    """Monitors active windows and captures screenshots."""

    def __init__(self, config: dict):
        self._config = config
        self.enabled = config.get("monitoring", {}).get("enabled", True)
        self.interval = config.get("monitoring", {}).get("screenshot_interval_seconds", 30)
        self.is_running = False
        self._current_window = ""
        self._window_start = time.time()
        self._callbacks: list[Callable] = []
        self._distraction_sites = config.get("monitoring", {}).get(
            "distraction_sites", ["facebook.com", "instagram.com", "tiktok.com"])

    def on_activity_change(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def get_active_window(self) -> str:
        """Get currently active window title (cross-platform)."""
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
                r = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                                   capture_output=True, text=True, timeout=5)
                return r.stdout.strip()
            elif system == "Darwin":
                script = 'tell app "System Events" to get name of first process whose frontmost is true'
                r = subprocess.run(["osascript", "-e", script],
                                   capture_output=True, text=True, timeout=5)
                return r.stdout.strip()
        except Exception:
            pass
        return "Unknown"

    def categorize(self, title: str) -> str:
        """Categorize window title."""
        t = title.lower()
        if any(s in t for s in self._distraction_sites):
            return "distraction"
        productive = ["vscode", "visual studio", "pycharm", "terminal", "cmd",
                       "powershell", "jupyter", "github", "gitlab", "stackoverflow"]
        if any(s in t for s in productive):
            return "productive"
        study = ["khan academy", "coursera", "udemy", "wikipedia", "arxiv",
                 "tutorial", "documentation", "learn"]
        if any(s in t for s in study):
            return "study"
        return "neutral"

    async def take_screenshot(self) -> Optional[str]:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fp = SCREENSHOTS_DIR / f"screen_{ts}.png"
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=str(fp))
            return str(fp)
        except ImportError:
            try:
                subprocess.run(["scrot", str(fp)], capture_output=True, timeout=10)
                if fp.exists():
                    return str(fp)
            except FileNotFoundError:
                pass
        return None

    async def run(self) -> None:
        """Main monitoring loop."""
        self.is_running = True
        logger.info("Screen monitoring started")
        while self.is_running:
            try:
                current = self.get_active_window()
                if current != self._current_window:
                    elapsed = time.time() - self._window_start
                    if self._current_window and elapsed > 1:
                        activity = {
                            "window": self._current_window,
                            "duration": elapsed,
                            "category": self.categorize(self._current_window),
                            "timestamp": datetime.now().isoformat(),
                        }
                        for cb in self._callbacks:
                            try:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb(activity)
                                else:
                                    cb(activity)
                            except Exception as e:
                                logger.error("Callback error: %s", e)
                    self._current_window = current
                    self._window_start = time.time()
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error("Monitor error: %s", e)
                await asyncio.sleep(5)

    def stop(self) -> None:
        self.is_running = False

    def get_context(self) -> dict:
        return {
            "active_window": self._current_window,
            "category": self.categorize(self._current_window),
            "time_on_current_seconds": time.time() - self._window_start,
            "timestamp": datetime.now().isoformat(),
        }
