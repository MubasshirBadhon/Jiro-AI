"""Health Checker - System, plugin, and API health monitor.

Checks system resources, validates API keys, tests plugins,
and provides a comprehensive health report with fix suggestions.
"""

import asyncio
import importlib
import logging
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.health")

PROJECT_ROOT = Path(__file__).parent.parent


class HealthChecker:
    """Comprehensive health monitoring for all Jiro AI components."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager
        self._issues: list[dict] = []

    async def full_check(self) -> dict:
        """Run all health checks."""
        self._issues.clear()
        report = {
            "system": self._check_system(),
            "python": self._check_python(),
            "dependencies": self._check_dependencies(),
            "directories": self._check_directories(),
            "config": self._check_config(),
            "audio": self._check_audio(),
        }

        if self._api_keys:
            report["api_keys"] = await self._api_keys.validate_all()

        report["plugins"] = self._check_plugins()
        report["issues"] = self._issues
        report["overall"] = "healthy" if not self._issues else "issues_found"
        report["fix_suggestions"] = self._generate_fixes()
        return report

    def _check_system(self) -> dict:
        """Check system resources."""
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }

        try:
            import psutil
            mem = psutil.virtual_memory()
            info["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
            info["ram_available_gb"] = round(mem.available / (1024 ** 3), 1)
            info["ram_percent"] = mem.percent
            info["cpu_count"] = psutil.cpu_count()
            info["cpu_percent"] = psutil.cpu_percent(interval=0.5)

            disk = shutil.disk_usage(str(PROJECT_ROOT))
            info["disk_free_gb"] = round(disk.free / (1024 ** 3), 1)

            if mem.total < 4 * (1024 ** 3):
                self._issues.append({
                    "component": "system",
                    "severity": "warning",
                    "message": "Low RAM detected. Jiro may run slowly.",
                    "fix": "Close unnecessary applications to free memory.",
                })
        except ImportError:
            self._issues.append({
                "component": "system",
                "severity": "warning",
                "message": "psutil not installed, cannot check system resources",
                "fix": "pip install psutil",
            })

        return info

    def _check_python(self) -> dict:
        """Check Python version compatibility."""
        ver = sys.version_info
        info = {"version": f"{ver.major}.{ver.minor}.{ver.micro}", "ok": ver >= (3, 10)}
        if not info["ok"]:
            self._issues.append({
                "component": "python",
                "severity": "critical",
                "message": f"Python {info['version']} detected. Jiro requires 3.10+",
                "fix": "Install Python 3.10+ from https://python.org",
            })
        return info

    def _check_dependencies(self) -> dict:
        """Check all required packages."""
        required = {
            "httpx": {"package": "httpx", "critical": True},
            "edge_tts": {"package": "edge-tts", "critical": True},
            "numpy": {"package": "numpy", "critical": True},
            "PIL": {"package": "Pillow", "critical": False},
            "psutil": {"package": "psutil", "critical": False},
            "fitz": {"package": "PyMuPDF", "critical": False},
            "mss": {"package": "mss", "critical": False},
            "schedule": {"package": "schedule", "critical": False},
        }

        optional_audio = {
            "sounddevice": {"package": "sounddevice", "critical": False},
            "pyaudio": {"package": "PyAudio", "critical": False},
        }

        results = {}
        missing_critical = []
        missing_optional = []

        for module, info in required.items():
            try:
                importlib.import_module(module)
                results[info["package"]] = "installed"
            except ImportError:
                results[info["package"]] = "missing"
                if info["critical"]:
                    missing_critical.append(info["package"])
                else:
                    missing_optional.append(info["package"])

        has_audio = False
        for module, info in optional_audio.items():
            try:
                importlib.import_module(module)
                results[info["package"]] = "installed"
                has_audio = True
            except ImportError:
                results[info["package"]] = "missing"

        if not has_audio:
            missing_optional.append("sounddevice (or PyAudio)")

        if missing_critical:
            self._issues.append({
                "component": "dependencies",
                "severity": "critical",
                "message": f"Missing critical packages: {', '.join(missing_critical)}",
                "fix": f"pip install {' '.join(missing_critical)}",
            })

        if missing_optional:
            self._issues.append({
                "component": "dependencies",
                "severity": "warning",
                "message": f"Missing optional packages: {', '.join(missing_optional)}",
                "fix": f"pip install {' '.join(missing_optional)}",
            })

        ffmpeg_ok = shutil.which("ffmpeg") is not None
        results["ffmpeg"] = "installed" if ffmpeg_ok else "missing"
        if not ffmpeg_ok:
            self._issues.append({
                "component": "dependencies",
                "severity": "warning",
                "message": "ffmpeg not found. TTS audio playback may not work.",
                "fix": "Windows: winget install ffmpeg  |  Or download from https://ffmpeg.org",
            })

        return results

    def _check_directories(self) -> dict:
        """Ensure all required directories exist."""
        dirs = {
            "data/memory": PROJECT_ROOT / "data" / "memory",
            "data/recordings": PROJECT_ROOT / "data" / "recordings",
            "data/models": PROJECT_ROOT / "data" / "models",
            "data/logs": PROJECT_ROOT / "data" / "logs",
            "plugins": PROJECT_ROOT / "plugins",
        }

        results = {}
        for name, path in dirs.items():
            exists = path.exists()
            results[name] = "ok" if exists else "missing"
            if not exists:
                path.mkdir(parents=True, exist_ok=True)
                results[name] = "created"

        return results

    def _check_config(self) -> dict:
        """Validate config.json structure."""
        required_keys = ["api_keys", "supabase", "models", "tts", "stt"]
        results = {}
        for key in required_keys:
            results[key] = "present" if key in self._config else "missing"
            if key not in self._config:
                self._issues.append({
                    "component": "config",
                    "severity": "warning",
                    "message": f"Missing config section: {key}",
                    "fix": "Re-download config.json from the repository",
                })

        configured_apis = [
            k for k, v in self._config.get("api_keys", {}).items() if v
        ]
        results["configured_apis"] = configured_apis
        if not configured_apis:
            self._issues.append({
                "component": "config",
                "severity": "critical",
                "message": "No API keys configured. Jiro cannot use AI features.",
                "fix": "Edit config.json and add at least one API key (Groq recommended).",
            })

        return results

    def _check_audio(self) -> dict:
        """Check audio device availability."""
        results = {"input": "unknown", "output": "unknown"}
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devs = [d for d in devices if d["max_input_channels"] > 0]
            output_devs = [d for d in devices if d["max_output_channels"] > 0]
            results["input"] = f"{len(input_devs)} device(s)" if input_devs else "none"
            results["output"] = f"{len(output_devs)} device(s)" if output_devs else "none"

            if not input_devs:
                self._issues.append({
                    "component": "audio",
                    "severity": "warning",
                    "message": "No microphone detected. Voice input won't work.",
                    "fix": "Connect a microphone and restart Jiro.",
                })
        except Exception:
            results["note"] = "sounddevice not available"
        return results

    def _check_plugins(self) -> dict:
        """Check all plugins in the plugins directory."""
        plugins_dir = PROJECT_ROOT / "plugins"
        results = {}
        for path in plugins_dir.glob("*_plugin.py"):
            try:
                spec = importlib.util.spec_from_file_location(path.stem, path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    results[path.stem] = "ok"
            except Exception as e:
                results[path.stem] = f"error: {e}"
                self._issues.append({
                    "component": "plugins",
                    "severity": "warning",
                    "message": f"Plugin {path.stem} has errors: {e}",
                    "fix": f"Check plugins/{path.name} for syntax errors.",
                })
        return results

    def _generate_fixes(self) -> list[str]:
        """Generate actionable fix suggestions."""
        fixes = []
        for issue in self._issues:
            fixes.append(f"[{issue['severity'].upper()}] {issue['message']}")
            if issue.get("fix"):
                fixes.append(f"  Fix: {issue['fix']}")
        return fixes

    def format_report(self, report: dict) -> str:
        """Format health report for display."""
        lines = ["=" * 55, "  JIRO AI - HEALTH CHECK REPORT", "=" * 55]

        overall = report.get("overall", "unknown")
        lines.append(f"\n  Overall: {'HEALTHY' if overall == 'healthy' else 'ISSUES FOUND'}\n")

        sys_info = report.get("system", {})
        lines.append(f"  System: {sys_info.get('platform', '?')} | "
                      f"RAM: {sys_info.get('ram_available_gb', '?')}GB free | "
                      f"CPU: {sys_info.get('cpu_percent', '?')}%")

        py_info = report.get("python", {})
        lines.append(f"  Python: {py_info.get('version', '?')} "
                      f"({'OK' if py_info.get('ok') else 'UPGRADE NEEDED'})")

        deps = report.get("dependencies", {})
        missing = [k for k, v in deps.items() if v == "missing"]
        if missing:
            lines.append(f"\n  Missing: {', '.join(missing)}")

        api_keys = report.get("api_keys", {})
        if api_keys:
            lines.append("\n  API Keys:")
            for provider, status in api_keys.items():
                s = status.get("status", "?") if isinstance(status, dict) else status
                icon = "OK" if s == "valid" else "!!"
                lines.append(f"    [{icon}] {provider}: {s}")

        fixes = report.get("fix_suggestions", [])
        if fixes:
            lines.append("\n  Issues & Fixes:")
            for fix in fixes:
                lines.append(f"    {fix}")

        lines.append("\n" + "=" * 55)
        return "\n".join(lines)
