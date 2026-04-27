"""First Aid Guide Plugin - Emergency first aid information."""

from plugins.plugin_loader import PluginBase

FIRST_AID = {
    "burn": "1. Cool under running water for 10+ min\n2. Do NOT use ice or butter\n3. Cover with clean cloth\n4. Take pain relief if needed\n5. See doctor for severe burns",
    "cut": "1. Apply firm pressure with clean cloth\n2. Clean wound with water\n3. Apply antiseptic\n4. Cover with bandage\n5. See doctor if deep or won't stop bleeding",
    "choking": "1. Encourage coughing\n2. Give 5 back blows between shoulder blades\n3. Give 5 abdominal thrusts (Heimlich)\n4. Alternate back blows and thrusts\n5. Call emergency if not relieved",
    "nosebleed": "1. Sit upright, lean slightly forward\n2. Pinch soft part of nose\n3. Hold for 10-15 minutes\n4. Do NOT tilt head back\n5. Apply ice pack on bridge of nose",
    "sprain": "RICE method:\n  R - Rest the injured area\n  I - Ice for 20 min every hour\n  C - Compress with elastic bandage\n  E - Elevate above heart level",
    "fainting": "1. Lay person flat, elevate legs\n2. Loosen tight clothing\n3. Check breathing\n4. If no recovery in 1 min, call emergency\n5. When conscious, give water slowly",
    "allergic": "1. Use epinephrine auto-injector if available\n2. Call emergency services\n3. Lay person flat (sitting if breathing difficulty)\n4. Loosen clothing\n5. Monitor breathing",
}


class FirstAidPlugin(PluginBase):
    name = "first_aid"
    description = "Emergency first aid information and guidance"
    triggers = ["first aid", "emergency", "burn", "bleeding", "choking",
                 "nosebleed", "sprain", "fainting", "hurt", "injured"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()
        for condition, steps in FIRST_AID.items():
            if condition in lower:
                return (f"FIRST AID - {condition.upper()}\n\n{steps}\n\n"
                        f"IMPORTANT: For serious injuries, call emergency services immediately!")

        return ("First Aid Guide:\n"
                "  Ask about: burn, cut, choking, nosebleed, sprain, fainting, allergic reaction\n\n"
                "  Emergency Numbers:\n"
                "  Bangladesh: 999\n"
                "  India: 112\n"
                "  USA: 911\n"
                "  UK: 999")
