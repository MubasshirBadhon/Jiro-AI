"""Internet Speed Test Plugin - Quick bandwidth test."""

from plugins.plugin_loader import PluginBase
import time


class InternetSpeedtestPlugin(PluginBase):
    name = "internet_speedtest"
    description = "Quick internet speed test"
    triggers = ["speed test", "speedtest", "internet speed", "bandwidth",
                 "how fast is my internet", "download speed"]

    async def execute(self, command: str, context: dict = None) -> str:
        results = []
        try:
            import httpx

            # Download test
            sizes = [100000, 500000, 1000000]
            speeds = []
            async with httpx.AsyncClient(timeout=30) as client:
                for size in sizes:
                    start = time.time()
                    resp = await client.get(f"https://speed.cloudflare.com/__down?bytes={size}")
                    elapsed = time.time() - start
                    if elapsed > 0:
                        speed = (size * 8) / (elapsed * 1000000)
                        speeds.append(speed)

            if speeds:
                avg_speed = sum(speeds) / len(speeds)
                results.append(f"Download: ~{avg_speed:.1f} Mbps")

                if avg_speed < 5:
                    results.append("Speed: Slow (basic browsing)")
                elif avg_speed < 25:
                    results.append("Speed: Moderate (HD streaming)")
                elif avg_speed < 100:
                    results.append("Speed: Fast (multiple devices)")
                else:
                    results.append("Speed: Very Fast!")

            # Latency test
            start = time.time()
            async with httpx.AsyncClient(timeout=5) as client:
                await client.get("https://1.1.1.1")
            latency = (time.time() - start) * 1000
            results.append(f"Latency: {latency:.0f}ms")

        except Exception as e:
            return f"Speed test failed: {e}"

        return "Internet Speed Test:\n  " + "\n  ".join(results)
