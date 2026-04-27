"""Folder Creator Plugin - Create folders/directories."""

import logging
from pathlib import Path

logger = logging.getLogger("jiro.plugins.folder_creator")

PLUGIN_NAME = "folder_creator"
PLUGIN_DESCRIPTION = "Create folders and directory structures"
PLUGIN_COMMANDS = ["create folder", "make folder", "new folder", "mkdir", "create directory"]


async def handle(command: str, context: dict = None) -> str:
    """Create a folder from the command."""
    lower = command.lower()
    for prefix in PLUGIN_COMMANDS:
        if lower.startswith(prefix):
            rest = command[len(prefix):].strip()
            break
    else:
        rest = command

    if not rest:
        return "Please specify a folder name. Example: 'create folder MyProject'"

    folder_path = Path(rest)

    # If it's just a name (no path separator), create on Desktop
    if not folder_path.is_absolute() and '/' not in rest and '\\' not in rest:
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            folder_path = desktop / rest
        else:
            folder_path = Path.home() / "Documents" / rest

    try:
        folder_path.mkdir(parents=True, exist_ok=True)
        return f"Folder created: {folder_path}"
    except Exception as e:
        logger.error("Folder creation failed: %s", e)
        return f"Failed to create folder: {e}"
