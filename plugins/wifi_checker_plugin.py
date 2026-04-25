"""WiFi Checker Plugin - Check internet connectivity and speed."""

from plugins.plugin_loader import PluginBase
import time


class WifiCheckerPlugin(PluginBase):
    name = "wifi_checker"
    description = "Check internet connection and speed"
    triggers = ["wifi", "internet speed", "connection", "network", "ping",
                 "am i online", "internet check"]

    async def execute(self, command: str, context: dict = None) -> str:
        results = []

        # Connectivity check
        try:
            import httpx
            start = time.time()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://www.google.com")
                latency = (time.time() - start) * 1000
                results.append(f"Internet: Connected (latency: {latency:.0f}ms)")
        except Exception:
            results.append("Internet: NOT connected!")
            return "\n".join(results) + "\nCheck your WiFi connection."

        # Simple speed test (download a small file)
        try:
            import httpx
            start = time.time()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://speed.cloudflare.com/__down?bytes=1000000")
                elapsed = time.time() - start
                if elapsed > 0:
                    speed_mbps = (1000000 * 8) / (elapsed * 1000000)
                    results.append(f"Download speed: ~{speed_mbps:.1f} Mbps")
                    if speed_mbps < 1:
                        results.append("Speed is slow. Consider moving closer to your router.")
                    elif speed_mbps < 10:
                        results.append("Speed is okay for browsing.")
                    else:
                        results.append("Speed is good!")
        except Exception:
            results.append("Could not test speed")

        # DNS check
        try:
            import socket
            start = time.time()
            socket.getaddrinfo("google.com", 80)
            dns_time = (time.time() - start) * 1000
            results.append(f"DNS resolution: {dns_time:.0f}ms")
        except Exception:
            results.append("DNS: Issues detected")

        return "Network Status:\n  " + "\n  ".join(results)
