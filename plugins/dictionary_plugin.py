"""Dictionary Plugin - Word definitions, synonyms, and translations."""

from plugins.plugin_loader import PluginBase
import re


class DictionaryPlugin(PluginBase):
    name = "dictionary"
    description = "Define words, find synonyms, and translate"
    triggers = ["define", "definition", "meaning", "synonym", "antonym",
                 "translate", "what does", "meaning of"]
    requires_api_keys = []

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        word_match = re.search(
            r'(?:define|definition|meaning|meaning of|what does)\s+["\']?(\w+)["\']?', lower
        )
        if not word_match:
            word_match = re.search(r'(\w+)\s+(?:meaning|definition)', lower)

        if word_match:
            word = word_match.group(1)
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                    )
                    if resp.status_code == 200:
                        data = resp.json()[0]
                        meanings = data.get("meanings", [])
                        result = f"**{word.title()}**\n"
                        for m in meanings[:3]:
                            pos = m.get("partOfSpeech", "")
                            defs = m.get("definitions", [])
                            if defs:
                                result += f"\n({pos}) {defs[0]['definition']}"
                                if defs[0].get("example"):
                                    result += f"\n  Example: \"{defs[0]['example']}\""
                            synonyms = m.get("synonyms", [])
                            if synonyms:
                                result += f"\n  Synonyms: {', '.join(synonyms[:5])}"
                        return result
                    return f"Could not find definition for '{word}'"
            except Exception:
                return f"Could not look up '{word}'. Check internet connection."

        if "translate" in lower:
            return ("For translation, I can help through conversation. "
                    "Just ask me to translate something and I'll do it!")

        return "Tell me a word to define. Example: 'define serendipity'"
