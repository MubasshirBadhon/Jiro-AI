"""Self-Fixer - Auto-diagnose and fix issues in Jiro AI.

If something breaks, Jiro tries to fix it using:
1. Built-in fix strategies (dependency install, config repair, etc.)
2. Offline LLM (if available) for code-level fixes
3. Online AI APIs for complex debugging

Handles special cases like llama-cpp-python on Windows.
"""

import importlib
import json
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
            self._fix_encoding_error,
        ]

        for strategy in fix_strategies:
            fix_result = await strategy(error, error_msg, context)
            if fix_result["handled"]:
                result.update(fix_result)
                self._fix_log.append(result)
                if result["fixed"]:
                    logger.info("Self-fixer: Fixed! Action: %s", result["action"])
                return result

        if self._ai_engine:
            ai_fix = await self._ask_ai_for_fix(error_type, error_msg, tb, context)
            if ai_fix:
                result["action"] = f"AI suggested: {ai_fix}"
                result["ai_suggestion"] = ai_fix

        self._fix_log.append(result)
        return result

    async def startup_check(self) -> list[dict]:
        """Run startup checks and auto-fix common issues."""
        fixes = []

        # Check required packages
        required = {
            "httpx": "httpx",
            "edge_tts": "edge-tts",
            "numpy": "numpy",
            "psutil": "psutil",
        }
        optional = {
            "speech_recognition": "SpeechRecognition",
            "sounddevice": "sounddevice",
            "customtkinter": "customtkinter",
            "PIL": "Pillow",
            "mss": "mss",
            "fitz": "PyMuPDF",
        }

        for module, package in required.items():
            try:
                importlib.import_module(module)
            except ImportError:
                fix = self._install_package(package)
                fixes.append(fix)

        for module, package in optional.items():
            try:
                importlib.import_module(module)
            except ImportError:
                logger.info("Optional package '%s' not installed. Installing...", package)
                fix = self._install_package(package)
                fixes.append(fix)

        # Check directories
        for d in ["data/memory", "data/recordings/screenshots", "data/models", "data/logs"]:
            path = PROJECT_ROOT / d
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                fixes.append({"fixed": True, "action": f"Created directory: {d}"})

        # Check config.json
        config_path = PROJECT_ROOT / "config.json"
        if not config_path.exists():
            self._create_default_config()
            fixes.append({"fixed": True, "action": "Created default config.json"})

        return fixes

    def _install_package(self, package: str) -> dict:
        """Install a pip package."""
        logger.info("Installing '%s'...", package)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "-q"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                logger.info("Installed %s", package)
                return {"fixed": True, "action": f"Installed {package}"}
            else:
                logger.warning("Failed to install %s: %s", package, result.stderr[:200])
                return {"fixed": False, "action": f"Failed to install {package}"}
        except subprocess.TimeoutExpired:
            return {"fixed": False, "action": f"Timeout installing {package}"}
        except Exception as e:
            return {"fixed": False, "action": f"Error installing {package}: {e}"}

    async def install_offline_llm(self) -> dict:
        """Install llama-cpp-python with proper Windows handling."""
        logger.info("Attempting to install llama-cpp-python for offline mode...")

        # Try pre-built wheel first (faster, no build tools needed)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "llama-cpp-python",
                 "--prefer-binary", "-q"],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                return {"fixed": True, "action": "Installed llama-cpp-python (pre-built)"}
        except subprocess.TimeoutExpired:
            pass

        # Try CPU-only build
        import os
        env = os.environ.copy()
        env["CMAKE_ARGS"] = "-DGGML_BLAS=OFF"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir"],
                capture_output=True, text=True, timeout=600, env=env,
            )
            if result.returncode == 0:
                return {"fixed": True, "action": "Installed llama-cpp-python (CPU build)"}
        except subprocess.TimeoutExpired:
            pass

        return {
            "fixed": False,
            "action": (
                "Could not install llama-cpp-python. For Windows:\n"
                "1. Install Visual Studio Build Tools from https://visualstudio.microsoft.com/visual-cpp-build-tools/\n"
                "2. Then run: pip install llama-cpp-python\n"
                "Jiro will work without offline mode using API keys."
            ),
        }

    async def _fix_import_error(self, error, msg: str, context: str) -> dict:
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
            "speech_recognition": "SpeechRecognition",
            "customtkinter": "customtkinter",
            "llama_cpp": "llama-cpp-python",
        }

        package = package_map.get(module_name, module_name)

        if package == "llama-cpp-python":
            return {
                "handled": True,
                **(await self.install_offline_llm()),
            }

        result = self._install_package(package)
        result["handled"] = True
        return result

    async def _fix_file_not_found(self, error, msg: str, context: str) -> dict:
        if not isinstance(error, FileNotFoundError):
            return {"handled": False}

        if "config.json" in msg:
            self._create_default_config()
            return {"handled": True, "fixed": True, "action": "Created default config.json"}

        if "data" in msg or "memory" in msg:
            for d in ["data/memory", "data/recordings/screenshots", "data/models", "data/logs"]:
                (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)
            return {"handled": True, "fixed": True, "action": "Created missing data directories"}

        if "ffmpeg" in msg or "ffplay" in msg:
            return {
                "handled": True,
                "fixed": False,
                "action": "ffmpeg not found. Install: winget install ffmpeg (Windows) or apt install ffmpeg (Linux)",
            }

        return {"handled": False}

    async def _fix_permission_error(self, error, msg: str, context: str) -> dict:
        if not isinstance(error, PermissionError):
            return {"handled": False}
        return {
            "handled": True, "fixed": False,
            "action": "Permission denied. Try running as administrator or check file permissions.",
        }

    async def _fix_connection_error(self, error, msg: str, context: str) -> dict:
        connection_errors = ("ConnectionError", "ConnectError", "TimeoutException",
                             "ConnectTimeout", "ReadTimeout", "HTTPStatusError")
        if type(error).__name__ not in connection_errors:
            return {"handled": False}
        return {
            "handled": True, "fixed": False,
            "action": "Network error. Check internet connection. Jiro can work offline if you download a model.",
        }

    async def _fix_json_error(self, error, msg: str, context: str) -> dict:
        if not isinstance(error, json.JSONDecodeError):
            return {"handled": False}

        if "config.json" in context:
            self._create_default_config()
            return {"handled": True, "fixed": True, "action": "Repaired corrupted config.json"}

        return {"handled": True, "fixed": False, "action": f"JSON parse error in {context}"}

    async def _fix_audio_error(self, error, msg: str, context: str) -> dict:
        audio_keywords = ["portaudio", "audio", "microphone", "sounddevice", "alsa"]
        if not any(kw in msg.lower() for kw in audio_keywords):
            return {"handled": False}

        # Try installing sounddevice
        if "sounddevice" in msg.lower() or "portaudio" in msg.lower():
            self._install_package("sounddevice")

        return {
            "handled": True, "fixed": False,
            "action": "Audio error. Make sure a microphone is connected. Use '--cli' for text-only mode.",
        }

    async def _fix_encoding_error(self, error, msg: str, context: str) -> dict:
        if not isinstance(error, (UnicodeDecodeError, UnicodeEncodeError)):
            return {"handled": False}
        return {
            "handled": True, "fixed": False,
            "action": "Encoding error. Try setting PYTHONIOENCODING=utf-8 environment variable.",
        }

    async def _ask_ai_for_fix(self, error_type: str, error_msg: str,
                               traceback_str: str, context: str) -> Optional[str]:
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
        default = {
            "assistant_name": "Jiro",
            "wake_word": "jiro",
            "language": "en",
            "supported_languages": ["en", "bn"],
            "api_keys": {"nvidia": "", "huggingface": "", "groq": "", "gemini": "", "openrouter": ""},
            "supabase": {"backend_url": "", "anon_key": ""},
            "models": {
                "nvidia_understanding": "meta/llama-3.1-70b-instruct",
                "groq_generation": "llama-3.1-70b-versatile",
                "gemini_generation": "gemini-2.0-flash",
            },
            "tts": {"engine": "edge-tts", "voice": "en-US-GuyNeural", "rate": "+0%"},
            "stt": {"model": "whisper-large-v3", "silence_threshold": 2.0, "energy_threshold": 300},
            "gui": {"always_on_top": True, "opacity": 0.95, "width": 400, "height": 600},
            "monitoring": {"enabled": True, "screenshot_interval_seconds": 30},
            "memory": {"max_conversation_history": 100, "persist_to_disk": True},
            "proactive": {"enabled": True, "study_quiz_interval_minutes": 30},
            "security": {"require_passkey": False, "passkey_hash": ""},
            "offline": {"enabled": False, "auto_download": True},
            "autostart": {"enabled": True, "start_minimized": True},
            "update": {"auto_update": True, "repo_url": "https://github.com/MubasshirBadhon/Jiro-AI.git", "branch": "main"},
        }
        with open(PROJECT_ROOT / "config.json", "w", encoding="utf-8") as f:
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
                code = plugin_path.read_text(encoding="utf-8")
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
                    import shutil
                    shutil.copy2(plugin_path, backup)
                    plugin_path.write_text(fixed_code, encoding="utf-8")

                    try:
                        importlib.import_module(f"plugins.{plugin_path.stem}")
                        return {"handled": True, "fixed": True,
                                "action": f"AI-fixed plugin: {plugin_path.name}"}
                    except Exception:
                        shutil.copy2(backup, plugin_path)
                        return {"handled": True, "fixed": False,
                                "action": f"AI fix attempt failed for {plugin_path.name}"}
            except Exception as e:
                logger.warning("AI fix for plugin failed: %s", e)

        return {"handled": True, "fixed": False,
                "action": f"Could not auto-fix {plugin_path.name}: {error}"}

    async def fix_all_issues(self) -> list[dict]:
        """Run all diagnostic checks and fix what we can."""
        fixes = await self.startup_check()

        # Check ffmpeg
        import shutil
        if not shutil.which("ffmpeg") and not shutil.which("ffplay"):
            fixes.append({
                "fixed": False,
                "action": "ffmpeg not found. TTS audio may not play. Install: winget install ffmpeg",
            })

        return fixes
