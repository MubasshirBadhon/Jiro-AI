"""IP Info Plugin - Get IP address and network information."""

from plugins.plugin_loader import PluginBase


class IPInfoPlugin(PluginBase):
    name = "ip_info"
    description = "Get your IP address and location info"
    triggers = ["ip address", "my ip", "what is my ip", "ip info",
                 "where am i", "my location"]

    async def execute(self, command: str, context: dict = None) -> str:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://ipapi.co/json/")
                if resp.status_code == 200:
                    data = resp.json()
                    return (f"Your Network Info:\n"
                            f"  IP: {data.get('ip', 'Unknown')}\n"
                            f"  City: {data.get('city', 'Unknown')}\n"
                            f"  Region: {data.get('region', 'Unknown')}\n"
                            f"  Country: {data.get('country_name', 'Unknown')}\n"
                            f"  ISP: {data.get('org', 'Unknown')}\n"
                            f"  Timezone: {data.get('timezone', 'Unknown')}")
        except Exception:
            pass
        return "Could not fetch IP info. Check your internet connection."
