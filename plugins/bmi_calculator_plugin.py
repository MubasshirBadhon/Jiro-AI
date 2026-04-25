"""BMI Calculator Plugin - Calculate Body Mass Index."""

from plugins.plugin_loader import PluginBase
import re


class BMICalculatorPlugin(PluginBase):
    name = "bmi_calculator"
    description = "Calculate BMI and health recommendations"
    triggers = ["bmi", "body mass index", "am i overweight", "healthy weight"]

    async def execute(self, command: str, context: dict = None) -> str:
        # Try to extract height and weight
        h_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cm|m)', command.lower())
        w_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg|lbs?)', command.lower())

        if h_match and w_match:
            height = float(h_match.group(1))
            weight = float(w_match.group(1))
            if "cm" in command.lower():
                height /= 100
            if "lb" in command.lower():
                weight *= 0.453592

            bmi = weight / (height ** 2)
            if bmi < 18.5: category = "Underweight"
            elif bmi < 25: category = "Normal weight"
            elif bmi < 30: category = "Overweight"
            else: category = "Obese"

            return (f"Your BMI: {bmi:.1f} ({category})\n\n"
                    f"  Underweight: < 18.5\n"
                    f"  Normal: 18.5 - 24.9\n"
                    f"  Overweight: 25 - 29.9\n"
                    f"  Obese: 30+")

        return ("BMI Calculator:\n"
                "  Provide height and weight:\n"
                "  'BMI 170cm 65kg'\n"
                "  'BMI 5.7ft 150lbs'")
