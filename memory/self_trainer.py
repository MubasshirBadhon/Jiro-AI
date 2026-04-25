"""Self Trainer - Learns from activity logs and improves over time.

Analyzes patterns in user behavior to provide better suggestions,
more accurate scheduling, and personalized assistance.
"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.memory.trainer")


class SelfTrainer:
    """Learns from user activity and improves Jiro's behavior."""

    def __init__(self, config: dict, long_term_memory=None):
        self._config = config
        self._memory = long_term_memory
        self._patterns: dict = defaultdict(list)

    def learn_from_activity(self, activity: dict) -> None:
        """Learn patterns from an activity event."""
        hour = datetime.now().hour
        category = activity.get("category", "neutral")
        window = activity.get("window", "")

        self._patterns["hourly_activity"].append({
            "hour": hour, "category": category, "window": window,
        })

        if self._memory:
            self._memory.add_pattern("activity", {
                "hour": hour, "category": category,
                "window": window[:100],
            })

    def learn_from_conversation(self, user_msg: str, jiro_response: str) -> None:
        """Learn from conversation patterns."""
        if self._memory:
            self._memory.add_pattern("conversation", {
                "user_length": len(user_msg),
                "response_length": len(jiro_response),
                "hour": datetime.now().hour,
            })

    def get_productivity_pattern(self) -> dict:
        """Analyze when the user is most productive."""
        if not self._memory:
            return {}

        patterns = self._memory.get_patterns("activity", limit=500)
        hourly = defaultdict(lambda: Counter())

        for p in patterns:
            data = p["data"]
            hour = data.get("hour", 0)
            cat = data.get("category", "neutral")
            hourly[hour][cat] += 1

        productive_hours = []
        for hour, counts in sorted(hourly.items()):
            total = sum(counts.values())
            prod = counts.get("productive", 0)
            if total > 0 and prod / total > 0.5:
                productive_hours.append(hour)

        return {
            "productive_hours": productive_hours,
            "most_productive": max(hourly.items(), key=lambda x: x[1].get("productive", 0))[0]
            if hourly else None,
        }

    def suggest_schedule(self) -> list[str]:
        """Suggest schedule improvements based on patterns."""
        suggestions = []
        pattern = self.get_productivity_pattern()

        prod_hours = pattern.get("productive_hours", [])
        if prod_hours:
            suggestions.append(
                f"You're most productive during {', '.join(f'{h}:00' for h in prod_hours[:3])}. "
                f"Try to schedule important work during these hours."
            )

        if self._memory:
            stats = self._memory.get_stats()
            if stats.get("conversations", 0) > 100:
                suggestions.append(
                    f"We've had {stats['conversations']} conversations. "
                    f"I'm getting better at understanding you!"
                )

        return suggestions

    def get_insights(self) -> str:
        """Get a summary of learned insights."""
        lines = ["Jiro AI - Learning Insights:"]
        pattern = self.get_productivity_pattern()

        if pattern.get("most_productive") is not None:
            lines.append(f"  Peak productivity hour: {pattern['most_productive']}:00")

        if self._memory:
            stats = self._memory.get_stats()
            lines.append(f"  Total conversations: {stats.get('conversations', 0)}")
            lines.append(f"  Learned patterns: {stats.get('patterns', 0)}")

        suggestions = self.suggest_schedule()
        if suggestions:
            lines.append("\n  Suggestions:")
            for s in suggestions:
                lines.append(f"    - {s}")

        return "\n".join(lines)
