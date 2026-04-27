"""Sleep Tracker Plugin - Log sleep, calculate sleep quality."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime, date
from pathlib import Path

SLEEP_FILE = Path(__file__).parent.parent / "data" / "memory" / "sleep.json"


class SleepTrackerPlugin(PluginBase):
    name = "sleep_tracker"
    description = "Track sleep hours, analyze sleep patterns"
    triggers = ["sleep", "slept", "bedtime", "wake up time", "sleep quality",
                 "how much sleep", "sleep log"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if SLEEP_FILE.exists():
            try: return json.loads(SLEEP_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"logs": []}

    def _save(self):
        SLEEP_FILE.parent.mkdir(parents=True, exist_ok=True)
        SLEEP_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        match = re.search(r'(?:slept|sleep)\s+(\d+(?:\.\d+)?)\s*(?:hours|hrs?|h)', lower)
        if match:
            hours = float(match.group(1))
            quality = "excellent" if hours >= 8 else "good" if hours >= 7 else "fair" if hours >= 6 else "poor"
            self._data["logs"].append({"hours": hours, "date": date.today().isoformat(), "quality": quality})
            self._save()
            return f"Logged {hours}h sleep ({quality}). {'Great rest!' if hours >= 7 else 'Try to get more sleep!'}"

        if any(w in lower for w in ["stats", "average", "history", "pattern"]):
            if not self._data["logs"]:
                return "No sleep data. Log with: 'slept 7 hours'"
            recent = self._data["logs"][-7:]
            avg = sum(l["hours"] for l in recent) / len(recent)
            return f"Sleep stats (last {len(recent)} days):\n  Average: {avg:.1f} hours\n  {'Good!' if avg >= 7 else 'You need more sleep!'}"

        return "Sleep Tracker:\n  'slept 7 hours' - log sleep\n  'sleep stats' - view history"
