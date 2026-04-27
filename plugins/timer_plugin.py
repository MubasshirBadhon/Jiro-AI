"""Timer Plugin - Countdown timers, stopwatch, Pomodoro."""

from plugins.plugin_loader import PluginBase
import asyncio
import re
import time


class TimerPlugin(PluginBase):
    name = "timer"
    description = "Countdown timers, stopwatch, and Pomodoro technique"
    triggers = ["timer", "countdown", "stopwatch", "pomodoro", "set timer",
                 "start timer", "stop timer", "time me"]

    def __init__(self):
        self._timers: dict = {}
        self._stopwatch_start: float = 0
        self._stopwatch_running: bool = False

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Pomodoro
        if "pomodoro" in lower:
            return ("Pomodoro technique:\n"
                    "  1. Work for 25 minutes (say 'set timer 25 minutes')\n"
                    "  2. Take a 5-minute break\n"
                    "  3. After 4 cycles, take a 15-minute break\n\n"
                    "Say 'set timer 25 minutes study session' to start!")

        # Stopwatch
        if "stopwatch" in lower:
            if "start" in lower or not self._stopwatch_running:
                self._stopwatch_start = time.time()
                self._stopwatch_running = True
                return "Stopwatch started!"
            elif "stop" in lower or "lap" in lower:
                if self._stopwatch_running:
                    elapsed = time.time() - self._stopwatch_start
                    self._stopwatch_running = False
                    mins, secs = divmod(int(elapsed), 60)
                    hrs, mins = divmod(mins, 60)
                    if hrs:
                        return f"Stopwatch: {hrs}h {mins}m {secs}s"
                    elif mins:
                        return f"Stopwatch: {mins}m {secs}s"
                    return f"Stopwatch: {secs}s"
                return "Stopwatch is not running. Say 'start stopwatch'"

        # Set timer
        time_match = re.search(r'(\d+)\s*(second|sec|minute|min|hour|hr)s?', lower)
        if time_match:
            amount = int(time_match.group(1))
            unit = time_match.group(2)

            if unit in ("second", "sec"):
                total_seconds = amount
                display = f"{amount} seconds"
            elif unit in ("minute", "min"):
                total_seconds = amount * 60
                display = f"{amount} minutes"
            else:
                total_seconds = amount * 3600
                display = f"{amount} hours"

            label = "Timer"
            label_match = re.search(r'(?:for|named?)\s+(.+)$', lower)
            if label_match:
                label = label_match.group(1).strip()

            timer_id = f"timer_{int(time.time())}"
            self._timers[timer_id] = {
                "seconds": total_seconds,
                "label": label,
                "start": time.time(),
            }
            return f"Timer set: {display} ({label}). I'll remind you when it's done!"

        # List active timers
        if "list" in lower or "active" in lower:
            if not self._timers:
                return "No active timers."
            result = "Active timers:\n"
            for tid, t in self._timers.items():
                elapsed = time.time() - t["start"]
                remaining = max(0, t["seconds"] - elapsed)
                mins, secs = divmod(int(remaining), 60)
                result += f"  {t['label']}: {mins}m {secs}s remaining\n"
            return result

        return ("Timer commands:\n"
                "  'set timer 5 minutes' - countdown\n"
                "  'start stopwatch' / 'stop stopwatch'\n"
                "  'pomodoro' - study technique")
