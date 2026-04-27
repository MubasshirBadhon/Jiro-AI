"""Word Counter Plugin - Count words, characters, sentences, reading time."""

from plugins.plugin_loader import PluginBase
import re


class WordCounterPlugin(PluginBase):
    name = "word_counter"
    description = "Count words, characters, sentences, reading time"
    triggers = ["word count", "count words", "character count", "how many words",
                 "reading time", "how long to read"]

    async def execute(self, command: str, context: dict = None) -> str:
        text = re.sub(r'(?:word count|count words|character count|how many words|reading time)\s*:?\s*', '', command, flags=re.IGNORECASE).strip()
        if not text or len(text) < 3:
            return "Paste the text after the command: 'word count: your text here'"

        words = len(text.split())
        chars = len(text)
        chars_no_space = len(text.replace(" ", ""))
        sentences = len(re.findall(r'[.!?]+', text)) or 1
        paragraphs = len([p for p in text.split('\n') if p.strip()])
        reading_time = max(1, words // 200)

        return (f"Text Analysis:\n"
                f"  Words: {words}\n"
                f"  Characters: {chars} (without spaces: {chars_no_space})\n"
                f"  Sentences: {sentences}\n"
                f"  Paragraphs: {paragraphs}\n"
                f"  Reading time: ~{reading_time} min")
