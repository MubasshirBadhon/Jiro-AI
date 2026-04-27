"""QR Code Plugin - Generate QR codes for text and URLs."""

from plugins.plugin_loader import PluginBase
import re


class QRCodePlugin(PluginBase):
    name = "qr_code"
    description = "Generate QR codes for text and URLs"
    triggers = ["qr code", "qr", "generate qr", "make qr"]

    async def execute(self, command: str, context: dict = None) -> str:
        text = re.sub(r'(?:qr code|generate qr|make qr|qr)\s*:?\s*(?:for)?\s*', '', command, flags=re.IGNORECASE).strip()
        if not text:
            return "What should the QR code contain? Say: 'qr code https://example.com'"

        try:
            import httpx
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={text}"

            # Try to open in browser
            import webbrowser
            webbrowser.open(qr_url)
            return f"QR code generated and opened in browser!\nURL: {qr_url}"
        except Exception:
            return f"Generate QR code at:\nhttps://api.qrserver.com/v1/create-qr-code/?size=200x200&data={text}"
