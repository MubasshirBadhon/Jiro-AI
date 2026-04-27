"""Birthday Reminder Plugin - Track and remind birthdays."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime, date
from pathlib import Path

BD_FILE = Path(__file__).parent.parent / "data" / "memory" / "birthdays.json"


class BirthdayReminderPlugin(PluginBase):
    name = "birthday_reminder"
    description = "Track birthdays and get reminders"
    triggers = ["birthday", "birthdays", "add birthday", "whose birthday",
                 "upcoming birthday"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if BD_FILE.exists():
            try: return json.loads(BD_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"people": []}

    def _save(self):
        BD_FILE.parent.mkdir(parents=True, exist_ok=True)
        BD_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Add birthday
        add_match = re.search(r'(?:add\s+)?birthday[:\s]+(\w[\w\s]*?)\s+(?:on|is)\s+(.+)', lower)
        if add_match:
            name = add_match.group(1).strip().title()
            date_str = add_match.group(2).strip()
            self._data["people"].append({"name": name, "date": date_str})
            self._save()
            return f"Birthday saved: {name} on {date_str}"

        # Check today
        if "today" in lower:
            today_str = date.today().strftime("%B %d").lower()
            today_short = date.today().strftime("%m/%d")
            matches = [p for p in self._data["people"]
                      if today_str in p["date"].lower() or today_short in p["date"]]
            if matches:
                names = ", ".join(p["name"] for p in matches)
                return f"Today's birthdays: {names}! Don't forget to wish them!"
            return "No birthdays today."

        # Upcoming
        if any(w in lower for w in ["upcoming", "next", "list", "all"]):
            if not self._data["people"]:
                return "No birthdays saved. Add with: 'birthday John on March 15'"
            result = "Saved birthdays:\n"
            for p in self._data["people"]:
                result += f"  {p['name']}: {p['date']}\n"
            return result

        return "Birthday commands:\n  'birthday John on March 15'\n  'upcoming birthdays'\n  'whose birthday today'"
