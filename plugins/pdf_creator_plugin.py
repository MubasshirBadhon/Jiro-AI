"""PDF Creator Plugin - Create PDF documents."""

import logging
from pathlib import Path

logger = logging.getLogger("jiro.plugins.pdf_creator")

PLUGIN_NAME = "pdf_creator"
PLUGIN_DESCRIPTION = "Create PDF documents with specified content"
PLUGIN_COMMANDS = ["create pdf", "make pdf", "generate pdf", "new pdf"]


async def handle(command: str, context: dict = None) -> str:
    """Create a PDF document from the command."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError:
        return "reportlab is not installed. Run: pip install reportlab"

    lower = command.lower()
    for prefix in PLUGIN_COMMANDS:
        if lower.startswith(prefix):
            rest = command[len(prefix):].strip()
            break
    else:
        rest = command

    parts = rest.split(maxsplit=1)
    if not parts:
        return "Please specify a filename. Example: 'create pdf report My report content'"

    filename = parts[0]
    if not filename.endswith('.pdf'):
        filename += '.pdf'

    content = parts[1] if len(parts) > 1 else "Document created by Jiro AI."

    desktop = Path.home() / "Desktop"
    if desktop.exists():
        filepath = desktop / filename
    else:
        docs_dir = Path.home() / "Documents"
        docs_dir.mkdir(exist_ok=True)
        filepath = docs_dir / filename

    try:
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(filename.replace('.pdf', ''), styles['Title']))
        story.append(Spacer(1, 20))
        for paragraph in content.split('\\n'):
            story.append(Paragraph(paragraph, styles['Normal']))
            story.append(Spacer(1, 10))
        doc.build(story)
        return f"PDF created: {filepath}"
    except Exception as e:
        logger.error("PDF creation failed: %s", e)
        return f"Failed to create PDF: {e}"
