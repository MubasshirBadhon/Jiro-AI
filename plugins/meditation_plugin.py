"""Meditation Guide Plugin - Guided meditation and breathing exercises."""

from plugins.plugin_loader import PluginBase
import random

EXERCISES = [
    {
        "name": "4-7-8 Breathing",
        "steps": "1. Breathe IN through nose for 4 seconds\n2. HOLD breath for 7 seconds\n3. Breathe OUT through mouth for 8 seconds\n4. Repeat 4 times",
        "benefit": "Reduces anxiety and helps you fall asleep"
    },
    {
        "name": "Box Breathing",
        "steps": "1. Breathe IN for 4 seconds\n2. HOLD for 4 seconds\n3. Breathe OUT for 4 seconds\n4. HOLD for 4 seconds\n5. Repeat 4 times",
        "benefit": "Calms nerves, used by Navy SEALs"
    },
    {
        "name": "Body Scan Meditation",
        "steps": "1. Close your eyes, sit comfortably\n2. Focus on your toes, relax them\n3. Move up: feet, legs, stomach, chest\n4. Continue: arms, hands, neck, face\n5. Stay present for 2 minutes",
        "benefit": "Reduces muscle tension and stress"
    },
    {
        "name": "5-4-3-2-1 Grounding",
        "steps": "Notice:\n  5 things you can SEE\n  4 things you can TOUCH\n  3 things you can HEAR\n  2 things you can SMELL\n  1 thing you can TASTE",
        "benefit": "Stops anxiety and panic attacks immediately"
    },
]


class MeditationPlugin(PluginBase):
    name = "meditation"
    description = "Guided meditation, breathing exercises, stress relief"
    triggers = ["meditate", "meditation", "breathe", "breathing", "calm down",
                 "relax", "stress", "anxious", "panic", "deep breath"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if any(w in lower for w in ["panic", "anxious", "anxiety", "stress"]):
            ex = EXERCISES[3]  # 5-4-3-2-1 grounding
        elif any(w in lower for w in ["sleep", "insomnia", "can't sleep"]):
            ex = EXERCISES[0]  # 4-7-8
        else:
            ex = random.choice(EXERCISES)

        return (f"  {ex['name']}\n\n"
                f"{ex['steps']}\n\n"
                f"Benefit: {ex['benefit']}\n\n"
                f"Take your time, boss. I'll be here when you're ready.")
