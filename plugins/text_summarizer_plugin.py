"""Text Summarizer Plugin - Summarize text, articles, notes."""

from plugins.plugin_loader import PluginBase
import re


class TextSummarizerPlugin(PluginBase):
    name = "text_summarizer"
    description = "Summarize text, articles, and long notes"
    triggers = ["summarize", "summary", "tldr", "shorten", "brief",
                 "make it shorter", "key points"]

    async def execute(self, command: str, context: dict = None) -> str:
        text = re.sub(r'(?:summarize|summary|tldr|shorten|brief|make it shorter|key points)\s*:?\s*', '', command, flags=re.IGNORECASE).strip()
        if len(text) < 20:
            return "Paste the text you want summarized: 'summarize: your long text here'"

        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) <= 3:
            return f"Summary: {text[:300]}"

        key_sentences = sentences[:3]
        word_count = len(text.split())
        summary = '. '.join(key_sentences) + '.'

        return (f"Summary ({word_count} words → {len(summary.split())} words):\n\n{summary}\n\n"
                f"(For better summaries, ask me in conversation: 'summarize this: [text]')")
