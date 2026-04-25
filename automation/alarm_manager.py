"""Smart Alarm Manager - Bengali + English natural language alarms.

Understands time references in both languages:
  "set alarm for 5 PM"
  "5 tay call dio"  → smart AM/PM decision
  "bikal 4 tay"     → 4 PM
  "ami call diye janabo bikale" → afternoon reminder
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("jiro.automation.alarm")

ALARMS_FILE = Path(__file__).parent.parent / "data" / "memory" / "alarms.json"


class AlarmManager:
    """Smart alarm system with Bengali + English NLP."""

    def __init__(self, config: dict):
        self._config = config
        self._alarms: list[dict] = []
        self._callbacks: list[Callable] = []
        self._load()

    def _load(self) -> None:
        if ALARMS_FILE.exists():
            try:
                with open(ALARMS_FILE, "r") as f:
                    self._alarms = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self) -> None:
        ALARMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ALARMS_FILE, "w") as f:
            json.dump(self._alarms, f, indent=2, default=str)

    def on_alarm(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def parse_time(self, text: str) -> Optional[datetime]:
        """Parse time from natural language (Bengali + English)."""
        now = datetime.now()
        text_lower = text.lower()

        bangla_periods = {
            "shokal": (6, 11), "sokal": (6, 11),
            "dupur": (12, 14), "dupure": (12, 14),
            "bikal": (15, 18), "bikale": (15, 18), "bikalei": (15, 18),
            "shondha": (17, 19), "shondhay": (17, 19),
            "raat": (20, 23), "raate": (20, 23), "ratre": (20, 23),
        }

        for word, (start_h, end_h) in bangla_periods.items():
            if word in text_lower:
                hour_match = re.search(r'(\d{1,2})', text_lower)
                if hour_match:
                    hour = int(hour_match.group(1))
                    if hour <= 12:
                        if start_h >= 12:
                            hour += 12
                    hour = hour % 24
                else:
                    hour = start_h

                target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                return target

        tay_match = re.search(r'(\d{1,2})\s*(?:tay|ta|টায়)', text_lower)
        if tay_match:
            hour = int(tay_match.group(1))
            if hour <= 12:
                if now.hour < 12 and hour >= now.hour:
                    pass
                elif now.hour >= 12 and hour < 12:
                    hour += 12
                elif now.hour < hour:
                    pass
                else:
                    hour += 12

            target = now.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target

        time_match = re.search(r'(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm|AM|PM)', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            period = time_match.group(3).lower()
            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target

        min_match = re.search(r'(\d+)\s*min', text_lower)
        if min_match:
            return now + timedelta(minutes=int(min_match.group(1)))

        hour_match = re.search(r'(\d+)\s*hour', text_lower)
        if hour_match:
            return now + timedelta(hours=int(hour_match.group(1)))

        plain_time = re.search(r'(\d{1,2})\s*(?::(\d{2}))?(?:\s*o.?clock)?', text_lower)
        if plain_time and any(w in text_lower for w in ["alarm", "remind", "call", "wake"]):
            hour = int(plain_time.group(1))
            minute = int(plain_time.group(2) or 0)
            if hour <= 12 and now.hour >= hour:
                hour += 12
            target = now.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target

        return None

    def set_alarm(self, text: str, alarm_time: Optional[datetime] = None) -> Optional[dict]:
        """Set an alarm from natural language or explicit time."""
        if alarm_time is None:
            alarm_time = self.parse_time(text)
        if alarm_time is None:
            return None

        alarm = {
            "time": alarm_time.isoformat(),
            "message": text,
            "created_at": datetime.now().isoformat(),
            "triggered": False,
        }
        self._alarms.append(alarm)
        self._save()
        logger.info("Alarm set for %s", alarm_time.strftime("%I:%M %p"))
        return alarm

    async def check_alarms(self) -> list[dict]:
        """Check and trigger any due alarms."""
        now = datetime.now()
        triggered = []
        for alarm in self._alarms:
            if alarm.get("triggered"):
                continue
            alarm_time = datetime.fromisoformat(alarm["time"])
            if alarm_time <= now:
                alarm["triggered"] = True
                triggered.append(alarm)
                for cb in self._callbacks:
                    try:
                        if asyncio.iscoroutinefunction(cb):
                            await cb(alarm)
                        else:
                            cb(alarm)
                    except Exception as e:
                        logger.error("Alarm callback error: %s", e)
        if triggered:
            self._save()
        return triggered

    async def alarm_loop(self) -> None:
        """Continuous alarm checking loop."""
        while True:
            await self.check_alarms()
            await asyncio.sleep(10)

    def list_alarms(self) -> list[dict]:
        return [a for a in self._alarms if not a.get("triggered")]

    def cancel_alarm(self, index: int) -> bool:
        active = self.list_alarms()
        if 0 <= index < len(active):
            active[index]["triggered"] = True
            self._save()
            return True
        return False
