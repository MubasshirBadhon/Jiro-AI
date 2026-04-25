"""Self-Fixer - Auto-diagnose and fix issues in Jiro AI.

If something breaks, Jiro tries to fix it using:
1. Built-in fix strategies (dependency install, config repair, etc.)
2. Offline LLM (if available) for code-level fixes
3. Online AI APIs for complex debugging
"""

import importlib
import logging
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.self_fixer")

PROJECT_ROOT = Path(__file__).parent.parent


class SelfFixer:
    """Auto-diagnoses and fixes issues in Jiro AI components."""

    def __init__(self, config: dict, ai_engine=None):
        self._config = config
        self._ai_engine = ai_engine
        self._fix_log: list[dict] = []

    async def diagnose_and_fix(self, error: Exception, context: str = "") -> dict:
        """Attempt to diagnose and fix an error automatically."""
        error_type = type(error).__name__
        error_msg = str(error)
        tb = traceback.format_exc()

        logger.info("Self-fixer: Diagnosing %s: %s", error_type, error_msg)

        result = {"error": error_msg, "type": error_type, "fixed": False, "action": ""}

        fix_strategies = [
            self._fix_import_error,
            self._fix_file_not_found,
            self._fix_permission_error,
            self._fix_connection_error,
            self._fix_json_error,
            self._fix_audio_error,
        ]

        for strategy in fix_strategies:
            fix_result = await strategy(error, error_msg, context)
            if fix_result["handled"]:
                result.update(fix_result)
                self._fix_log.append(result)
                return result

        if self._ai_engine:
            ai_fix = await self._ask_ai_for_fix(error_type, error_msg, tb, context)
            if ai_fix:
                result["action"] = f"AI suggested: {ai_fix}"
                result["ai_suggestion"] = ai_fix

        self._fix_log.append(result)
        return result

    async def _fix_import_error(self, error, msg: str, context: str) -> dict:
        """Fix missing module imports by installing them."""
        if not isinstance(error, (ImportError, ModuleNotFoundError)):
            return {"handled": False}

        module_name = msg.split("'")[1] if "'" in msg else msg.split()[-1]

        package_map = {
            "cv2": "opencv-python-headless",
            "PIL": "Pillow",
            "fitz": "PyMuPDF",
            "sklearn": "scikit-learn",
            "yaml": "pyyaml",
            "gi": "PyGObject",
            "win32api": "pywin32",
            "win32gui": "pywin32",
            "pynput": "pynput",
            "mss": "mss",
            "edge_tts": "edge-tts",
            "sounddevice": "sounddevice",
            "pyaudio": "PyAudio",
        }

        package = package_map.get(module_name, module_name)
        logger.info("Self-fixer: Installing missing package '%s'...", package)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                logger.info("Self-fixer: Successfully installed %s", package)
                return {
                    "handled": True,
                    "fixed": True,
                    "action": f"Installed missing package: {package}",
                }
            else:
                return {
                    "handled": True,
                    "fixed": False,
                    "action": f"Failed to install {package}: {result.stderr[:200]}",
                }
        except subprocess.TimeoutExpired:
            return {"handled": True, "fixed": False, "action": f"Timeout installing {package}"}

    async def _fix_file_not_found(self, error, msg: str, context: str) -> dict:
        if not isinstance(error, FileNotFoundError):
            return {"handled": False}

        if "config.json" in msg:
            self._create_default_config()
            return {"handled": True, "fixed": True, "action": "Created default config.json"}

        if "data" in msg or "memory" in msg:
            for d in ["data/memory", "data/recordings", "data/models", "data/logs"]:
                (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)
            return {"handled": True, "fixed": True, "action": "Created missing data directories"}

        if "ffmpeg" in msg or "ffplay" in msg:
            return {
                "handled": True,
                "fixed": False,
                "action": "ffmpeg not found. Install it: winget install ffmpeg",
            }

        return {"handled": False}

    async def _fix_permission_error(self, error, msg: str, context: str) -> dict:
        if not isinstance(error, PermissionError):
            return {"handled": False}
        return {
            "handled": True,
            "fixed": False,
            "action": "Permission denied. Try running as administrator or check file permissions.",
        }

    async def _fix_connection_error(self, error, msg: str, context: str) -> dict:
        connection_errors = ("ConnectionError", "ConnectError", "TimeoutException",
                             "ConnectTimeout", "ReadTimeout")
        if type(error).__name__ not in connection_errors:
            return {"handled": False}

        return {
            "handled": True,
            "fixed": False,
            "action": "Network connection error. Check your internet connection and try again.",
        }

    async def _fix_json_error(self, error, msg: str, context: str) -> dict:
        if not isinstance(error, (json.JSONDecodeError if hasattr(error, '__module__') else type(None),)):
            try:
                import json
                if not isinstance(error, json.JSONDecodeError):
                    return {"handled": False}
            except Exception:
                return {"handled": False}

        if "config.json" in context:
            self._create_default_config()
            return {"handled": True, "fixed": True, "action": "Repaired corrupted config.json"}

        return {"handled": True, "fixed": False, "action": f"JSON parse error in {context}"}

    async def _fix_audio_error(self, error, msg: str, context: str) -> dict:
        audio_keywords = ["portaudio", "audio", "microphone", "sounddevice", "alsa"]
        if not any(kw in msg.lower() for kw in audio_keywords):
            return {"handled": False}

        return {
            "handled": True,
            "fixed": False,
            "action": (
                "Audio system error. On Windows, install PortAudio or use '--cli' mode. "
                "If using voice, ensure a microphone is connected."
            ),
        }

    async def _ask_ai_for_fix(self, error_type: str, error_msg: str,
                               traceback_str: str, context: str) -> Optional[str]:
        """Ask AI for help fixing an error."""
        if not self._ai_engine:
            return None

        try:
            prompt = (
                f"Jiro AI encountered an error. Suggest a concise fix.\n"
                f"Error: {error_type}: {error_msg}\n"
                f"Context: {context}\n"
                f"Traceback (last 5 lines):\n"
                f"{chr(10).join(traceback_str.strip().split(chr(10))[-5:])}"
            )

            if hasattr(self._ai_engine, 'process'):
                response = await self._ai_engine.process(prompt)
                return response[:500]
        except Exception:
            pass
        return None

    def _create_default_config(self) -> None:
        """Create a default config.json."""
        import json
        default = {
            "assistant_name": "Jiro",
            "wake_word": "jiro",
            "language": "en",
            "api_keys": {"nvidia": "", "huggingface": "", "groq": "", "gemini": "", "openrouter": ""},
            "supabase": {"backend_url": "", "anon_key": ""},
            "models": {
                "nvidia_understanding": "meta/llama-3.1-70b-instruct",
                "groq_generation": "llama-3.1-70b-versatile",
                "gemini_generation": "gemini-2.0-flash",
            },
            "tts": {"voice": "en-US-GuyNeural", "rate": "+0%"},
            "stt": {"model": "whisper-large-v3"},
        }
        with open(PROJECT_ROOT / "config.json", "w") as f:
            json.dump(default, f, indent=4)

    def get_fix_log(self) -> list[dict]:
        return list(self._fix_log)

    async def fix_plugin(self, plugin_path: Path, error: Exception) -> dict:
        """Attempt to fix a broken plugin."""
        logger.info("Attempting to fix plugin: %s", plugin_path.name)

        if isinstance(error, (ImportError, ModuleNotFoundError)):
            fix = await self._fix_import_error(error, str(error), f"plugin:{plugin_path.name}")
            return fix

        if self._ai_engine:
            try:
                code = plugin_path.read_text()
                prompt = (
                    f"Fix this Python plugin code. Error: {error}\n\n"
                    f"```python\n{code[:3000]}\n```\n\n"
                    f"Return ONLY the fixed Python code, nothing else."
                )
                fixed_code = await self._ai_engine.process(prompt)

                if "```python" in fixed_code:
                    fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
                elif "```" in fixed_code:
                    fixed_code = fixed_code.split("```")[1].split("```")[0].strip()

                if "class " in fixed_code and "PluginBase" in fixed_code:
                    backup = plugin_path.with_suffix(".py.bak")
                    plugin_path.rename(backup)
                    plugin_path.write_text(fixed_code)

                    try:
                        spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        logger.info("Plugin fixed successfully: %s", plugin_path.name)
                        backup.unlink()
                        return {"handled": True, "fixed": True, "action": "AI fixed the plugin code"}
                    except Exception:
                        plugin_path.unlink()
                        backup.rename(plugin_path)
                        return {"handled": True, "fixed": False, "action": "AI fix didn't work, restored backup"}
            except Exception as e:
                logger.error("AI fix attempt failed: %s", e)

        return {"handled": True, "fixed": False, "action": "Could not auto-fix plugin"}
