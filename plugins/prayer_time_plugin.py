"""Prayer Time Plugin - Islamic prayer times based on location."""

from plugins.plugin_loader import PluginBase


class PrayerTimePlugin(PluginBase):
    name = "prayer_time"
    description = "Get Islamic prayer times for your location"
    triggers = ["prayer time", "namaz time", "salah", "fajr", "zuhr", "asr",
                 "maghrib", "isha", "prayer", "namaz"]

    async def execute(self, command: str, context: dict = None) -> str:
        import re
        city = "Dhaka"
        country = "Bangladesh"
        match = re.search(r'(?:in|for|at)\s+(.+)', command, re.IGNORECASE)
        if match:
            city = match.group(1).strip()

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=1"
                )
                if resp.status_code == 200:
                    timings = resp.json()["data"]["timings"]
                    return (f"Prayer Times ({city}):\n\n"
                            f"  Fajr:    {timings['Fajr']}\n"
                            f"  Sunrise: {timings['Sunrise']}\n"
                            f"  Dhuhr:   {timings['Dhuhr']}\n"
                            f"  Asr:     {timings['Asr']}\n"
                            f"  Maghrib: {timings['Maghrib']}\n"
                            f"  Isha:    {timings['Isha']}")
        except Exception:
            pass
        return f"Could not fetch prayer times for {city}. Check internet connection."
