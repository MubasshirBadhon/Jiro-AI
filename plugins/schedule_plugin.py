"""Schedule Plugin - Calendar awareness + availability checking."""

from plugins.plugin_loader import PluginBase


class SchedulePlugin(PluginBase):
    name = "schedule"
    description = "Check schedule, availability, and manage events"
    triggers = ["schedule", "free", "busy", "calendar", "event", "available"]
    version = "1.0.0"

    async def execute(self, command, context=None):
        try:
            from automation.schedule_manager import ScheduleManager
            sm = ScheduleManager(self.config)

            cmd = command.lower()
            if "add" in cmd or "event" in cmd:
                return "Use: 'add event [title] at [time]' to add events."
            if any(w in cmd for w in ["free", "busy", "available"]):
                return sm.suggest_reply(command) + "\n\n" + sm.format_today()
            return sm.format_today()
        except Exception as e:
            return f"Schedule error: {e}"
