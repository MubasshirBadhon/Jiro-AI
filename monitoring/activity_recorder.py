"""Activity Recorder - Full activity logger for self-training.

Records all tracked activities for pattern analysis and self-improvement.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.monitor.activity")

ACTIVITY_LOG = Path(__file__).parent.parent / "data" / "memory" / "activity_log.json"


class ActivityRecorder:
    """Records and analyzes user activity patterns."""

    def __init__(self, config: dict):
        self._config = config
        self._log: list[dict] = []
        self._topics: list[dict] = []
        self._load()

    def _load(self) -> None:
        if ACTIVITY_LOG.exists():
            try:
                with open(ACTIVITY_LOG, "r") as f:
                    data = json.load(f)
                self._log = data.get("log", [])
                self._topics = data.get("topics", [])
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self) -> None:
        ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVITY_LOG, "w") as f:
            json.dump({"log": self._log[-2000:], "topics": self._topics[-500:]}, f, indent=2, default=str)

    def record(self, activity: dict) -> None:
        self._log.append(activity)
        window = activity.get("window", "")
        if self._is_study(window):
            topic = self._extract_topic(window)
            if topic:
                self._topics.append({"topic": topic, "timestamp": datetime.now().isoformat(), "quizzed": False})
        self._save()

    def _is_study(self, title: str) -> bool:
        indicators = ["youtube", "wikipedia", "khan academy", "coursera", "udemy",
                       "arxiv", "tutorial", "learn", "documentation", "docs", "article"]
        return any(i in title.lower() for i in indicators)

    def _extract_topic(self, title: str) -> Optional[str]:
        noise = ["youtube", "google chrome", "firefox", "edge", "mozilla", "- ", "| "]
        topic = title
        for n in noise:
            topic = topic.replace(n, "").replace(n.title(), "")
        topic = topic.strip(" -|")
        return topic if len(topic) > 3 else None

    def get_unquizzed_topics(self) -> list[dict]:
        return [t for t in self._topics if not t.get("quizzed")]

    def mark_quizzed(self, topic: str) -> None:
        for t in self._topics:
            if t["topic"] == topic:
                t["quizzed"] = True
        self._save()

    def get_daily_stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        today_acts = [a for a in self._log if a.get("timestamp", "").startswith(today)]
        cats = defaultdict(float)
        for a in today_acts:
            cats[a.get("category", "neutral")] += a.get("duration", 0)
        return {
            "total": len(today_acts),
            "productive_min": round(cats.get("productive", 0) / 60, 1),
            "distraction_min": round(cats.get("distraction", 0) / 60, 1),
            "study_min": round(cats.get("study", 0) / 60, 1),
        }

    def get_app_usage(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        usage = defaultdict(float)
        for a in self._log:
            if a.get("timestamp", "").startswith(today):
                usage[a.get("window", "Unknown")] += a.get("duration", 0)
        return {k: round(v / 60, 1) for k, v in sorted(usage.items(), key=lambda x: -x[1])}
