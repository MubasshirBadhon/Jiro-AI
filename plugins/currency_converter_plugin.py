"""Currency Converter Plugin - Convert between currencies."""

from plugins.plugin_loader import PluginBase
import re

STATIC_RATES = {
    "USD": 1.0, "BDT": 110.0, "EUR": 0.92, "GBP": 0.79,
    "INR": 83.0, "JPY": 149.0, "CNY": 7.24, "AUD": 1.53,
    "CAD": 1.36, "SGD": 1.34, "MYR": 4.69, "SAR": 3.75,
}


class CurrencyConverterPlugin(PluginBase):
    name = "currency_converter"
    description = "Convert between currencies"
    triggers = ["currency", "exchange rate", "usd to bdt", "dollar to taka",
                 "convert currency", "taka to dollar", "how much in"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        match = re.search(r'(\d+(?:\.\d+)?)\s*(\w+)\s+(?:to|in)\s+(\w+)', lower)
        if not match:
            return ("Currency Converter:\n"
                    "  '100 usd to bdt'\n"
                    "  '5000 taka to dollar'\n"
                    "  Supported: USD, BDT, EUR, GBP, INR, JPY, CNY")

        amount = float(match.group(1))
        from_c = match.group(2).upper()
        to_c = match.group(3).upper()

        aliases = {"DOLLAR": "USD", "TAKA": "BDT", "EURO": "EUR", "POUND": "GBP",
                   "RUPEE": "INR", "YEN": "JPY", "YUAN": "CNY"}
        from_c = aliases.get(from_c, from_c)
        to_c = aliases.get(to_c, to_c)

        # Try live API first
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"https://api.exchangerate-api.com/v4/latest/{from_c}")
                if resp.status_code == 200:
                    rate = resp.json()["rates"].get(to_c)
                    if rate:
                        result = amount * rate
                        return f"{amount:,.2f} {from_c} = {result:,.2f} {to_c} (live rate: {rate:.4f})"
        except Exception:
            pass

        # Fallback to static rates
        if from_c in STATIC_RATES and to_c in STATIC_RATES:
            usd_amount = amount / STATIC_RATES[from_c]
            result = usd_amount * STATIC_RATES[to_c]
            return f"{amount:,.2f} {from_c} ≈ {result:,.2f} {to_c} (approximate rate)"

        return f"Cannot convert {from_c} to {to_c}. Supported: {', '.join(STATIC_RATES.keys())}"
