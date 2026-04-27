"""Reminder Extractor - Auto-extract reminders from messages and conversations.

Detects implicit reminders from natural language:
  "ami ajke bikale call diye janabo" → afternoon call reminder
  "tomorrow meeting at 3"           → meeting reminder
  "remind me to buy groceries"      → general reminder
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("jiro.automation.reminders")


class ReminderExtractor:
    """Extracts reminders from text messages automatically."""

    def __init__(self, config: dict, alarm_manager=None):
        self._config = config
        self._alarm_manager = alarm_manager

    def extract_and_set(self, text: str) -> list[dict]:
        """Extract reminders from text and set them."""
        reminders = self.extract(text)
        results = []
        for r in reminders:
            if self._alarm_manager and r.get("time"):
                alarm_time = datetime.fromisoformat(r["time"])
                alarm = self._alarm_manager.set_alarm(r["message"], alarm_time)
                if alarm:
                    r["alarm_set"] = True
                    results.append(r)
        return results

    def extract(self, text: str) -> list[dict]:
        """Extract potential reminders from text."""
        reminders = []
        text_lower = text.lower()

        call_patterns = [
            (r'call\s+(?:dio|dibo|korbo)\s*(\d{1,2})\s*(?:tay|ta)', "call"),
            (r'(\d{1,2})\s*(?:tay|ta)\s*call\s*(?:dio|dibo)', "call"),
            (r'call\s+(?:at|by)\s+(\d{1,2})\s*(am|pm)?', "call"),
            (r'remind\s+(?:me\s+)?(?:to\s+)?(.+?)(?:\s+at\s+(\d{1,2}))?$', "reminder"),
        ]

        for pattern, rtype in call_patterns:
            match = re.search(pattern, text_lower)
            if match:
                now = datetime.now()
                hour = None

                try:
                    hour = int(match.group(1))
                except (IndexError, ValueError):
                    pass

                if hour:
                    if hour <= 12 and now.hour >= hour:
                        hour += 12
                    target = now.replace(hour=hour % 24, minute=0, second=0, microsecond=0)
                    if target <= now:
                        target += timedelta(days=1)
                    reminders.append({
                        "type": rtype,
                        "time": target.isoformat(),
                        "message": text,
                        "auto_extracted": True,
                    })

        time_words = {
            "tomorrow": timedelta(days=1),
            "next hour": timedelta(hours=1),
            "tonight": None,
            "ajke": timedelta(days=0),
            "kalke": timedelta(days=1),
        }

        for word, delta in time_words.items():
            if word in text_lower and delta is not None:
                period_map = {
                    "morning": 9, "shokal": 9, "sokal": 9,
                    "afternoon": 14, "bikal": 16, "bikale": 16,
                    "evening": 18, "shondha": 18,
                    "night": 21, "raat": 21,
                }
                hour = 9
                for period_word, period_hour in period_map.items():
                    if period_word in text_lower:
                        hour = period_hour
                        break

                now = datetime.now()
                target = (now + delta).replace(hour=hour, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)

                reminders.append({
                    "type": "reminder",
                    "time": target.isoformat(),
                    "message": text,
                    "auto_extracted": True,
                })
                break

        return reminders

    def should_extract(self, text: str) -> bool:
        """Check if text likely contains a reminder."""
        keywords = [
            "remind", "alarm", "call", "meeting", "schedule",
            "tomorrow", "tonight", "later",
            "dio", "dibo", "korbo", "janabo",
            "bikal", "shokal", "raat", "dupur",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)
