"""Assignment Tracker Plugin - Track homework and assignment deadlines."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime, date
from pathlib import Path

ASSIGN_FILE = Path(__file__).parent.parent / "data" / "memory" / "assignments.json"


class AssignmentTrackerPlugin(PluginBase):
    name = "assignment_tracker"
    description = "Track homework and assignment deadlines"
    triggers = ["assignment", "homework due", "deadline", "submission",
                 "due date", "assignments due", "pending assignments"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if ASSIGN_FILE.exists():
            try: return json.loads(ASSIGN_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"assignments": []}

    def _save(self):
        ASSIGN_FILE.parent.mkdir(parents=True, exist_ok=True)
        ASSIGN_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Add assignment
        add_match = re.search(r'(?:assignment|homework|due)[:\s]+(.+?)\s+(?:due|by|on)\s+(.+)', lower)
        if add_match:
            title = add_match.group(1).strip().title()
            due_date = add_match.group(2).strip()
            self._data["assignments"].append({
                "title": title, "due": due_date, "done": False,
                "added": datetime.now().isoformat(),
            })
            self._save()
            return f"Assignment added: '{title}' due {due_date}"

        # Mark done
        done_match = re.search(r'(?:done|finished|completed|submitted)\s+(?:assignment\s+)?(.+)', lower)
        if done_match:
            title = done_match.group(1).strip()
            for a in self._data["assignments"]:
                if title in a["title"].lower():
                    a["done"] = True
                    self._save()
                    return f"Marked as done: {a['title']}"

        # Show assignments
        pending = [a for a in self._data["assignments"] if not a["done"]]
        done = [a for a in self._data["assignments"] if a["done"]]

        if not pending and not done:
            return "No assignments tracked. Add: 'assignment Physics Lab Report due Friday'"

        result = ""
        if pending:
            result += "Pending Assignments:\n"
            for a in pending:
                result += f"  - {a['title']} (due: {a['due']})\n"
        if done:
            result += f"\nCompleted: {len(done)} assignments"

        return result
