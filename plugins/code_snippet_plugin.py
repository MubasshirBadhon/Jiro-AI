"""Code Snippet Plugin - Save and retrieve code snippets."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime
from pathlib import Path

SNIPPETS_FILE = Path(__file__).parent.parent / "data" / "memory" / "snippets.json"


class CodeSnippetPlugin(PluginBase):
    name = "code_snippet"
    description = "Save and retrieve code snippets"
    triggers = ["code snippet", "save code", "my snippets", "show snippet",
                 "add snippet", "snippet"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if SNIPPETS_FILE.exists():
            try: return json.loads(SNIPPETS_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"snippets": []}

    def _save(self):
        SNIPPETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNIPPETS_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Save snippet
        save_match = re.search(r'(?:save|add)\s+(?:code\s+)?snippet[:\s]+(\w+)\s*[:\s]+(.+)', command, re.DOTALL | re.IGNORECASE)
        if save_match:
            name = save_match.group(1)
            code = save_match.group(2).strip()
            self._data["snippets"].append({"name": name, "code": code, "date": datetime.now().isoformat()})
            self._save()
            return f"Snippet '{name}' saved!"

        # Show snippet
        show_match = re.search(r'(?:show|get)\s+snippet[:\s]+(\w+)', lower)
        if show_match:
            name = show_match.group(1)
            for s in self._data["snippets"]:
                if s["name"].lower() == name:
                    return f"Snippet '{s['name']}':\n{s['code']}"
            return f"Snippet '{name}' not found"

        # List snippets
        if any(w in lower for w in ["list", "show", "all", "my snippets"]):
            if not self._data["snippets"]:
                return "No snippets saved. Save with: 'save snippet hello_world: print(\"Hello!\")'"
            result = "Your snippets:\n"
            for s in self._data["snippets"]:
                result += f"  - {s['name']} ({s['date'][:10]})\n"
            return result

        return "Snippet commands: 'save snippet name: code', 'show snippet name', 'list snippets'"
