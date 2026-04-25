"""Email Draft Plugin - Draft professional emails."""

from plugins.plugin_loader import PluginBase
import re


class EmailDraftPlugin(PluginBase):
    name = "email_draft"
    description = "Draft professional emails, replies, and formal letters"
    triggers = ["email", "draft email", "write email", "compose email",
                 "formal letter", "write a letter"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if "sick leave" in lower or "leave" in lower:
            return ("Subject: Leave Application\n\n"
                    "Dear Sir/Ma'am,\n\n"
                    "I am writing to request leave from [date] to [date] due to [reason]. "
                    "I will ensure all pending work is completed before my leave.\n\n"
                    "I kindly request your approval.\n\n"
                    "Thank you,\n[Your Name]")

        if "thank" in lower:
            return ("Subject: Thank You\n\n"
                    "Dear [Name],\n\n"
                    "Thank you for [reason]. I truly appreciate your [help/support/time]. "
                    "Looking forward to [next steps].\n\n"
                    "Best regards,\n[Your Name]")

        if "professor" in lower or "teacher" in lower:
            return ("Subject: [Topic]\n\n"
                    "Dear Professor [Name],\n\n"
                    "I hope this email finds you well. I am [Your Name] from [Class/Section]. "
                    "I am writing regarding [reason].\n\n"
                    "[Your message here]\n\n"
                    "Thank you for your time and consideration.\n\n"
                    "Respectfully,\n[Your Name]\n[Student ID]")

        return ("I can help draft emails! Try:\n"
                "  'draft email for sick leave'\n"
                "  'draft thank you email'\n"
                "  'draft email to professor'\n"
                "  Or describe what you need: 'draft email about project submission deadline'")
