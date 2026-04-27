"""Screenshot Plugin - Analyze screen with LOCAL OCR first, then AI vision.

Local-first approach:
1. Try OCR (pytesseract) to extract text from screenshot - no API
2. If text found locally, use offline LLM to analyze it - no API
3. Only if local processing fails, use Gemini/Groq vision API
"""

import base64
import logging
from datetime import datetime
from pathlib import Path

from plugins.plugin_loader import PluginBase

logger = logging.getLogger("jiro.plugin.screenshot")


class ScreenshotPlugin(PluginBase):
    name = "screenshot"
    description = "Take and analyze screenshots - uses local OCR first, AI vision as fallback"
    triggers = ["screenshot", "capture screen", "take screenshot", "screen capture",
                 "print screen", "snap screen", "what's on my screen",
                 "analyze screen", "look at my screen", "what do you see",
                 "read my screen", "what am i looking at"]

    async def execute(self, command: str, context: dict = None) -> str:
        save_dir = Path(__file__).parent.parent / "data" / "recordings" / "screenshots"
        save_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = save_dir / filename

        # Take the screenshot
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=str(filepath))
        except ImportError:
            return "Screenshot requires 'mss' package. Run: pip install mss"
        except Exception as e:
            return f"Could not take screenshot: {e}"

        lower = command.lower()
        wants_analysis = any(w in lower for w in [
            "analyze", "what", "look", "see", "read", "tell me", "describe",
            "screen", "explain",
        ])

        if wants_analysis:
            # LOCAL FIRST: Try OCR to extract text without any API
            ocr_text = self._local_ocr(filepath)
            if ocr_text and len(ocr_text.strip()) > 20:
                return (f"Screenshot saved: {filepath}\n\n"
                        f"I can see this text on your screen:\n{ocr_text.strip()}")

            # Fallback: AI vision API
            analysis = await self._analyze_with_ai(filepath, command, context)
            if analysis:
                return f"Screenshot saved: {filepath}\n\n{analysis}"

            return f"Screenshot saved: {filepath}\n(No OCR or vision API available to analyze it)"

        return f"Screenshot saved: {filepath}"

    def _local_ocr(self, image_path: Path) -> str:
        """Extract text from image using local OCR (no API call)."""
        # Try pytesseract
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(str(image_path))
            text = pytesseract.image_to_string(img, lang='eng')
            if text.strip():
                return text
        except ImportError:
            logger.debug("pytesseract not installed - skipping local OCR")
        except Exception as e:
            logger.debug("OCR failed: %s", e)

        # Try easyocr
        try:
            import easyocr
            reader = easyocr.Reader(['en'], gpu=False)
            results = reader.readtext(str(image_path))
            text = " ".join([r[1] for r in results])
            if text.strip():
                return text
        except ImportError:
            pass
        except Exception as e:
            logger.debug("EasyOCR failed: %s", e)

        return ""

    async def _analyze_with_ai(self, image_path: Path, query: str, context: dict = None) -> str:
        """Send screenshot to AI vision API (fallback only)."""
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            logger.error("Could not read screenshot: %s", e)
            return ""

        result = await self._try_gemini_vision(img_b64, query)
        if result:
            return result

        result = await self._try_groq_vision(img_b64, query)
        if result:
            return result

        return ""

    async def _try_gemini_vision(self, img_b64: str, query: str) -> str:
        """Use Gemini vision to analyze image."""
        import json as _json

        config_path = Path(__file__).parent.parent / "config.json"
        try:
            config = _json.loads(config_path.read_text())
        except Exception:
            return ""

        api_key = config.get("api_keys", {}).get("gemini", "")
        if not api_key:
            return ""

        try:
            import httpx
            model = config.get("models", {}).get("gemini_generation", "gemini-2.0-flash")
            prompt = query if query else "Describe what you see on this screen."

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": api_key},
                    json={
                        "contents": [{
                            "parts": [
                                {"text": f"You are Jiro AI. {prompt}"},
                                {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                            ]
                        }],
                        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
        except Exception as e:
            logger.error("Gemini vision failed: %s", e)
        return ""

    async def _try_groq_vision(self, img_b64: str, query: str) -> str:
        """Use Groq vision model to analyze image."""
        import json as _json

        config_path = Path(__file__).parent.parent / "config.json"
        try:
            config = _json.loads(config_path.read_text())
        except Exception:
            return ""

        api_key = config.get("api_keys", {}).get("groq", "")
        if not api_key:
            return ""

        try:
            import httpx
            prompt = query if query else "Describe what you see on this screen."

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.2-90b-vision-preview",
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"You are Jiro AI. {prompt}"},
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}"}},
                            ],
                        }],
                        "max_tokens": 1024,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error("Groq vision failed: %s", e)
        return ""
