"""Productivity Plugin for Jiro AI.

Monitors active window usage, provides productivity insights,
and can warn about excessive unproductive time.
"""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.plugin_loader import PluginBase

logger = logging.getLogger("jiro.plugins.productivity")

ACTIVITY_LOG = Path(__file__).parent.parent / "data" / "memory" / "activity_log.json"


class ProductivityPlugin(PluginBase):
    name = "productivity"
    description = "Track app usage, provide productivity insights, warn about distractions"
    triggers = [
        "productivity", "screen time", "how long", "time spent",
        "distraction", "focus", "productive",
    ]
    version = "1.0.0"

    def __init__(self, config_manager, ai_engine=None):
        super().__init__(config_manager, ai_engine)
        self.activity_log: dict = defaultdict(float)
        self.session_start = datetime.now()
        self._load_log()

    def _load_log(self) -> None:
        if ACTIVITY_LOG.exists():
            with open(ACTIVITY_LOG, "r") as f:
                self.activity_log = defaultdict(float, json.load(f))

    def _save_log(self) -> None:
        ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVITY_LOG, "w") as f:
            json.dump(dict(self.activity_log), f, indent=2)

    def log_activity(self, app_name: str, duration_seconds: float) -> None:
        """Log time spent on an application."""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{today}:{app_name}"
        self.activity_log[key] += duration_seconds
        self._save_log()

    def get_today_summary(self) -> dict[str, float]:
        """Get today's app usage summary in minutes."""
        today = datetime.now().strftime("%Y-%m-%d")
        summary = {}
        for key, seconds in self.activity_log.items():
            if key.startswith(today + ":"):
                app = key.split(":", 1)[1]
                summary[app] = round(seconds / 60, 1)
        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))

    def get_distraction_time(self) -> float:
        """Get total distraction time today in minutes."""
        distraction_sites = self.config.get("monitoring.distraction_sites", [])
        today = datetime.now().strftime("%Y-%m-%d")
        total = 0.0
        for key, seconds in self.activity_log.items():
            if key.startswith(today + ":"):
                app = key.split(":", 1)[1].lower()
                if any(site in app for site in distraction_sites):
                    total += seconds
        return round(total / 60, 1)

    def should_warn(self) -> Optional[str]:
        """Check if a productivity warning should be issued."""
        threshold = self.config.get("monitoring.distraction_threshold_minutes", 15)
        distraction_mins = self.get_distraction_time()

        if distraction_mins >= threshold:
            return (
                f"You've spent {distraction_mins:.0f} minutes on distracting apps today. "
                f"Maybe it's time to focus on something productive?"
            )
        return None

    async def execute(self, command: str, context: Optional[dict] = None) -> str:
        cmd_lower = command.lower()

        if any(w in cmd_lower for w in ["summary", "report", "today", "time"]):
            return self._format_summary()

        if any(w in cmd_lower for w in ["distraction", "wasting"]):
            return self._format_distractions()

        return self._format_summary()

    def _format_summary(self) -> str:
        summary = self.get_today_summary()
        if not summary:
            return "No activity recorded today yet."

        total_mins = sum(summary.values())
        lines = [f"Today's screen time ({total_mins:.0f} min total):"]

        for app, mins in list(summary.items())[:10]:
            bar = "#" * min(int(mins / 5), 20)
            lines.append(f"  {app:30s} {mins:6.1f} min  {bar}")

        distraction = self.get_distraction_time()
        if distraction > 0:
            lines.append(f"\nDistraction time: {distraction:.0f} minutes")

        return "\n".join(lines)

    def _format_distractions(self) -> str:
        distraction_sites = self.config.get("monitoring.distraction_sites", [])
        today = datetime.now().strftime("%Y-%m-%d")

        lines = ["Distraction breakdown:"]
        for key, seconds in self.activity_log.items():
            if key.startswith(today + ":"):
                app = key.split(":", 1)[1]
                if any(site in app.lower() for site in distraction_sites):
                    mins = seconds / 60
                    lines.append(f"  {app}: {mins:.1f} minutes")

        if len(lines) == 1:
            return "No distraction time recorded today. Great job!"

        return "\n".join(lines)
