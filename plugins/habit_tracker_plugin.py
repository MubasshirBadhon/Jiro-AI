"""Habit Tracker Plugin - Track daily habits and streaks."""

from plugins.plugin_loader import PluginBase
import json
from datetime import datetime, date
from pathlib import Path

HABITS_FILE = Path(__file__).parent.parent / "data" / "memory" / "habits.json"


class HabitTrackerPlugin(PluginBase):
    name = "habit_tracker"
    description = "Track daily habits, build streaks, monitor consistency"
    triggers = ["habit", "streak", "track habit", "daily habit", "did i",
                 "mark habit", "add habit", "my habits"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if HABITS_FILE.exists():
            try:
                return json.loads(HABITS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"habits": {}}

    def _save(self):
        HABITS_FILE.parent.mkdir(parents=True, exist_ok=True)
        HABITS_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        today = date.today().isoformat()

        # Add habit
        if "add habit" in lower:
            name = lower.replace("add habit", "").strip().strip(":")
            if name:
                self._data["habits"][name] = {"dates": [], "created": today}
                self._save()
                return f"Habit '{name}' created! Mark it daily with 'did {name}'"

        # Mark habit done
        if lower.startswith("did ") or "mark habit" in lower:
            name = lower.replace("did ", "").replace("mark habit", "").strip()
            if name in self._data["habits"]:
                if today not in self._data["habits"][name]["dates"]:
                    self._data["habits"][name]["dates"].append(today)
                    self._save()
                    streak = self._get_streak(name)
                    return f"'{name}' done today! Streak: {streak} days"
                return f"'{name}' already marked for today!"
            return f"Habit '{name}' not found. Add it first: 'add habit {name}'"

        # Show habits
        if any(w in lower for w in ["show", "list", "my habits", "all habits"]):
            if not self._data["habits"]:
                return "No habits tracked. Start with: 'add habit exercise'"
            result = "Your Habits:\n"
            for name, data in self._data["habits"].items():
                streak = self._get_streak(name)
                done_today = today in data["dates"]
                status = "done" if done_today else "pending"
                result += f"  [{status}] {name} - {streak} day streak ({len(data['dates'])} total)\n"
            return result

        return ("Habit Tracker:\n"
                "  'add habit exercise' - create habit\n"
                "  'did exercise' - mark done today\n"
                "  'my habits' - show all habits")

    def _get_streak(self, name: str) -> int:
        dates = sorted(self._data["habits"][name]["dates"], reverse=True)
        if not dates:
            return 0
        streak = 0
        check = date.today()
        for d in dates:
            if d == check.isoformat():
                streak += 1
                check = date.fromisoformat(d)
                from datetime import timedelta
                check -= timedelta(days=1)
            else:
                break
        return streak
