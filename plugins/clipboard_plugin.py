"""Clipboard Plugin - Copy/paste, clipboard history."""

from plugins.plugin_loader import PluginBase
import subprocess
import platform


class ClipboardPlugin(PluginBase):
    name = "clipboard"
    description = "Copy text to clipboard, view clipboard content"
    triggers = ["clipboard", "copy", "paste", "clip"]

    _history: list = []

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if any(w in lower for w in ["what", "show", "view", "paste", "read"]):
            text = self._get_clipboard()
            if text:
                self._history.append(text)
                return f"Clipboard: {text[:500]}"
            return "Clipboard is empty"

        if "history" in lower:
            if not self._history:
                return "No clipboard history"
            result = "Clipboard History:\n"
            for i, h in enumerate(self._history[-10:], 1):
                result += f"  {i}. {h[:80]}...\n" if len(h) > 80 else f"  {i}. {h}\n"
            return result

        if "copy" in lower:
            text = command.replace("copy", "", 1).strip()
            if text:
                self._set_clipboard(text)
                self._history.append(text)
                return f"Copied to clipboard: {text[:100]}"
            return "What should I copy?"

        if "clear" in lower:
            self._set_clipboard("")
            return "Clipboard cleared"

        return "Clipboard commands: 'show clipboard', 'copy <text>', 'clipboard history', 'clear clipboard'"

    def _get_clipboard(self) -> str:
        try:
            if platform.system() == "Windows":
                import ctypes
                cf_text = 13
                ctypes.windll.user32.OpenClipboard(0)
                handle = ctypes.windll.user32.GetClipboardData(cf_text)
                if handle:
                    data = ctypes.c_wchar_p(handle).value
                    ctypes.windll.user32.CloseClipboard()
                    return data or ""
                ctypes.windll.user32.CloseClipboard()
            else:
                r = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                   capture_output=True, text=True, timeout=5)
                return r.stdout
        except Exception:
            pass
        return ""

    def _set_clipboard(self, text: str) -> None:
        try:
            if platform.system() == "Windows":
                subprocess.run(["clip"], input=text, text=True, timeout=5)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=text, text=True, timeout=5)
        except Exception:
            pass
