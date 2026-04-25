"""Water Reminder Plugin - Track water intake and send reminders."""

from plugins.plugin_loader import PluginBase
import json
from datetime import datetime, date
from pathlib import Path

WATER_FILE = Path(__file__).parent.parent / "data" / "memory" / "water.json"


class WaterReminderPlugin(PluginBase):
    name = "water_reminder"
    description = "Track water intake, remind to drink water"
    triggers = ["water", "drink water", "hydration", "drank water", "glass of water",
                 "water intake", "how much water"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if WATER_FILE.exists():
            try:
                return json.loads(WATER_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"daily_goal": 8, "log": {}}

    def _save(self):
        WATER_FILE.parent.mkdir(parents=True, exist_ok=True)
        WATER_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        today = date.today().isoformat()

        if any(w in lower for w in ["drank", "had", "drink", "glass"]):
            self._data["log"].setdefault(today, 0)
            self._data["log"][today] += 1
            count = self._data["log"][today]
            goal = self._data["daily_goal"]
            self._save()
            if count >= goal:
                return f"Glass #{count} logged! You've reached your daily goal of {goal} glasses!"
            return f"Glass #{count}/{goal} logged! {goal - count} more to go."

        if "status" in lower or "how much" in lower or "intake" in lower:
            count = self._data["log"].get(today, 0)
            goal = self._data["daily_goal"]
            return f"Water intake today: {count}/{goal} glasses. {'Great job!' if count >= goal else f'{goal - count} more to reach your goal.'}"

        return ("Water Tracker:\n"
                "  'drank water' - log a glass\n"
                "  'water status' - check today's intake\n"
                f"  Daily goal: {self._data['daily_goal']} glasses")
