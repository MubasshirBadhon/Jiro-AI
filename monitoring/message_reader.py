"""Message Reader - Reads messages and extracts tasks/reminders.

Analyzes text from screen or clipboard to extract actionable items
like calls, meetings, reminders, and tasks. Supports Bengali + English.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("jiro.monitor.messages")


class MessageReader:
    """Reads and analyzes messages to extract tasks and reminders."""

    def __init__(self, config: dict, ai_engine=None):
        self._config = config
        self._ai_engine = ai_engine

    async def analyze_message(self, text: str) -> dict:
        """Analyze a message for actionable items."""
        result = {"original": text, "actions": [], "reminders": [], "replies": []}

        local_actions = self._extract_local(text)
        result["actions"].extend(local_actions.get("actions", []))
        result["reminders"].extend(local_actions.get("reminders", []))

        if self._ai_engine and (not result["actions"] and not result["reminders"]):
            ai_result = await self._ai_analyze(text)
            result["actions"].extend(ai_result.get("actions", []))
            result["reminders"].extend(ai_result.get("reminders", []))
            result["replies"].extend(ai_result.get("replies", []))

        return result

    def _extract_local(self, text: str) -> dict:
        """Extract actions from text using pattern matching."""
        actions = []
        reminders = []
        text_lower = text.lower()

        call_patterns = [
            r'call\s+(?:me\s+)?(?:at\s+)?(\d{1,2})\s*(?::\d{2})?\s*(am|pm|AM|PM)?',
            r'call\s+dio\s+(\d{1,2})\s*(?:tay|ta|টায়)',
            r'call\s+dibo\s+(\d{1,2})\s*(?:tay|ta)',
            r'(\d{1,2})\s*(?:tay|ta|টায়)\s*call\s*(?:dio|dibo|korbo)',
        ]
        for pattern in call_patterns:
            match = re.search(pattern, text_lower)
            if match:
                hour = int(match.group(1))
                now = datetime.now()
                if hour <= 12 and now.hour >= hour:
                    hour += 12
                target = now.replace(hour=hour % 24, minute=0, second=0)
                if target <= now:
                    target += timedelta(days=1)
                reminders.append({
                    "type": "call",
                    "time": target.isoformat(),
                    "message": text,
                    "source": "message",
                })

        bangla_time_map = {
            "bikal": 16, "bikale": 16, "bikalei": 16,
            "shokal": 8, "sokal": 8,
            "raat": 21, "raate": 21,
            "dupur": 12, "dupure": 12,
        }

        for word, hour in bangla_time_map.items():
            if word in text_lower:
                if any(a in text_lower for a in ["call", "remind", "janabo", "dibo"]):
                    now = datetime.now()
                    target = now.replace(hour=hour, minute=0, second=0)
                    if target <= now:
                        target += timedelta(days=1)
                    reminders.append({
                        "type": "reminder",
                        "time": target.isoformat(),
                        "message": text,
                        "source": "bangla_message",
                    })
                break

        if any(w in text_lower for w in ["free acho", "free aso", "busy"]):
            actions.append({
                "type": "check_schedule",
                "message": text,
            })

        return {"actions": actions, "reminders": reminders}

    async def _ai_analyze(self, text: str) -> dict:
        """Use AI to analyze message for deeper understanding."""
        if not self._ai_engine:
            return {"actions": [], "reminders": [], "replies": []}

        try:
            prompt = (
                f"Analyze this message and extract any actionable items. "
                f"Return JSON with: actions (list), reminders (list with type/time/message), "
                f"replies (suggested reply list). The message:\n\n{text}"
            )
            response = await self._ai_engine.process(prompt)

            import json
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning("AI message analysis failed: %s", e)

        return {"actions": [], "reminders": [], "replies": []}
