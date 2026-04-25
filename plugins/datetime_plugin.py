"""Date & Time Plugin - Current time, date calculations, timezone."""

from plugins.plugin_loader import PluginBase
from datetime import datetime, timedelta
import re


class DateTimePlugin(PluginBase):
    name = "datetime"
    description = "Current time/date, date calculations, day of week"
    triggers = ["time", "date", "today", "tomorrow", "yesterday", "day",
                 "what day", "what time", "clock", "how many days"]

    async def execute(self, command: str, context: dict = None) -> str:
        now = datetime.now()
        lower = command.lower()

        if "time" in lower and "what" in lower:
            return f"It's {now.strftime('%I:%M %p')} ({now.strftime('%H:%M')})"

        if "date" in lower and "what" in lower or "today" in lower:
            return f"Today is {now.strftime('%A, %B %d, %Y')}"

        if "tomorrow" in lower:
            tmrw = now + timedelta(days=1)
            return f"Tomorrow is {tmrw.strftime('%A, %B %d, %Y')}"

        if "yesterday" in lower:
            yday = now - timedelta(days=1)
            return f"Yesterday was {yday.strftime('%A, %B %d, %Y')}"

        # Days until a date
        until_match = re.search(r'(?:how many days|days until|days to)\s+(.+)', lower)
        if until_match:
            target = until_match.group(1).strip()
            for fmt in ["%B %d", "%d/%m", "%m/%d", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    t = datetime.strptime(target, fmt)
                    t = t.replace(year=now.year)
                    if t < now:
                        t = t.replace(year=now.year + 1)
                    diff = (t - now).days
                    return f"{diff} days until {t.strftime('%B %d, %Y')}"
                except ValueError:
                    continue

        # Day of week for a date
        day_match = re.search(r'what day (?:is|was) (.+)', lower)
        if day_match:
            target = day_match.group(1).strip()
            for fmt in ["%B %d %Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    t = datetime.strptime(target, fmt)
                    return f"{target} is/was a {t.strftime('%A')}"
                except ValueError:
                    continue

        # Week number
        if "week" in lower:
            return f"Current week number: {now.isocalendar()[1]}"

        return f"Current date & time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}"
