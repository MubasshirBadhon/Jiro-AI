"""Random Facts Plugin - Share interesting facts."""

from plugins.plugin_loader import PluginBase
import random

FACTS = [
    "Honey never spoils. Archaeologists have found 3000-year-old honey that was still edible.",
    "Octopuses have three hearts and blue blood.",
    "A day on Venus is longer than its year.",
    "The human brain uses about 20% of the body's total energy.",
    "Bananas are berries, but strawberries aren't.",
    "There are more possible chess games than atoms in the observable universe.",
    "The shortest war in history lasted 38 minutes (Britain vs Zanzibar, 1896).",
    "Light takes 8 minutes and 20 seconds to travel from the Sun to Earth.",
    "The total weight of all ants on Earth is roughly equal to the total weight of all humans.",
    "Your DNA is about 99.9% identical to every other human.",
    "Water can boil and freeze at the same time (triple point).",
    "There are more trees on Earth than stars in the Milky Way.",
    "A group of flamingos is called a 'flamboyance'.",
    "The shortest complete sentence in English is 'I am' or 'Go'.",
    "The average person walks about 100,000 miles in their lifetime.",
    "Sharks are older than trees. Sharks: 400M years. Trees: 350M years.",
    "A teaspoon of neutron star material would weigh about 6 billion tons.",
    "The Great Wall of China is not visible from space with the naked eye.",
    "Cleopatra lived closer to the Moon landing than to the construction of the Great Pyramid.",
    "The inventor of the Pringles can is buried in one.",
]


class RandomFactsPlugin(PluginBase):
    name = "random_facts"
    description = "Share interesting and fun facts"
    triggers = ["fact", "fun fact", "interesting fact", "did you know",
                 "tell me something", "random fact", "trivia"]

    async def execute(self, command: str, context: dict = None) -> str:
        return f"Did you know?\n\n{random.choice(FACTS)}"
