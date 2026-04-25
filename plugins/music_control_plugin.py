"""Music Control Plugin - Control system media playback."""

from plugins.plugin_loader import PluginBase
import platform, subprocess


class MusicControlPlugin(PluginBase):
    name = "music_control"
    description = "Control music and media playback"
    triggers = ["play music", "pause music", "next song", "stop music",
                 "volume", "mute", "unmute", "media"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if platform.system() != "Windows":
            return "Media control is currently Windows-only. Use your media player directly."

        try:
            import ctypes
            VK_MEDIA_PLAY_PAUSE = 0xB3
            VK_MEDIA_NEXT = 0xB0
            VK_MEDIA_PREV = 0xB1
            VK_VOLUME_UP = 0xAF
            VK_VOLUME_DOWN = 0xAE
            VK_VOLUME_MUTE = 0xAD

            if any(w in lower for w in ["pause", "play", "resume"]):
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)
                return "Toggled play/pause"
            elif "next" in lower or "skip" in lower:
                ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT, 0, 2, 0)
                return "Skipped to next track"
            elif "previous" in lower or "prev" in lower or "back" in lower:
                ctypes.windll.user32.keybd_event(VK_MEDIA_PREV, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_MEDIA_PREV, 0, 2, 0)
                return "Previous track"
            elif "mute" in lower:
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
                return "Toggled mute"
            elif "volume up" in lower:
                for _ in range(5):
                    ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
                return "Volume up"
            elif "volume down" in lower:
                for _ in range(5):
                    ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                return "Volume down"
        except Exception as e:
            return f"Media control error: {e}"

        return ("Media commands:\n"
                "  'play/pause music'\n"
                "  'next song' / 'previous song'\n"
                "  'volume up' / 'volume down'\n"
                "  'mute'")
