"""Schedule Management Plugin for Jiro AI.

Manages daily schedule, tracks events, and provides smart suggestions
about availability based on past memory.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.plugin_loader import PluginBase

logger = logging.getLogger("jiro.plugins.schedule")

SCHEDULE_FILE = Path(__file__).parent.parent / "data" / "memory" / "schedule.json"


class SchedulePlugin(PluginBase):
    name = "schedule"
    description = "Manage daily schedule, check availability, suggest replies"
    triggers = [
        "schedule", "calendar", "free", "busy", "available",
        "appointment", "meeting", "event", "plan",
        "free acho", "busy achi", "ki korbo",
    ]
    version = "1.0.0"

    def __init__(self, config_manager, ai_engine=None):
        super().__init__(config_manager, ai_engine)
        self.schedule: list[dict] = []
        self._load_schedule()

    def _load_schedule(self) -> None:
        if SCHEDULE_FILE.exists():
            with open(SCHEDULE_FILE, "r") as f:
                self.schedule = json.load(f)

    def _save_schedule(self) -> None:
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(self.schedule, f, indent=2, default=str)

    def add_event(self, title: str, start: datetime, end: Optional[datetime] = None,
                  category: str = "general") -> dict:
        if end is None:
            end = start + timedelta(hours=1)

        event = {
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "category": category,
            "created_at": datetime.now().isoformat(),
        }
        self.schedule.append(event)
        self._save_schedule()
        return event

    def get_events_for_date(self, date: datetime) -> list[dict]:
        date_str = date.strftime("%Y-%m-%d")
        return [
            e for e in self.schedule
            if e["start"].startswith(date_str)
        ]

    def is_free(self, check_time: datetime) -> bool:
        for event in self.schedule:
            start = datetime.fromisoformat(event["start"])
            end = datetime.fromisoformat(event["end"])
            if start <= check_time <= end:
                return False
        return True

    def get_free_slots(self, date: datetime, start_hour: int = 8,
                       end_hour: int = 22) -> list[tuple[datetime, datetime]]:
        events = self.get_events_for_date(date)
        events.sort(key=lambda e: e["start"])

        free_slots = []
        current = date.replace(hour=start_hour, minute=0, second=0)
        day_end = date.replace(hour=end_hour, minute=0, second=0)

        for event in events:
            event_start = datetime.fromisoformat(event["start"])
            event_end = datetime.fromisoformat(event["end"])

            if current < event_start:
                free_slots.append((current, event_start))
            current = max(current, event_end)

        if current < day_end:
            free_slots.append((current, day_end))

        return free_slots

    async def execute(self, command: str, context: Optional[dict] = None) -> str:
        cmd_lower = command.lower()

        if any(w in cmd_lower for w in ["free", "available", "busy", "free acho"]):
            return await self._check_availability(command)

        if any(w in cmd_lower for w in ["add", "schedule", "create", "set"]):
            return await self._add_event(command)

        if any(w in cmd_lower for w in ["today", "show", "list", "what"]):
            return self._show_today()

        if any(w in cmd_lower for w in ["tomorrow"]):
            return self._show_tomorrow()

        if self.ai_engine:
            schedule_context = self._show_today()
            return await self.ai_engine.process(
                f"User schedule request: '{command}'\n"
                f"Current schedule:\n{schedule_context}\n"
                f"Current time: {datetime.now().strftime('%I:%M %p')}\n"
                f"Help the user with their schedule request."
            )

        return self._show_today()

    async def _check_availability(self, command: str) -> str:
        now = datetime.now()
        today_events = self.get_events_for_date(now)
        free_slots = self.get_free_slots(now)

        if not today_events:
            return "You have no events scheduled today. You're completely free!"

        lines = ["Today's schedule:"]
        for event in today_events:
            start = datetime.fromisoformat(event["start"])
            lines.append(f"  - {start.strftime('%I:%M %p')}: {event['title']}")

        if free_slots:
            lines.append("\nFree slots:")
            for start, end in free_slots:
                lines.append(f"  - {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')}")

        return "\n".join(lines)

    async def _add_event(self, command: str) -> str:
        if self.ai_engine:
            parse_result = await self.ai_engine.process(
                f"Extract event details from: '{command}'. "
                f"Return only JSON: {{\"title\": \"...\", \"hour\": N, \"minute\": N, \"duration_hours\": N}}"
            )
            try:
                import re
                json_match = re.search(r'\{.*\}', parse_result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    now = datetime.now()
                    start = now.replace(
                        hour=data.get("hour", now.hour),
                        minute=data.get("minute", 0),
                        second=0,
                    )
                    if start <= now:
                        start += timedelta(days=1)

                    duration = timedelta(hours=data.get("duration_hours", 1))
                    event = self.add_event(data["title"], start, start + duration)

                    return (
                        f"Event '{data['title']}' added at "
                        f"{start.strftime('%I:%M %p')} for "
                        f"{data.get('duration_hours', 1)} hour(s)."
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        return "Please specify the event details. Example: 'Schedule meeting at 3 PM for 2 hours'"

    def _show_today(self) -> str:
        events = self.get_events_for_date(datetime.now())
        if not events:
            return "No events scheduled for today."

        lines = ["Today's schedule:"]
        for event in sorted(events, key=lambda e: e["start"]):
            start = datetime.fromisoformat(event["start"])
            lines.append(f"  {start.strftime('%I:%M %p')} - {event['title']}")
        return "\n".join(lines)

    def _show_tomorrow(self) -> str:
        tomorrow = datetime.now() + timedelta(days=1)
        events = self.get_events_for_date(tomorrow)
        if not events:
            return "No events scheduled for tomorrow."

        lines = ["Tomorrow's schedule:"]
        for event in sorted(events, key=lambda e: e["start"]):
            start = datetime.fromisoformat(event["start"])
            lines.append(f"  {start.strftime('%I:%M %p')} - {event['title']}")
        return "\n".join(lines)
