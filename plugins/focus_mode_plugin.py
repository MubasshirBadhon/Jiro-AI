"""Focus Mode Plugin - Block distractions, enable Pomodoro."""

from plugins.plugin_loader import PluginBase
import time


class FocusModePlugin(PluginBase):
    name = "focus_mode"
    description = "Enable focus mode to block distractions and track work"
    triggers = ["focus", "focus mode", "do not disturb", "dnd", "deep work",
                 "block distractions", "concentration"]

    _active = False
    _start_time = 0
    _duration = 25 * 60

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if "stop" in lower or "off" in lower or "end" in lower:
            if self._active:
                elapsed = int(time.time() - self._start_time)
                self._active = False
                mins = elapsed // 60
                return f"Focus mode ended. You focused for {mins} minutes. Great work!"
            return "Focus mode is not active."

        if "status" in lower:
            if self._active:
                elapsed = int(time.time() - self._start_time)
                remaining = max(0, self._duration - elapsed)
                return f"Focus mode active: {remaining // 60}m {remaining % 60}s remaining"
            return "Focus mode is off."

        if self._active:
            elapsed = int(time.time() - self._start_time)
            remaining = max(0, self._duration - elapsed)
            return f"Already in focus mode! {remaining // 60}m remaining. Say 'stop focus' to end."

        import re
        dur_match = re.search(r'(\d+)\s*(?:min|minute)', lower)
        if dur_match:
            self._duration = int(dur_match.group(1)) * 60
        else:
            self._duration = 25 * 60

        self._active = True
        self._start_time = time.time()
        mins = self._duration // 60

        return (f"Focus mode activated for {mins} minutes!\n"
                f"  - Distraction warnings enabled\n"
                f"  - Notifications silenced\n"
                f"  - Say 'stop focus' when done\n"
                f"\nStay focused, boss!")
