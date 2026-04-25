"""App Launcher Plugin - Open apps, websites, and files."""

from plugins.plugin_loader import PluginBase
import subprocess
import platform
import webbrowser
import re


class LauncherPlugin(PluginBase):
    name = "launcher"
    description = "Open apps, websites, folders, and files"
    triggers = ["open", "launch", "start", "run", "go to"]

    APPS = {
        "notepad": "notepad",
        "calculator": "calc",
        "paint": "mspaint",
        "terminal": "cmd",
        "cmd": "cmd",
        "powershell": "powershell",
        "file manager": "explorer",
        "explorer": "explorer",
        "task manager": "taskmgr",
        "settings": "ms-settings:",
        "control panel": "control",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "vscode": "code",
        "vs code": "code",
    }

    SITES = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "facebook": "https://www.facebook.com",
        "github": "https://www.github.com",
        "gmail": "https://mail.google.com",
        "drive": "https://drive.google.com",
        "classroom": "https://classroom.google.com",
        "chatgpt": "https://chat.openai.com",
        "wikipedia": "https://www.wikipedia.org",
        "stackoverflow": "https://stackoverflow.com",
        "whatsapp": "https://web.whatsapp.com",
    }

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        target = re.sub(r'(?:open|launch|start|run|go to)\s*', '', lower).strip()

        # Check websites
        for name, url in self.SITES.items():
            if name in target:
                webbrowser.open(url)
                return f"Opening {name}..."

        # Check URL
        url_match = re.search(r'(https?://\S+)', command)
        if url_match:
            webbrowser.open(url_match.group(1))
            return f"Opening {url_match.group(1)}..."

        # Check apps (Windows)
        if platform.system() == "Windows":
            for name, cmd in self.APPS.items():
                if name in target:
                    try:
                        subprocess.Popen(cmd, shell=True)
                        return f"Opening {name}..."
                    except Exception:
                        return f"Could not open {name}"

        # Try as a direct command
        if target:
            try:
                if platform.system() == "Windows":
                    subprocess.Popen(f"start {target}", shell=True)
                else:
                    subprocess.Popen(target.split())
                return f"Trying to open: {target}"
            except Exception:
                pass

        return "What should I open? Try: 'open notepad', 'open youtube', 'open https://example.com'"
