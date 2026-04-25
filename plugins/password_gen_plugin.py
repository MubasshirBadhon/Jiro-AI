"""Password Generator Plugin - Generate secure passwords."""

from plugins.plugin_loader import PluginBase
import random
import string
import re


class PasswordGenPlugin(PluginBase):
    name = "password_gen"
    description = "Generate secure random passwords"
    triggers = ["password", "generate password", "random password", "secure password"]

    async def execute(self, command: str, context: dict = None) -> str:
        length = 16
        len_match = re.search(r'(\d+)', command)
        if len_match:
            length = max(8, min(128, int(len_match.group(1))))

        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.SystemRandom().choice(chars) for _ in range(length))

        pin = ''.join(random.SystemRandom().choice(string.digits) for _ in range(6))
        passphrase_words = ["correct", "horse", "battery", "staple", "thunder",
                           "wizard", "dragon", "phoenix", "crystal", "shadow",
                           "quantum", "nebula", "arctic", "ember", "cosmic"]
        phrase = '-'.join(random.sample(passphrase_words, 4))

        return (f"Generated passwords ({length} chars):\n"
                f"  Strong: {password}\n"
                f"  PIN: {pin}\n"
                f"  Passphrase: {phrase}\n"
                f"\n  Tip: Use a password manager to store these!")
