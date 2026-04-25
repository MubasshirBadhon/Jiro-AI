"""System Info Plugin - PC specs, resource usage, disk space."""

from plugins.plugin_loader import PluginBase
import platform


class SystemInfoPlugin(PluginBase):
    name = "system_info"
    description = "Check PC specs, CPU/RAM/disk usage, battery"
    triggers = ["system info", "pc info", "cpu", "ram", "disk", "battery",
                 "memory usage", "storage", "specs", "my computer"]

    async def execute(self, command: str, context: dict = None) -> str:
        import psutil
        lower = command.lower()

        # Battery
        if "battery" in lower:
            batt = psutil.sensors_battery()
            if batt:
                status = "charging" if batt.power_plugged else "discharging"
                return f"Battery: {batt.percent}% ({status})"
            return "No battery detected (desktop PC?)"

        # CPU
        if "cpu" in lower:
            return (f"CPU: {platform.processor()}\n"
                    f"  Cores: {psutil.cpu_count()} ({psutil.cpu_count(logical=False)} physical)\n"
                    f"  Usage: {psutil.cpu_percent(interval=1)}%")

        # RAM
        if "ram" in lower or "memory" in lower:
            mem = psutil.virtual_memory()
            return (f"RAM: {mem.total / (1024**3):.1f} GB total\n"
                    f"  Used: {mem.used / (1024**3):.1f} GB ({mem.percent}%)\n"
                    f"  Free: {mem.available / (1024**3):.1f} GB")

        # Disk
        if "disk" in lower or "storage" in lower:
            partitions = psutil.disk_partitions()
            result = "Disk Usage:\n"
            for p in partitions:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    result += (f"  {p.device}: {usage.total / (1024**3):.1f} GB total, "
                               f"{usage.free / (1024**3):.1f} GB free ({usage.percent}% used)\n")
                except Exception:
                    continue
            return result

        # Full system info
        mem = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=0.5)
        result = (f"System: {platform.system()} {platform.release()}\n"
                  f"CPU: {platform.processor()} ({psutil.cpu_count()} cores) - {cpu_pct}% used\n"
                  f"RAM: {mem.used / (1024**3):.1f}/{mem.total / (1024**3):.1f} GB ({mem.percent}%)\n")
        batt = psutil.sensors_battery()
        if batt:
            result += f"Battery: {batt.percent}%\n"
        return result
