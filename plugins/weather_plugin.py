"""Weather Plugin - Current weather and forecast."""

from plugins.plugin_loader import PluginBase
import re


class WeatherPlugin(PluginBase):
    name = "weather"
    description = "Check current weather and forecast"
    triggers = ["weather", "temperature", "forecast", "rain", "sunny",
                 "humidity", "wind", "climate"]

    async def execute(self, command: str, context: dict = None) -> str:
        city = "Dhaka"
        city_match = re.search(r'(?:weather|forecast|temperature)\s+(?:in|for|at)\s+(.+)', command, re.IGNORECASE)
        if city_match:
            city = city_match.group(1).strip()

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"https://wttr.in/{city}?format=j1")
                if resp.status_code == 200:
                    data = resp.json()
                    current = data["current_condition"][0]
                    temp = current["temp_C"]
                    feels = current["FeelsLikeC"]
                    desc = current["weatherDesc"][0]["value"]
                    humidity = current["humidity"]
                    wind = current["windspeedKmph"]
                    return (f"Weather in {city}: {desc}\n"
                            f"  Temperature: {temp}°C (feels like {feels}°C)\n"
                            f"  Humidity: {humidity}% | Wind: {wind} km/h")
        except Exception:
            pass
        return f"Could not fetch weather for {city}. Check your internet connection."
