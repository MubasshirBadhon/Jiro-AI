"""Dashboard - Monitoring transparency view.

Shows what Jiro is monitoring, productivity stats,
and system status in a transparent, informative way.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("jiro.ui.dashboard")


class Dashboard:
    """Provides monitoring transparency and status information."""

    def __init__(self, config: dict, activity_recorder=None,
                 schedule_manager=None, alarm_manager=None):
        self._config = config
        self._activity = activity_recorder
        self._schedule = schedule_manager
        self._alarms = alarm_manager

    def get_status(self) -> dict:
        """Get current system status."""
        status = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_enabled": self._config.get("monitoring", {}).get("enabled", False),
            "proactive_enabled": self._config.get("proactive", {}).get("enabled", False),
        }

        if self._activity:
            status["daily_stats"] = self._activity.get_daily_stats()
            status["app_usage"] = dict(list(self._activity.get_app_usage().items())[:5])

        if self._schedule:
            status["today_events"] = len(self._schedule.get_today())

        if self._alarms:
            status["active_alarms"] = len(self._alarms.list_alarms())

        return status

    def format_dashboard(self) -> str:
        """Format dashboard for display."""
        status = self.get_status()
        lines = [
            "=" * 45,
            "  JIRO AI - DASHBOARD",
            "=" * 45,
            f"  Time: {datetime.now().strftime('%I:%M %p, %B %d %Y')}",
            f"  Monitoring: {'ON' if status.get('monitoring_enabled') else 'OFF'}",
            f"  Proactive: {'ON' if status.get('proactive_enabled') else 'OFF'}",
        ]

        stats = status.get("daily_stats", {})
        if stats:
            lines.append(f"\n  Today's Activity:")
            lines.append(f"    Productive: {stats.get('productive_min', 0)} min")
            lines.append(f"    Study: {stats.get('study_min', 0)} min")
            lines.append(f"    Distraction: {stats.get('distraction_min', 0)} min")

        usage = status.get("app_usage", {})
        if usage:
            lines.append(f"\n  Top Apps:")
            for app, mins in list(usage.items())[:5]:
                lines.append(f"    {app[:30]:30s} {mins:.1f} min")

        lines.append(f"\n  Events today: {status.get('today_events', 0)}")
        lines.append(f"  Active alarms: {status.get('active_alarms', 0)}")
        lines.append("=" * 45)
        return "\n".join(lines)
