"""Book Tracker Plugin - Track reading list and progress."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime
from pathlib import Path

BOOKS_FILE = Path(__file__).parent.parent / "data" / "memory" / "books.json"


class BookTrackerPlugin(PluginBase):
    name = "book_tracker"
    description = "Track books you're reading and want to read"
    triggers = ["book", "reading", "finished book", "reading list", "book list",
                 "add book", "currently reading"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if BOOKS_FILE.exists():
            try: return json.loads(BOOKS_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"reading": [], "want_to_read": [], "finished": []}

    def _save(self):
        BOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        BOOKS_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if "finished" in lower or "done reading" in lower:
            match = re.search(r'(?:finished|done reading)[:\s]+(.+)', lower)
            if match:
                title = match.group(1).strip().title()
                self._data["finished"].append({"title": title, "date": datetime.now().isoformat()})
                self._data["reading"] = [b for b in self._data["reading"] if b["title"].lower() != title.lower()]
                self._save()
                return f"Congrats on finishing '{title}'! Total books read: {len(self._data['finished'])}"

        if any(w in lower for w in ["add book", "want to read", "add to list"]):
            match = re.search(r'(?:add book|want to read|add to list)[:\s]+(.+)', lower)
            if match:
                title = match.group(1).strip().title()
                self._data["want_to_read"].append({"title": title})
                self._save()
                return f"Added '{title}' to reading list!"

        if "reading" in lower and any(w in lower for w in ["start", "currently", "now"]):
            match = re.search(r'(?:start|currently|now)\s+reading[:\s]+(.+)', lower)
            if match:
                title = match.group(1).strip().title()
                self._data["reading"].append({"title": title, "started": datetime.now().isoformat()})
                self._save()
                return f"Started reading '{title}'!"

        if any(w in lower for w in ["list", "show", "my books"]):
            parts = []
            if self._data["reading"]:
                parts.append("Currently reading:\n" + "\n".join(f"  - {b['title']}" for b in self._data["reading"]))
            if self._data["want_to_read"]:
                parts.append("Want to read:\n" + "\n".join(f"  - {b['title']}" for b in self._data["want_to_read"]))
            if self._data["finished"]:
                parts.append(f"Finished: {len(self._data['finished'])} books")
            return "\n\n".join(parts) if parts else "No books tracked. Add with: 'add book The Alchemist'"

        return "Book Tracker:\n  'add book Title' - add to list\n  'start reading Title'\n  'finished Title'\n  'my books'"
