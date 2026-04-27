"""Daily Planner Plugin - Plan your day hour by hour."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime, date
from pathlib import Path

PLAN_FILE = Path(__file__).parent.parent / "data" / "memory" / "daily_plans.json"


class DailyPlannerPlugin(PluginBase):
    name = "daily_planner"
    description = "Plan your day hour by hour, set daily goals"
    triggers = ["plan my day", "daily plan", "today's plan", "plan today",
                 "morning routine", "evening routine", "daily goals"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if PLAN_FILE.exists():
            try: return json.loads(PLAN_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"plans": {}}

    def _save(self):
        PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        PLAN_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        today = date.today().isoformat()

        # Add task to plan
        add_match = re.search(r'(?:at|plan)\s+(\d+(?::\d+)?)\s*(?:am|pm)?\s*[:-]\s*(.+)', lower)
        if add_match:
            time_str = add_match.group(1)
            task = add_match.group(2).strip()
            self._data["plans"].setdefault(today, []).append({"time": time_str, "task": task, "done": False})
            self._data["plans"][today].sort(key=lambda x: x["time"])
            self._save()
            return f"Added to today's plan: {time_str} - {task}"

        # Show today's plan
        if any(w in lower for w in ["show", "today", "my plan", "view"]):
            tasks = self._data["plans"].get(today, [])
            if not tasks:
                return ("No plan for today! Create one:\n"
                        "  'plan 9:00 - Study Physics'\n"
                        "  'plan 14:00 - Go to gym'\n"
                        "  'plan 20:00 - Review notes'")
            result = f"Today's Plan ({today}):\n"
            for t in tasks:
                status = "done" if t["done"] else "  "
                result += f"  [{status}] {t['time']} - {t['task']}\n"
            return result

        # Suggest a plan
        if "suggest" in lower:
            return ("Suggested Daily Plan:\n\n"
                    "  6:00 - Wake up, freshen up\n"
                    "  6:30 - Exercise/walk (30 min)\n"
                    "  7:00 - Breakfast\n"
                    "  7:30 - Study session 1 (2 hrs)\n"
                    "  9:30 - Break (15 min)\n"
                    "  9:45 - Study session 2 (2 hrs)\n"
                    "  12:00 - Lunch & rest\n"
                    "  14:00 - Classes/study (3 hrs)\n"
                    "  17:00 - Exercise/hobby\n"
                    "  18:00 - Dinner\n"
                    "  19:00 - Light study/revision\n"
                    "  21:00 - Free time\n"
                    "  22:30 - Sleep\n\n"
                    "Customize with: 'plan 9:00 - Your task'")

        return ("Daily Planner:\n"
                "  'plan 9:00 - Study Physics' - add task\n"
                "  'show today's plan' - view plan\n"
                "  'suggest a plan' - get template")
