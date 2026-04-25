"""Color Picker Plugin - Color codes, conversions, palettes."""

from plugins.plugin_loader import PluginBase
import re, random

COLORS = {
    "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
    "white": "#FFFFFF", "black": "#000000", "yellow": "#FFFF00",
    "cyan": "#00FFFF", "magenta": "#FF00FF", "orange": "#FFA500",
    "purple": "#800080", "pink": "#FFC0CB", "gray": "#808080",
    "brown": "#A52A2A", "navy": "#000080", "teal": "#008080",
    "coral": "#FF7F50", "gold": "#FFD700", "lime": "#00FF00",
}


class ColorPickerPlugin(PluginBase):
    name = "color_picker"
    description = "Color codes, hex values, RGB conversions"
    triggers = ["color", "colour", "hex", "rgb", "color code", "color picker"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        for name, hex_val in COLORS.items():
            if name in lower:
                r, g, b = int(hex_val[1:3], 16), int(hex_val[3:5], 16), int(hex_val[5:7], 16)
                return f"{name.title()}:\n  HEX: {hex_val}\n  RGB: ({r}, {g}, {b})"

        hex_match = re.search(r'#([0-9a-fA-F]{6})', command)
        if hex_match:
            h = hex_match.group(1)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"Color #{h}:\n  RGB: ({r}, {g}, {b})"

        if "random" in lower or "palette" in lower:
            colors = random.sample(list(COLORS.items()), 5)
            result = "Random Color Palette:\n"
            for name, hex_val in colors:
                result += f"  {name.title()}: {hex_val}\n"
            return result

        return ("Color Picker:\n"
                "  'color red' - get color code\n"
                "  'color #FF5733' - hex to RGB\n"
                "  'random palette' - generate palette")
