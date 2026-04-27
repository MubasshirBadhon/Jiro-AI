"""Typing Speed Plugin - Test and improve typing speed."""

from plugins.plugin_loader import PluginBase
import random
import time

SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "Practice makes perfect when learning to type faster.",
    "Programming is the art of telling a computer what to do.",
    "Education is the passport to the future.",
    "Every expert was once a beginner who never gave up.",
    "Consistency is more important than perfection.",
    "The only way to learn programming is by writing code.",
    "A journey of a thousand miles begins with a single step.",
]


class TypingSpeedPlugin(PluginBase):
    name = "typing_speed"
    description = "Test and practice your typing speed"
    triggers = ["typing speed", "typing test", "type test", "wpm",
                 "how fast can i type", "typing practice"]

    _start_time = 0
    _current_text = ""

    async def execute(self, command: str, context: dict = None) -> str:
        if self._start_time > 0 and self._current_text:
            elapsed = time.time() - self._start_time
            words = len(command.split())
            wpm = int((words / elapsed) * 60)

            # Calculate accuracy
            original_words = self._current_text.lower().split()
            typed_words = command.lower().split()
            correct = sum(1 for a, b in zip(original_words, typed_words) if a == b)
            accuracy = (correct / len(original_words)) * 100 if original_words else 0

            self._start_time = 0
            self._current_text = ""

            result = f"Typing Results:\n  Speed: {wpm} WPM\n  Accuracy: {accuracy:.0f}%\n  Time: {elapsed:.1f}s\n\n"
            if wpm < 30: result += "Keep practicing! Average is 40 WPM."
            elif wpm < 60: result += "Good speed! Professional average is 65-75 WPM."
            elif wpm < 80: result += "Great speed! You're above average."
            else: result += "Excellent! You're a fast typist!"
            return result

        self._current_text = random.choice(SENTENCES)
        self._start_time = time.time()
        return f"Type this as fast as you can:\n\n  \"{self._current_text}\"\n\n(Copy the text exactly, then press Enter)"
