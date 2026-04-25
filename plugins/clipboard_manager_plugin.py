"""Clipboard Manager Plugin - Extended clipboard with history."""

from plugins.plugin_loader import PluginBase


class ClipboardManagerPlugin(PluginBase):
    name = "clipboard_manager"
    description = "Extended clipboard manager with history and templates"
    triggers = ["text template", "save template", "my templates", "quick text"]

    _templates = {
        "email_sign": "Best regards,\n[Your Name]\n[Your Email]",
        "thank_you": "Thank you for your time and consideration.",
        "regards": "With warm regards,\n[Your Name]",
        "apology": "I sincerely apologize for the inconvenience. I will ensure this does not happen again.",
    }

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        for name, text in self._templates.items():
            if name.replace("_", " ") in lower:
                return f"Template '{name}':\n\n{text}\n\n(Copied to your response)"

        if "list" in lower or "all" in lower:
            result = "Text Templates:\n"
            for name in self._templates:
                result += f"  - {name.replace('_', ' ')}\n"
            return result

        return "Templates: 'email sign', 'thank you', 'regards', 'apology'. Say 'list templates'."
