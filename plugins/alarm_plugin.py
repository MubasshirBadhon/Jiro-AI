"""Alarm Plugin - Bengali + English natural language alarms."""

from plugins.plugin_loader import PluginBase


class AlarmPlugin(PluginBase):
    name = "alarm"
    description = "Set alarms using natural language (Bengali + English)"
    triggers = ["alarm", "remind", "timer", "wake", "call dio", "call dibo"]
    version = "1.0.0"

    async def execute(self, command, context=None):
        try:
            from automation.alarm_manager import AlarmManager
            am = AlarmManager(self.config)
            alarm = am.set_alarm(command)
            if alarm:
                from datetime import datetime
                t = datetime.fromisoformat(alarm["time"])
                return f"Alarm set for {t.strftime('%I:%M %p on %B %d')}!"
            return "I couldn't understand the time. Try: 'set alarm for 5 PM' or '5 tay alarm dio'"
        except Exception as e:
            return f"Alarm error: {e}"
