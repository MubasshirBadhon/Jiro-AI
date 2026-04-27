"""Markdown Helper Plugin - Quick markdown formatting reference."""

from plugins.plugin_loader import PluginBase


class MarkdownHelperPlugin(PluginBase):
    name = "markdown_helper"
    description = "Markdown formatting quick reference"
    triggers = ["markdown", "md format", "how to format", "markdown syntax",
                 "markdown help"]

    async def execute(self, command: str, context: dict = None) -> str:
        return ("Markdown Quick Reference:\n\n"
                "  # Heading 1\n"
                "  ## Heading 2\n"
                "  ### Heading 3\n\n"
                "  **bold text**\n"
                "  *italic text*\n"
                "  ~~strikethrough~~\n\n"
                "  - Bullet list\n"
                "  1. Numbered list\n\n"
                "  [Link text](url)\n"
                "  ![Image alt](image_url)\n\n"
                "  > Blockquote\n\n"
                "  `inline code`\n"
                "  ```\n"
                "  code block\n"
                "  ```\n\n"
                "  | Col1 | Col2 |\n"
                "  |------|------|\n"
                "  | data | data |")
