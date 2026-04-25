"""Screenshot Plugin - Take and save screenshots."""

from plugins.plugin_loader import PluginBase
from datetime import datetime
from pathlib import Path


class ScreenshotPlugin(PluginBase):
    name = "screenshot"
    description = "Take screenshots of your screen"
    triggers = ["screenshot", "capture screen", "take screenshot", "screen capture",
                 "print screen", "snap screen"]

    async def execute(self, command: str, context: dict = None) -> str:
        save_dir = Path(__file__).parent.parent / "data" / "recordings" / "screenshots"
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = save_dir / filename

        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=str(filepath))
            return f"Screenshot saved: {filepath}"
        except ImportError:
            return "Screenshot requires 'mss' package. Installing... Run again after install."
        except Exception as e:
            return f"Could not take screenshot: {e}"
