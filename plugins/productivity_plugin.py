"""Productivity Plugin - Activity tracking and insights."""

from plugins.plugin_loader import PluginBase


class ProductivityPlugin(PluginBase):
    name = "productivity"
    description = "Track and report on productivity and app usage"
    triggers = ["productivity", "stats", "activity", "usage", "dashboard"]
    version = "1.0.0"

    async def execute(self, command, context=None):
        try:
            from monitoring.activity_recorder import ActivityRecorder
            recorder = ActivityRecorder(self.config)
            stats = recorder.get_daily_stats()
            usage = recorder.get_app_usage()

            lines = [
                "Today's Productivity:",
                f"  Productive: {stats.get('productive_min', 0)} min",
                f"  Study: {stats.get('study_min', 0)} min",
                f"  Distraction: {stats.get('distraction_min', 0)} min",
            ]

            if usage:
                lines.append("\nTop Apps:")
                for app, mins in list(usage.items())[:5]:
                    lines.append(f"  {app[:30]:30s} {mins:.1f} min")

            return "\n".join(lines)
        except Exception as e:
            return f"Productivity error: {e}"
