"""Alarm and Reminder Plugin for Jiro AI.

Handles setting alarms, reminders, and timers.
Understands natural language including Bengali time references.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.plugin_loader import PluginBase

logger = logging.getLogger("jiro.plugins.alarm")

ALARMS_FILE = Path(__file__).parent.parent / "data" / "memory" / "alarms.json"


class AlarmPlugin(PluginBase):
    name = "alarm"
    description = "Set alarms, reminders, and timers with natural language"
    triggers = [
        "alarm", "reminder", "remind me", "set alarm", "wake me",
        "timer", "call dio", "call dibo", "call korbo",
        "remind", "schedule alarm", "alert me",
    ]
    version = "1.0.0"

    def __init__(self, config_manager, ai_engine=None):
        super().__init__(config_manager, ai_engine)
        self.alarms: list[dict] = []
        self._load_alarms()
        self._running_tasks: list[asyncio.Task] = []

    def _load_alarms(self) -> None:
        if ALARMS_FILE.exists():
            with open(ALARMS_FILE, "r") as f:
                self.alarms = json.load(f)

    def _save_alarms(self) -> None:
        ALARMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ALARMS_FILE, "w") as f:
            json.dump(self.alarms, f, indent=2, default=str)

    def _parse_time(self, text: str) -> Optional[datetime]:
        """Parse time from natural language including Bengali."""
        now = datetime.now()
        text_lower = text.lower()

        bangla_time_map = {
            "shokal": 8, "sokal": 8, "bikal": 16, "bikale": 16,
            "bikalei": 16, "raat": 21, "raate": 21, "dupur": 12,
            "dupure": 12, "shondha": 18, "shondhay": 18,
        }

        for bangla_word, hour in bangla_time_map.items():
            if bangla_word in text_lower:
                target = now.replace(hour=hour, minute=0, second=0)
                if target <= now:
                    target += timedelta(days=1)
                return target

        time_match = re.search(r'(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm|AM|PM)?', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3)

            if period:
                if period.lower() == "pm" and hour != 12:
                    hour += 12
                elif period.lower() == "am" and hour == 12:
                    hour = 0
            else:
                if hour <= 12 and now.hour >= hour + 12:
                    pass
                elif hour <= 12 and now.hour >= hour:
                    hour += 12

            target = now.replace(hour=hour, minute=minute, second=0)
            if target <= now:
                target += timedelta(days=1)
            return target

        minutes_match = re.search(r'(\d+)\s*min', text_lower)
        if minutes_match:
            mins = int(minutes_match.group(1))
            return now + timedelta(minutes=mins)

        hours_match = re.search(r'(\d+)\s*hour', text_lower)
        if hours_match:
            hrs = int(hours_match.group(1))
            return now + timedelta(hours=hrs)

        tay_match = re.search(r'(\d{1,2})\s*(?:tay|ta|টায়)', text_lower)
        if tay_match:
            hour = int(tay_match.group(1))
            if hour <= 12 and now.hour >= hour:
                hour += 12
            if hour <= 12 and now.hour >= hour + 12:
                pass
            target = now.replace(hour=hour % 24, minute=0, second=0)
            if target <= now:
                target += timedelta(days=1)
            return target

        return None

    async def execute(self, command: str, context: Optional[dict] = None) -> str:
        if "list" in command.lower() or "show" in command.lower():
            return self._list_alarms()

        if "cancel" in command.lower() or "delete" in command.lower():
            return self._cancel_alarm(command)

        alarm_time = self._parse_time(command)
        if alarm_time:
            alarm = {
                "time": alarm_time.isoformat(),
                "message": command,
                "created_at": datetime.now().isoformat(),
                "triggered": False,
            }
            self.alarms.append(alarm)
            self._save_alarms()

            task = asyncio.create_task(self._wait_and_trigger(alarm))
            self._running_tasks.append(task)

            time_str = alarm_time.strftime("%I:%M %p")
            return f"Alarm set for {time_str}. I'll remind you!"

        if self.ai_engine:
            return await self.ai_engine.process(
                f"The user wants to set an alarm or reminder: '{command}'. "
                f"Help them specify a time. Current time is {datetime.now().strftime('%I:%M %p')}."
            )

        return "I couldn't understand the time. Please specify like '5 PM', '30 minutes', or 'bikal 4 tay'."

    async def _wait_and_trigger(self, alarm: dict) -> None:
        alarm_time = datetime.fromisoformat(alarm["time"])
        wait_seconds = (alarm_time - datetime.now()).total_seconds()

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        alarm["triggered"] = True
        self._save_alarms()
        logger.info("ALARM TRIGGERED: %s", alarm["message"])

    def _list_alarms(self) -> str:
        active = [a for a in self.alarms if not a.get("triggered")]
        if not active:
            return "No active alarms."

        lines = ["Active alarms:"]
        for i, alarm in enumerate(active, 1):
            t = datetime.fromisoformat(alarm["time"])
            lines.append(f"  {i}. {t.strftime('%I:%M %p')} - {alarm['message']}")
        return "\n".join(lines)

    def _cancel_alarm(self, command: str) -> str:
        num_match = re.search(r'(\d+)', command)
        if num_match:
            idx = int(num_match.group(1)) - 1
            active = [a for a in self.alarms if not a.get("triggered")]
            if 0 <= idx < len(active):
                active[idx]["triggered"] = True
                self._save_alarms()
                return f"Alarm {idx + 1} cancelled."
        return "Please specify which alarm to cancel (e.g., 'cancel alarm 1')."
