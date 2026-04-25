"""Health Tips Plugin - Daily health and wellness tips."""

from plugins.plugin_loader import PluginBase
import random

TIPS = [
    "Drink at least 8 glasses of water daily. Your brain is 75% water!",
    "Take a 5-minute break every hour of screen time. Look at something 20 feet away.",
    "Get 7-8 hours of sleep. Your brain consolidates learning during sleep.",
    "Exercise for at least 30 minutes daily. Even a walk counts!",
    "Eat breakfast! It improves concentration and memory for studying.",
    "Reduce sugar intake. It causes energy crashes during study sessions.",
    "Practice the 20-20-20 rule: Every 20 min, look 20 feet away for 20 seconds.",
    "Sit with good posture. Slouching reduces oxygen to your brain by 30%.",
    "Take deep breaths when stressed. It activates your parasympathetic nervous system.",
    "Eat foods rich in Omega-3 (fish, walnuts) for better brain function.",
    "Avoid studying in bed. Your brain associates bed with sleep, not focus.",
    "Stretch your neck and shoulders every hour. Tension causes headaches.",
    "Limit caffeine after 2 PM. It takes 6 hours for half of it to leave your body.",
    "Eat fruits and vegetables. They contain antioxidants that protect brain cells.",
    "Walk outside for 10 minutes. Sunlight boosts vitamin D and mood.",
]


class HealthTipsPlugin(PluginBase):
    name = "health_tips"
    description = "Daily health and wellness tips for students"
    triggers = ["health tip", "health advice", "wellness", "stay healthy",
                 "health tips", "healthy", "eye strain", "headache"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        if "eye" in lower or "screen" in lower:
            return ("Eye Care Tips:\n"
                    "  1. Follow 20-20-20 rule (every 20 min, look 20 ft away for 20 sec)\n"
                    "  2. Adjust screen brightness to match surroundings\n"
                    "  3. Keep screen at arm's length\n"
                    "  4. Use night mode/blue light filter after sunset\n"
                    "  5. Blink frequently!")

        if "headache" in lower:
            return ("Headache Relief:\n"
                    "  1. Drink water (dehydration is #1 cause)\n"
                    "  2. Take a break from screens\n"
                    "  3. Massage temples gently\n"
                    "  4. Fresh air - open a window or go outside\n"
                    "  5. Rest in a dark, quiet room for 15 minutes")

        return f"Health Tip: {random.choice(TIPS)}"
