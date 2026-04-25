"""Calculator Plugin - Math calculations and unit conversions."""

from plugins.plugin_loader import PluginBase
import math
import re


class CalculatorPlugin(PluginBase):
    name = "calculator"
    description = "Calculate math expressions, unit conversions, percentages"
    triggers = ["calculate", "calc", "math", "what is", "how much is", "convert",
                 "percentage", "percent", "square root", "power", "factorial"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Percentage calculations
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)', lower)
        if pct_match:
            pct, num = float(pct_match.group(1)), float(pct_match.group(2))
            result = (pct / 100) * num
            return f"{pct}% of {num} = {result}"

        pct_match2 = re.search(r'(\d+(?:\.\d+)?)\s*(?:is\s+)?what\s*%\s*of\s*(\d+(?:\.\d+)?)', lower)
        if pct_match2:
            part, whole = float(pct_match2.group(1)), float(pct_match2.group(2))
            if whole != 0:
                return f"{part} is {(part/whole)*100:.2f}% of {whole}"

        # Square root
        sqrt_match = re.search(r'(?:square root|sqrt)\s*(?:of\s+)?(\d+(?:\.\d+)?)', lower)
        if sqrt_match:
            n = float(sqrt_match.group(1))
            return f"√{n} = {math.sqrt(n):.4f}"

        # Factorial
        fact_match = re.search(r'(?:factorial|fact)\s*(?:of\s+)?(\d+)', lower)
        if fact_match:
            n = int(fact_match.group(1))
            if n <= 170:
                return f"{n}! = {math.factorial(n)}"
            return "Number too large for factorial"

        # Power
        pow_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:to the power|power|\^|raised to)\s*(\d+(?:\.\d+)?)', lower)
        if pow_match:
            base, exp = float(pow_match.group(1)), float(pow_match.group(2))
            return f"{base}^{exp} = {base**exp}"

        # General math expression
        expr = re.sub(r'(?:calculate|calc|what is|how much is|compute)\s*', '', lower).strip()
        expr = expr.replace('x', '*').replace('×', '*').replace('÷', '/')
        try:
            expr_clean = re.sub(r'[^0-9+\-*/().%^ ]', '', expr)
            if expr_clean:
                result = eval(expr_clean)
                return f"{expr_clean} = {result}"
        except Exception:
            pass

        return "I couldn't calculate that. Try: 'calculate 2 + 2' or '15% of 200'"
