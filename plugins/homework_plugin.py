"""Homework Helper Plugin - Help with assignments, explanations, problem solving."""

from plugins.plugin_loader import PluginBase
import re


class HomeworkPlugin(PluginBase):
    name = "homework"
    description = "Help with homework, explain concepts, solve problems"
    triggers = ["homework", "explain", "how does", "what is", "why does",
                 "solve", "help me understand", "teach me", "example of"]

    async def execute(self, command: str, context: dict = None) -> str:
        return (
            f"I'll help you with that! Let me think about: '{command}'\n\n"
            f"(This will be processed by my AI brain for a detailed explanation. "
            f"Ask me in conversation mode for the best results!)"
        )
