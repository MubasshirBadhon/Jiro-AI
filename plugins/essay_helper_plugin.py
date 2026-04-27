"""Essay Helper Plugin - Help structure and outline essays."""

from plugins.plugin_loader import PluginBase


class EssayHelperPlugin(PluginBase):
    name = "essay_helper"
    description = "Help structure essays, create outlines, thesis statements"
    triggers = ["essay", "thesis", "outline", "introduction", "conclusion",
                 "write essay", "essay structure", "paragraph"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if "structure" in lower or "outline" in lower:
            return ("Essay Structure:\n\n"
                    "1. Introduction (10-15%)\n"
                    "   - Hook (interesting opening)\n"
                    "   - Background context\n"
                    "   - Thesis statement\n\n"
                    "2. Body Paragraphs (70-80%)\n"
                    "   Each paragraph:\n"
                    "   - Topic sentence\n"
                    "   - Evidence/examples\n"
                    "   - Analysis\n"
                    "   - Transition\n\n"
                    "3. Conclusion (10-15%)\n"
                    "   - Restate thesis\n"
                    "   - Summarize key points\n"
                    "   - Final thought/call to action\n\n"
                    "Tell me your topic and I'll help create an outline!")

        if "thesis" in lower:
            return ("Thesis Statement Formula:\n\n"
                    "  [Topic] + [Your Position] + [Reasons]\n\n"
                    "  Example:\n"
                    "  'Social media (topic) negatively impacts student productivity (position) "
                    "because it reduces focus, disrupts sleep, and creates anxiety (reasons).'\n\n"
                    "Tell me your topic and I'll help draft a thesis!")

        if "introduction" in lower:
            return ("Introduction Writing Tips:\n"
                    "  1. Start with a hook (question, quote, or surprising fact)\n"
                    "  2. Provide context (2-3 sentences of background)\n"
                    "  3. End with your thesis statement\n"
                    "  4. Keep it 10-15% of total essay length")

        return ("Essay Helper:\n"
                "  'essay structure' - full outline template\n"
                "  'thesis statement' - how to write thesis\n"
                "  'introduction tips' - intro writing guide\n"
                "  Or ask me about any topic for essay help!")
