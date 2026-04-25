"""Unit Converter Plugin - Convert between units."""

from plugins.plugin_loader import PluginBase
import re

CONVERSIONS = {
    ("km", "miles"): 0.621371, ("miles", "km"): 1.60934,
    ("kg", "lbs"): 2.20462, ("lbs", "kg"): 0.453592,
    ("cm", "inches"): 0.393701, ("inches", "cm"): 2.54,
    ("m", "feet"): 3.28084, ("feet", "m"): 0.3048,
    ("celsius", "fahrenheit"): None, ("fahrenheit", "celsius"): None,
    ("liters", "gallons"): 0.264172, ("gallons", "liters"): 3.78541,
    ("gb", "mb"): 1024, ("mb", "gb"): 1/1024,
    ("tb", "gb"): 1024, ("gb", "tb"): 1/1024,
}


class UnitConverterPlugin(PluginBase):
    name = "unit_converter"
    description = "Convert between units (distance, weight, temperature, data)"
    triggers = ["convert", "how many", "to celsius", "to fahrenheit",
                 "to km", "to miles", "to kg", "to lbs"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        match = re.search(r'(\d+(?:\.\d+)?)\s*(\w+)\s+(?:to|in)\s+(\w+)', lower)
        if not match:
            return ("Convert units: '100 km to miles', '72 fahrenheit to celsius'\n"
                    "Supported: km/miles, kg/lbs, cm/inches, m/feet, C/F, liters/gallons, GB/MB/TB")

        value = float(match.group(1))
        from_unit = match.group(2).lower()
        to_unit = match.group(3).lower()

        # Temperature special case
        if from_unit in ("celsius", "c") and to_unit in ("fahrenheit", "f"):
            result = (value * 9/5) + 32
            return f"{value}°C = {result:.1f}°F"
        if from_unit in ("fahrenheit", "f") and to_unit in ("celsius", "c"):
            result = (value - 32) * 5/9
            return f"{value}°F = {result:.1f}°C"

        # Lookup conversion
        for (f, t), factor in CONVERSIONS.items():
            if factor and from_unit.startswith(f[:2]) and to_unit.startswith(t[:2]):
                result = value * factor
                return f"{value} {f} = {result:.4f} {t}"

        return f"Sorry, I don't know how to convert {from_unit} to {to_unit}"
