"""Motivation Plugin - Quotes, affirmations, encouragement."""

from plugins.plugin_loader import PluginBase
import random

QUOTES = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
    "Believe you can and you're halfway there. - Theodore Roosevelt",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "It does not matter how slowly you go as long as you do not stop. - Confucius",
    "Education is the most powerful weapon which you can use to change the world. - Nelson Mandela",
    "The more that you read, the more things you will know. The more that you learn, the more places you'll go. - Dr. Seuss",
    "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
    "Start where you are. Use what you have. Do what you can. - Arthur Ashe",
    "The secret of getting ahead is getting started. - Mark Twain",
    "Your limitation—it's only your imagination.",
    "Push yourself, because no one else is going to do it for you.",
    "Great things never come from comfort zones.",
    "Dream it. Wish it. Do it.",
    "The harder you work for something, the greater you'll feel when you achieve it.",
    "Wake up with determination. Go to bed with satisfaction.",
    "Do something today that your future self will thank you for.",
    "Success doesn't just find you. You have to go out and get it.",
    "Dream bigger. Do bigger.",
    "Don't stop when you're tired. Stop when you're done.",
]

STUDY_MOTIVATION = [
    "Study now, selfie later! 📚",
    "Your brain is like a muscle - the more you use it, the stronger it gets!",
    "Every expert was once a beginner. Keep studying!",
    "One more chapter, one step closer to your goal!",
    "Focus on progress, not perfection.",
    "Today's study session is tomorrow's easy exam!",
    "Discipline is choosing between what you want now and what you want most.",
    "The pain of studying is temporary, but the joy of success is permanent!",
]


class MotivationPlugin(PluginBase):
    name = "motivation"
    description = "Get motivational quotes, study encouragement"
    triggers = ["motivate", "motivation", "inspire", "quote", "encourage",
                 "i give up", "i can't", "too hard", "demotivated", "lazy",
                 "pep talk", "cheer me up"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        if any(w in lower for w in ["study", "exam", "test", "homework"]):
            return random.choice(STUDY_MOTIVATION)
        if any(w in lower for w in ["give up", "can't", "hard", "tired", "lazy"]):
            return ("Hey boss, I believe in you! " + random.choice(QUOTES) +
                    "\n\nRemember: You're not studying because it's easy. "
                    "You're studying because you're building your future!")
        return random.choice(QUOTES)
