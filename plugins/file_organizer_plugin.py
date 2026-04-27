"""File Organizer Plugin - Organize files on desktop/folders."""

from plugins.plugin_loader import PluginBase
import platform
from pathlib import Path


FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx", ".csv"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c"],
    "Installers": [".exe", ".msi", ".deb", ".dmg"],
}


class FileOrganizerPlugin(PluginBase):
    name = "file_organizer"
    description = "Organize files on desktop and folders by type"
    triggers = ["organize files", "clean desktop", "sort files", "file manager",
                 "organize desktop", "messy desktop"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Get target directory
        if "desktop" in lower:
            if platform.system() == "Windows":
                target = Path.home() / "Desktop"
            else:
                target = Path.home() / "Desktop"
        elif "downloads" in lower:
            target = Path.home() / "Downloads"
        else:
            target = Path.home() / "Desktop"

        if not target.exists():
            return f"Directory not found: {target}"

        # Count files by category
        files = [f for f in target.iterdir() if f.is_file()]
        if not files:
            return f"No files to organize in {target}"

        categorized = {}
        for f in files:
            ext = f.suffix.lower()
            placed = False
            for cat, exts in FILE_CATEGORIES.items():
                if ext in exts:
                    categorized.setdefault(cat, []).append(f.name)
                    placed = True
                    break
            if not placed:
                categorized.setdefault("Other", []).append(f.name)

        result = f"Files in {target.name} ({len(files)} total):\n"
        for cat, cat_files in categorized.items():
            result += f"\n  {cat} ({len(cat_files)}):\n"
            for f in cat_files[:5]:
                result += f"    - {f}\n"
            if len(cat_files) > 5:
                result += f"    ... and {len(cat_files) - 5} more\n"

        result += ("\n\nSay 'organize desktop now' to sort files into folders. "
                   "(Currently in preview mode)")
        return result
