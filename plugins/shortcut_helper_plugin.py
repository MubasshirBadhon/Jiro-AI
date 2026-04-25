"""Shortcut Helper Plugin - Common keyboard shortcuts reference."""

from plugins.plugin_loader import PluginBase

SHORTCUTS = {
    "general": {
        "Copy": "Ctrl+C", "Paste": "Ctrl+V", "Cut": "Ctrl+X",
        "Undo": "Ctrl+Z", "Redo": "Ctrl+Y", "Select All": "Ctrl+A",
        "Save": "Ctrl+S", "Find": "Ctrl+F", "Print": "Ctrl+P",
        "New Tab": "Ctrl+T", "Close Tab": "Ctrl+W", "Switch Tab": "Ctrl+Tab",
        "Task Manager": "Ctrl+Shift+Esc", "Lock Screen": "Win+L",
        "Desktop": "Win+D", "Screenshot": "Win+Shift+S",
        "File Explorer": "Win+E", "Settings": "Win+I",
    },
    "vscode": {
        "Command Palette": "Ctrl+Shift+P", "Terminal": "Ctrl+`",
        "Go to File": "Ctrl+P", "Find in Files": "Ctrl+Shift+F",
        "Toggle Sidebar": "Ctrl+B", "Split Editor": "Ctrl+\\",
        "Comment Line": "Ctrl+/", "Format Document": "Shift+Alt+F",
        "Go to Definition": "F12", "Rename Symbol": "F2",
    },
    "chrome": {
        "New Tab": "Ctrl+T", "Reopen Closed Tab": "Ctrl+Shift+T",
        "Dev Tools": "F12", "Address Bar": "Ctrl+L",
        "Bookmark": "Ctrl+D", "History": "Ctrl+H",
        "Incognito": "Ctrl+Shift+N", "Refresh": "F5",
    },
}


class ShortcutHelperPlugin(PluginBase):
    name = "shortcut_helper"
    description = "Reference for keyboard shortcuts"
    triggers = ["shortcut", "keyboard shortcut", "hotkey", "ctrl", "shortcut for"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        for category, shortcuts in SHORTCUTS.items():
            if category in lower:
                result = f"{category.title()} Shortcuts:\n"
                for action, keys in shortcuts.items():
                    result += f"  {keys}: {action}\n"
                return result

        # Search for specific shortcut
        for category, shortcuts in SHORTCUTS.items():
            for action, keys in shortcuts.items():
                if action.lower() in lower:
                    return f"{action}: {keys}"

        # Show general shortcuts
        result = "Keyboard Shortcuts:\n"
        for action, keys in SHORTCUTS["general"].items():
            result += f"  {keys}: {action}\n"
        result += "\nSay 'vscode shortcuts' or 'chrome shortcuts' for app-specific shortcuts"
        return result
