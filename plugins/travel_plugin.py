"""Travel Helper Plugin - Packing lists, travel tips."""

from plugins.plugin_loader import PluginBase


class TravelPlugin(PluginBase):
    name = "travel"
    description = "Travel packing lists, tips, and information"
    triggers = ["travel", "packing list", "trip", "vacation", "flight",
                 "pack", "traveling"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if any(w in lower for w in ["pack", "list", "what to bring"]):
            return ("Packing Checklist:\n\n"
                    "Essentials:\n"
                    "  [ ] Passport/ID\n"
                    "  [ ] Phone + charger\n"
                    "  [ ] Cash + cards\n"
                    "  [ ] Tickets/bookings\n"
                    "  [ ] Medications\n\n"
                    "Clothes:\n"
                    "  [ ] Underwear (days + 1 extra)\n"
                    "  [ ] Outfits for each day\n"
                    "  [ ] Sleepwear\n"
                    "  [ ] Comfortable shoes\n\n"
                    "Tech:\n"
                    "  [ ] Laptop + charger\n"
                    "  [ ] Power bank\n"
                    "  [ ] Earphones\n"
                    "  [ ] Universal adapter\n\n"
                    "Toiletries:\n"
                    "  [ ] Toothbrush + paste\n"
                    "  [ ] Deodorant\n"
                    "  [ ] Sunscreen")

        return ("Travel Helper:\n"
                "  'packing list' - travel checklist\n"
                "  Ask me about any destination!")
