"""Language Practice Plugin - Vocabulary building and word practice."""

from plugins.plugin_loader import PluginBase
import random

WORDS = [
    {"word": "ubiquitous", "meaning": "present everywhere", "example": "Smartphones are ubiquitous today."},
    {"word": "eloquent", "meaning": "fluent and persuasive in speaking", "example": "She gave an eloquent speech."},
    {"word": "pragmatic", "meaning": "practical, realistic", "example": "Take a pragmatic approach to the problem."},
    {"word": "ephemeral", "meaning": "lasting for a very short time", "example": "Social media fame is often ephemeral."},
    {"word": "resilient", "meaning": "able to recover quickly", "example": "Resilient students bounce back from failure."},
    {"word": "altruistic", "meaning": "selflessly caring for others", "example": "His altruistic nature inspired everyone."},
    {"word": "meticulous", "meaning": "very careful and precise", "example": "She was meticulous in her research."},
    {"word": "inevitable", "meaning": "certain to happen", "example": "Change is inevitable in technology."},
    {"word": "versatile", "meaning": "able to adapt to many functions", "example": "Python is a versatile language."},
    {"word": "cognitive", "meaning": "related to thinking and understanding", "example": "Cognitive skills improve with practice."},
    {"word": "paradigm", "meaning": "a typical pattern or model", "example": "This represents a paradigm shift."},
    {"word": "hypothesis", "meaning": "a proposed explanation for testing", "example": "Test your hypothesis with experiments."},
    {"word": "ambiguous", "meaning": "having multiple meanings, unclear", "example": "The question was ambiguous."},
    {"word": "perseverance", "meaning": "continued effort despite difficulty", "example": "Success requires perseverance."},
    {"word": "synthesize", "meaning": "combine ideas into a coherent whole", "example": "Synthesize information from multiple sources."},
]


class LanguagePracticePlugin(PluginBase):
    name = "language_practice"
    description = "Build vocabulary with word of the day and practice"
    triggers = ["vocabulary", "word of the day", "learn word", "practice english",
                 "new word", "vocab", "word meaning"]

    async def execute(self, command: str, context: dict = None) -> str:
        word = random.choice(WORDS)
        return (f"Word of the Day: {word['word'].upper()}\n\n"
                f"  Meaning: {word['meaning']}\n"
                f"  Example: \"{word['example']}\"\n\n"
                f"Try using this word in a sentence today!")
