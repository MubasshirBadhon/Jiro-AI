"""Document Creator Plugin - Create Word documents (.docx)."""

import logging
import os
from pathlib import Path

logger = logging.getLogger("jiro.plugins.doc_creator")

PLUGIN_NAME = "doc_creator"
PLUGIN_DESCRIPTION = "Create Word documents (.docx) with specified content"
PLUGIN_COMMANDS = ["create doc", "create document", "make doc", "write doc", "new document"]


async def handle(command: str, context: dict = None) -> str:
    """Create a Word document from the command."""
    try:
        from docx import Document
    except ImportError:
        return ("python-docx is not installed. Installing... "
                "Run: pip install python-docx")

    # Parse filename and content from command
    lower = command.lower()
    for prefix in PLUGIN_COMMANDS:
        if lower.startswith(prefix):
            rest = command[len(prefix):].strip()
            break
    else:
        rest = command

    # Try to extract filename and content
    # Formats: "create doc <filename> <content>" or "create doc <filename>"
    parts = rest.split(maxsplit=1)
    if not parts:
        return "Please specify a filename. Example: 'create doc report My report content here'"

    filename = parts[0]
    if not filename.endswith('.docx'):
        filename += '.docx'

    content = parts[1] if len(parts) > 1 else "Document created by Jiro AI."

    # Save to Desktop or current directory
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        filepath = desktop / filename
    else:
        docs_dir = Path.home() / "Documents"
        docs_dir.mkdir(exist_ok=True)
        filepath = docs_dir / filename

    try:
        doc = Document()
        doc.add_heading(filename.replace('.docx', ''), level=1)
        for paragraph in content.split('\\n'):
            doc.add_paragraph(paragraph)
        doc.save(str(filepath))
        return f"Document created: {filepath}"
    except Exception as e:
        logger.error("Doc creation failed: %s", e)
        return f"Failed to create document: {e}"
