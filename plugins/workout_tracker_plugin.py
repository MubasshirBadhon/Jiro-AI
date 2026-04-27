"""Workout Tracker Plugin - Log exercises and track fitness."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime, date
from pathlib import Path

WORKOUT_FILE = Path(__file__).parent.parent / "data" / "memory" / "workouts.json"


class WorkoutTrackerPlugin(PluginBase):
    name = "workout_tracker"
    description = "Log exercises, track workouts and fitness progress"
    triggers = ["workout", "exercise", "pushups", "did exercises", "gym",
                 "push ups", "sit ups", "running", "jogging", "walked"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if WORKOUT_FILE.exists():
            try: return json.loads(WORKOUT_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"workouts": []}

    def _save(self):
        WORKOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        WORKOUT_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Log exercise
        ex_match = re.search(r'(?:did|done|completed)\s+(\d+)\s+(pushups?|push.?ups?|sit.?ups?|squats?|pull.?ups?|burpees?)', lower)
        if ex_match:
            count = int(ex_match.group(1))
            exercise = ex_match.group(2).strip()
            self._data["workouts"].append({
                "exercise": exercise, "count": count,
                "date": datetime.now().isoformat(),
            })
            self._save()
            total = sum(w["count"] for w in self._data["workouts"] if w["exercise"] == exercise)
            return f"Logged {count} {exercise}! Total all-time: {total}"

        # Log running/walking
        run_match = re.search(r'(?:ran|run|walked|jogged)\s+(\d+(?:\.\d+)?)\s*(?:km|miles?|meters?)', lower)
        if run_match:
            distance = float(run_match.group(1))
            activity = "running" if any(w in lower for w in ["ran", "run", "jog"]) else "walking"
            self._data["workouts"].append({
                "exercise": activity, "count": distance,
                "date": datetime.now().isoformat(),
            })
            self._save()
            return f"Logged {distance} km {activity}! Great job staying active!"

        # Stats
        if any(w in lower for w in ["stats", "history", "summary", "total"]):
            if not self._data["workouts"]:
                return "No workouts logged. Try: 'did 20 pushups' or 'ran 3 km'"
            today_workouts = [w for w in self._data["workouts"] if w["date"].startswith(date.today().isoformat())]
            result = "Workout Stats:\n"
            result += f"  Total sessions: {len(self._data['workouts'])}\n"
            if today_workouts:
                result += "  Today:\n"
                for w in today_workouts:
                    result += f"    {w['count']} {w['exercise']}\n"
            return result

        return ("Workout Tracker:\n"
                "  'did 20 pushups'\n"
                "  'ran 3 km'\n"
                "  'walked 5 km'\n"
                "  'workout stats'")
