"""Screenshot Plugin - Take, save, and analyze screenshots using AI vision."""

from plugins.plugin_loader import PluginBase
from datetime import datetime
from pathlib import Path
import base64
import logging

logger = logging.getLogger("jiro.plugin.screenshot")


class ScreenshotPlugin(PluginBase):
    name = "screenshot"
    description = "Take and analyze screenshots of your screen"
    triggers = ["screenshot", "capture screen", "take screenshot", "screen capture",
                 "print screen", "snap screen", "what's on my screen",
                 "analyze screen", "look at my screen", "what do you see"]

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
        ])

        if wants_analysis:
            analysis = await self._analyze_with_ai(filepath, command, context)
            if analysis:
                return f"Screenshot saved: {filepath}\n\n{analysis}"

        return f"Screenshot saved: {filepath}"

    async def _analyze_with_ai(self, image_path: Path, query: str, context: dict = None) -> str:
        """Send screenshot to AI vision API for analysis."""
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            logger.error("Could not read screenshot: %s", e)
            return ""

        # Try Gemini Vision first (free tier supports images)
        result = await self._try_gemini_vision(img_b64, query, context)
        if result:
            return result

        # Try Groq Vision (llama-3.2-90b-vision)
        result = await self._try_groq_vision(img_b64, query, context)
        if result:
            return result

        return "Screenshot taken but no vision API available to analyze it. Add a Gemini or Groq API key."

    async def _try_gemini_vision(self, img_b64: str, query: str, context: dict = None) -> str:
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
            prompt = query if query else "Describe what you see on this screen in detail."

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": api_key},
                    json={
                        "contents": [{
                            "parts": [
                                {"text": f"You are Jiro AI, analyzing a screenshot. {prompt}"},
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
                logger.warning("Gemini vision error: %s", resp.status_code)
        except Exception as e:
            logger.error("Gemini vision failed: %s", e)
        return ""

    async def _try_groq_vision(self, img_b64: str, query: str, context: dict = None) -> str:
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
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}",
                                }},
                            ],
                        }],
                        "max_tokens": 1024,
                        "temperature": 0.4,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                logger.warning("Groq vision error: %s", resp.status_code)
        except Exception as e:
            logger.error("Groq vision failed: %s", e)
        return ""
