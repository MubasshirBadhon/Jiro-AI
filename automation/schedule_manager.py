"""Schedule Manager - Calendar + schedule awareness.

Tracks events, checks availability, and provides smart suggestions
about whether the user is free or busy.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.automation.schedule")

SCHEDULE_FILE = Path(__file__).parent.parent / "data" / "memory" / "schedule.json"


class ScheduleManager:
    """Manages daily schedule and availability."""

    def __init__(self, config: dict):
        self._config = config
        self._events: list[dict] = []
        self._load()

    def _load(self) -> None:
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE, "r") as f:
                    self._events = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self) -> None:
        SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(self._events, f, indent=2, default=str)

    def add_event(self, title: str, start: datetime,
                  end: Optional[datetime] = None, category: str = "general") -> dict:
        if end is None:
            end = start + timedelta(hours=1)
        event = {
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "category": category,
        }
        self._events.append(event)
        self._save()
        return event

    def get_today(self) -> list[dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return sorted(
            [e for e in self._events if e["start"].startswith(today)],
            key=lambda e: e["start"],
        )

    def is_free(self, check_time: datetime) -> bool:
        for e in self._events:
            start = datetime.fromisoformat(e["start"])
            end = datetime.fromisoformat(e["end"])
            if start <= check_time <= end:
                return False
        return True

    def get_free_slots(self, date: Optional[datetime] = None) -> list[tuple[str, str]]:
        date = date or datetime.now()
        events = self.get_today() if date.date() == datetime.now().date() else []
        events.sort(key=lambda e: e["start"])

        free = []
        current = date.replace(hour=8, minute=0, second=0)
        end_of_day = date.replace(hour=22, minute=0, second=0)

        for e in events:
            es = datetime.fromisoformat(e["start"])
            ee = datetime.fromisoformat(e["end"])
            if current < es:
                free.append((current.strftime("%I:%M %p"), es.strftime("%I:%M %p")))
            current = max(current, ee)

        if current < end_of_day:
            free.append((current.strftime("%I:%M %p"), end_of_day.strftime("%I:%M %p")))

        return free

    def format_today(self) -> str:
        events = self.get_today()
        if not events:
            return "No events scheduled for today. You're completely free!"
        lines = ["Today's schedule:"]
        for e in events:
            start = datetime.fromisoformat(e["start"])
            lines.append(f"  {start.strftime('%I:%M %p')} - {e['title']}")
        free = self.get_free_slots()
        if free:
            lines.append("\nFree slots:")
            for s, e in free:
                lines.append(f"  {s} to {e}")
        return "\n".join(lines)

    def suggest_reply(self, question: str) -> str:
        """Suggest a reply about availability."""
        now = datetime.now()
        events = self.get_today()
        free_slots = self.get_free_slots()

        if not events:
            return "You're free all day. You can say yes!"
        if self.is_free(now):
            return f"You're currently free. Your next event is later. You can say yes for now."
        return f"You have {len(events)} events today. Check your schedule before committing."
