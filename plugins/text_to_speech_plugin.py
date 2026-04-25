"""Text-to-Speech Plugin - Read text aloud."""

from plugins.plugin_loader import PluginBase
import re


class TextToSpeechPlugin(PluginBase):
    name = "text_to_speech"
    description = "Read text aloud, change voice settings"
    triggers = ["read aloud", "speak this", "say this", "read this",
                 "text to speech", "tts", "change voice"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if "change voice" in lower or "voice" in lower:
            return ("Available TTS voices:\n"
                    "  en-US-GuyNeural (male, default)\n"
                    "  en-US-JennyNeural (female)\n"
                    "  en-GB-RyanNeural (British male)\n"
                    "  en-GB-SoniaNeural (British female)\n"
                    "  bn-BD-NabanitaNeural (Bengali female)\n"
                    "  bn-BD-PradeepNeural (Bengali male)\n\n"
                    "Change in config.json: tts.voice")

        text = re.sub(r'(?:read aloud|speak this|say this|read this|tts)\s*:?\s*', '', command, flags=re.IGNORECASE).strip()
        if text:
            return f"[Speaking]: {text}"

        return "Say 'read aloud: your text here' to have me read it out"
