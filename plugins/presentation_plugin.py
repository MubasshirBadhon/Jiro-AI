"""Presentation Helper Plugin - Tips and outlines for presentations."""

from plugins.plugin_loader import PluginBase


class PresentationPlugin(PluginBase):
    name = "presentation"
    description = "Help create presentation outlines and public speaking tips"
    triggers = ["presentation", "powerpoint", "ppt", "slides", "public speaking",
                 "speech", "present"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if any(w in lower for w in ["tips", "advice", "how to"]):
            return ("Presentation Tips:\n\n"
                    "  1. Start with a hook (question, story, or statistic)\n"
                    "  2. Follow the 10-20-30 rule:\n"
                    "     - Max 10 slides\n"
                    "     - Max 20 minutes\n"
                    "     - Min 30pt font\n"
                    "  3. One idea per slide\n"
                    "  4. Use visuals over text\n"
                    "  5. Practice 3 times before presenting\n"
                    "  6. Make eye contact\n"
                    "  7. End with a call to action\n"
                    "  8. Keep a glass of water nearby")

        if "outline" in lower or "structure" in lower:
            return ("Presentation Outline:\n\n"
                    "  Slide 1: Title + Your Name\n"
                    "  Slide 2: Problem/Question\n"
                    "  Slide 3: Why It Matters\n"
                    "  Slide 4-7: Main Points (1 per slide)\n"
                    "  Slide 8: Key Findings/Results\n"
                    "  Slide 9: Conclusion\n"
                    "  Slide 10: Q&A / Thank You\n\n"
                    "Tell me your topic and I'll help fill in the content!")

        if "nervous" in lower or "scared" in lower or "anxious" in lower:
            return ("Stage Fright Tips:\n"
                    "  1. It's normal! Even pros get nervous\n"
                    "  2. Practice deep breathing before\n"
                    "  3. Focus on your message, not yourself\n"
                    "  4. Start by looking at friendly faces\n"
                    "  5. Remember: the audience wants you to succeed!\n"
                    "  6. Power pose for 2 minutes before (arms up)\n"
                    "  7. Arrive early, get comfortable with the space")

        return ("Presentation Helper:\n"
                "  'presentation tips' - speaking advice\n"
                "  'presentation outline' - slide structure\n"
                "  'nervous about presentation' - stage fright help\n"
                "  Or describe your topic for a custom outline!")
