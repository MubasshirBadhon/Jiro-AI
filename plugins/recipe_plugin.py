"""Recipe Helper Plugin - Quick recipes and cooking tips."""

from plugins.plugin_loader import PluginBase
import random

QUICK_RECIPES = [
    {"name": "Instant Noodle Upgrade", "time": "10 min",
     "steps": "Boil noodles. Add an egg, green onions, soy sauce, and chili flakes. Top with sesame oil."},
    {"name": "Banana Smoothie", "time": "5 min",
     "steps": "Blend: 1 banana + 1 cup milk + 2 tbsp honey + ice. Optional: oats, peanut butter."},
    {"name": "Egg Fried Rice", "time": "15 min",
     "steps": "Fry rice in oil. Push aside, scramble eggs. Mix together. Add soy sauce, salt, veggies."},
    {"name": "Toast & Egg", "time": "5 min",
     "steps": "Toast bread. Fry/boil egg. Season with salt & pepper. Add butter to toast."},
    {"name": "Chai Tea", "time": "8 min",
     "steps": "Boil water with tea leaves, ginger, cardamom. Add milk and sugar. Strain and serve."},
    {"name": "Quick Oatmeal", "time": "5 min",
     "steps": "Microwave oats + milk for 2 min. Add banana slices, honey, and cinnamon."},
    {"name": "Sandwich", "time": "5 min",
     "steps": "Bread + mayo + lettuce + tomato + cheese + protein of choice. Press and cut diagonally."},
    {"name": "Maggi/Ramen Upgrade", "time": "12 min",
     "steps": "Cook noodles. Add: peanut butter + soy sauce + chili + lime juice. Top with green onions."},
]


class RecipePlugin(PluginBase):
    name = "recipe"
    description = "Quick recipes and cooking tips for students"
    triggers = ["recipe", "cook", "cooking", "how to make", "ingredients",
                 "quick meal", "what to eat", "food", "hungry"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if any(w in lower for w in ["quick", "fast", "easy", "simple", "random"]):
            recipe = random.choice(QUICK_RECIPES)
            return f"Quick Recipe: {recipe['name']} ({recipe['time']})\n\n{recipe['steps']}"

        if "hungry" in lower or "what to eat" in lower:
            recipe = random.choice(QUICK_RECIPES)
            return f"How about {recipe['name']}? Takes only {recipe['time']}!\n\n{recipe['steps']}"

        if "list" in lower:
            result = "Quick Student Recipes:\n"
            for r in QUICK_RECIPES:
                result += f"  - {r['name']} ({r['time']})\n"
            return result + "\nSay the recipe name for details!"

        return ("Recipe Helper:\n"
                "  'quick recipe' - random easy recipe\n"
                "  'recipe list' - all quick recipes\n"
                "  'I'm hungry' - food suggestion\n"
                "  Or ask about any dish!")
