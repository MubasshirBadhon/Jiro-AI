"""Activity Tracker for Jiro AI.

Aggregates activity data from screen monitoring and provides
insights about user behavior patterns for the proactive assistant.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.monitoring.activity")

ACTIVITY_DB = Path(__file__).parent.parent / "data" / "memory" / "activity_history.json"


class ActivityTracker:
    """Tracks and analyzes user activity patterns."""

    def __init__(self, config_manager):
        self.config = config_manager
        self._history: list[dict] = []
        self._topics: list[dict] = []
        self._load()

    def _load(self) -> None:
        if ACTIVITY_DB.exists():
            try:
                with open(ACTIVITY_DB, "r") as f:
                    data = json.load(f)
                self._history = data.get("history", [])
                self._topics = data.get("topics", [])
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self) -> None:
        ACTIVITY_DB.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVITY_DB, "w") as f:
            json.dump(
                {"history": self._history[-1000:], "topics": self._topics[-500:]},
                f, indent=2, default=str,
            )

    def record_activity(self, activity: dict) -> None:
        """Record an activity event."""
        self._history.append(activity)

        window = activity.get("window", "")
        if self._is_study_activity(window):
            topic = self._extract_topic(window)
            if topic:
                self._topics.append({
                    "topic": topic,
                    "timestamp": datetime.now().isoformat(),
                    "quizzed": False,
                })

        self._save()

    def _is_study_activity(self, window_title: str) -> bool:
        study_indicators = [
            "youtube", "wikipedia", "khan academy", "coursera",
            "udemy", "arxiv", "tutorial", "learn", "guide",
            "documentation", "docs", "article",
        ]
        return any(ind in window_title.lower() for ind in study_indicators)

    def _extract_topic(self, window_title: str) -> Optional[str]:
        """Extract study topic from window title."""
        noise_words = [
            "youtube", "google chrome", "firefox", "edge",
            "mozilla", "safari", "- ", "| ",
        ]
        topic = window_title
        for word in noise_words:
            topic = topic.replace(word, "").replace(word.title(), "")
        topic = topic.strip(" -|")
        return topic if len(topic) > 3 else None

    def get_unquizzed_topics(self) -> list[dict]:
        """Get study topics the user hasn't been quizzed on yet."""
        return [t for t in self._topics if not t.get("quizzed")]

    def mark_topic_quizzed(self, topic: str) -> None:
        """Mark a topic as quizzed."""
        for t in self._topics:
            if t["topic"] == topic:
                t["quizzed"] = True
        self._save()

    def get_daily_stats(self) -> dict:
        """Get today's activity statistics."""
        today = datetime.now().strftime("%Y-%m-%d")
        today_activities = [
            a for a in self._history if a.get("timestamp", "").startswith(today)
        ]

        categories = defaultdict(float)
        for act in today_activities:
            cat = act.get("category", "neutral")
            dur = act.get("duration", 0)
            categories[cat] += dur

        return {
            "total_activities": len(today_activities),
            "categories": dict(categories),
            "productive_minutes": round(categories.get("productive", 0) / 60, 1),
            "distraction_minutes": round(categories.get("distraction", 0) / 60, 1),
            "study_minutes": round(categories.get("study", 0) / 60, 1),
        }

    def get_pattern_insights(self) -> list[str]:
        """Analyze activity patterns and provide insights."""
        stats = self.get_daily_stats()
        insights = []

        if stats["distraction_minutes"] > 30:
            insights.append(
                f"You've spent {stats['distraction_minutes']:.0f} minutes on distractions today."
            )

        if stats["productive_minutes"] > 120:
            insights.append(
                f"Great work! {stats['productive_minutes']:.0f} minutes of productive time today."
            )

        if stats["study_minutes"] > 0:
            unquizzed = self.get_unquizzed_topics()
            if unquizzed:
                insights.append(
                    f"You studied {len(unquizzed)} topics. Ready for a quick review?"
                )

        return insights
