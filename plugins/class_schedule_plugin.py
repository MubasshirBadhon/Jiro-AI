"""Class Schedule Plugin - Manage weekly class timetable."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime
from pathlib import Path

SCHEDULE_FILE = Path(__file__).parent.parent / "data" / "memory" / "class_schedule.json"

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class ClassSchedulePlugin(PluginBase):
    name = "class_schedule"
    description = "Manage weekly class timetable"
    triggers = ["class schedule", "timetable", "next class", "class today",
                 "add class", "my classes", "class tomorrow"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if SCHEDULE_FILE.exists():
            try: return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {day: [] for day in DAYS}

    def _save(self):
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Add class
        add_match = re.search(r'add\s+class[:\s]+(.+?)\s+(?:on\s+)?(\w+day)\s+(?:at\s+)?(\d+[:\d]*\s*(?:am|pm)?)', lower)
        if add_match:
            subject = add_match.group(1).strip().title()
            day = add_match.group(2).lower()
            time_str = add_match.group(3).strip()
            if day in self._data:
                self._data[day].append({"subject": subject, "time": time_str})
                self._data[day].sort(key=lambda x: x["time"])
                self._save()
                return f"Added: {subject} on {day.title()} at {time_str}"
            return f"Invalid day: {day}"

        # Today's classes
        if "today" in lower:
            today = DAYS[datetime.now().weekday()]
            classes = self._data.get(today, [])
            if not classes:
                return f"No classes today ({today.title()})!"
            result = f"Today's classes ({today.title()}):\n"
            for c in classes:
                result += f"  {c['time']} - {c['subject']}\n"
            return result

        # Tomorrow's classes
        if "tomorrow" in lower:
            tmrw = DAYS[(datetime.now().weekday() + 1) % 7]
            classes = self._data.get(tmrw, [])
            if not classes:
                return f"No classes tomorrow ({tmrw.title()})!"
            result = f"Tomorrow's classes ({tmrw.title()}):\n"
            for c in classes:
                result += f"  {c['time']} - {c['subject']}\n"
            return result

        # Full timetable
        result = "Class Schedule:\n"
        has_classes = False
        for day in DAYS:
            classes = self._data.get(day, [])
            if classes:
                has_classes = True
                result += f"\n{day.title()}:\n"
                for c in classes:
                    result += f"  {c['time']} - {c['subject']}\n"
        if not has_classes:
            result = "No classes scheduled. Add with: 'add class Physics on Monday at 9am'"
        return result
