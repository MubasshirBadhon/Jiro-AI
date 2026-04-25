"""Notes Plugin - Quick notes, to-do lists, bookmarks."""

from plugins.plugin_loader import PluginBase
import json
import re
from datetime import datetime
from pathlib import Path

NOTES_FILE = Path(__file__).parent.parent / "data" / "memory" / "notes.json"


class NotesPlugin(PluginBase):
    name = "notes"
    description = "Take notes, manage to-do lists, save bookmarks"
    triggers = ["note", "notes", "todo", "to-do", "bookmark", "save",
                 "remember this", "write down", "add note", "show notes",
                 "list notes", "delete note"]

    def __init__(self):
        self._notes = self._load()

    def _load(self) -> dict:
        if NOTES_FILE.exists():
            try:
                return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"notes": [], "todos": [], "bookmarks": []}

    def _save(self) -> None:
        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        NOTES_FILE.write_text(json.dumps(self._notes, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Show/list notes
        if any(w in lower for w in ["show notes", "list notes", "my notes", "all notes"]):
            if not self._notes["notes"]:
                return "No notes saved. Say 'add note: your text here'"
            result = "Your notes:\n"
            for i, n in enumerate(self._notes["notes"], 1):
                result += f"  {i}. {n['text']} ({n['time']})\n"
            return result

        # Show todos
        if any(w in lower for w in ["show todo", "list todo", "my todo", "tasks"]):
            if not self._notes["todos"]:
                return "No to-do items. Say 'add todo: study physics'"
            result = "To-Do List:\n"
            for i, t in enumerate(self._notes["todos"], 1):
                status = "done" if t.get("done") else "pending"
                result += f"  {i}. [{status}] {t['text']}\n"
            return result

        # Complete todo
        done_match = re.search(r'(?:complete|done|finish)\s*(?:todo|task)\s*#?(\d+)', lower)
        if done_match:
            idx = int(done_match.group(1)) - 1
            if 0 <= idx < len(self._notes["todos"]):
                self._notes["todos"][idx]["done"] = True
                self._save()
                return f"Marked as done: {self._notes['todos'][idx]['text']}"
            return "Invalid task number"

        # Delete note
        del_match = re.search(r'delete\s*note\s*#?(\d+)', lower)
        if del_match:
            idx = int(del_match.group(1)) - 1
            if 0 <= idx < len(self._notes["notes"]):
                removed = self._notes["notes"].pop(idx)
                self._save()
                return f"Deleted note: {removed['text']}"
            return "Invalid note number"

        # Add todo
        todo_match = re.search(r'(?:add\s*)?(?:todo|to-do|task)[:\s]+(.+)', lower)
        if todo_match:
            text = todo_match.group(1).strip()
            self._notes["todos"].append({
                "text": text,
                "done": False,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            self._save()
            return f"Added to-do: {text}"

        # Add bookmark
        bm_match = re.search(r'bookmark[:\s]+(https?://\S+)', lower)
        if bm_match:
            url = bm_match.group(1)
            self._notes["bookmarks"].append({
                "url": url,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            self._save()
            return f"Bookmarked: {url}"

        # Add note (general)
        note_match = re.search(r'(?:add\s*)?(?:note|remember|write down|save)[:\s]+(.+)', command, re.IGNORECASE)
        if note_match:
            text = note_match.group(1).strip()
            self._notes["notes"].append({
                "text": text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            self._save()
            return f"Note saved: {text}"

        return ("Notes commands:\n"
                "  'add note: <text>' - save a note\n"
                "  'add todo: <task>' - add a task\n"
                "  'show notes' / 'show todos'\n"
                "  'complete todo #1'\n"
                "  'delete note #1'")
