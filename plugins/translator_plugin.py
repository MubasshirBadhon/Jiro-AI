"""Translator Plugin - Translate between languages using AI."""

from plugins.plugin_loader import PluginBase
import re


class TranslatorPlugin(PluginBase):
    name = "translator"
    description = "Translate text between English, Bengali, and other languages"
    triggers = ["translate", "translation", "in english", "in bengali", "in bangla",
                 "banglay bolo", "english e bolo"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Detect target language
        target = "English"
        if any(w in lower for w in ["bengali", "bangla", "banglay"]):
            target = "Bengali"
        elif "hindi" in lower:
            target = "Hindi"
        elif "spanish" in lower:
            target = "Spanish"
        elif "french" in lower:
            target = "French"
        elif "arabic" in lower:
            target = "Arabic"
        elif "japanese" in lower:
            target = "Japanese"
        elif "chinese" in lower:
            target = "Chinese"

        # Extract text to translate
        text_match = re.search(
            r'translate\s+["\']?(.+?)["\']?\s+(?:to|in|into)\s+\w+', command, re.IGNORECASE
        )
        if not text_match:
            text_match = re.search(r'translate\s+(.+)', command, re.IGNORECASE)

        if text_match:
            text = text_match.group(1).strip()
            return f"[Translation to {target}]: Please ask me in conversation mode: 'translate \"{text}\" to {target}' and I'll translate it for you."

        return "Say 'translate <text> to <language>'. Example: 'translate hello to Bengali'"
