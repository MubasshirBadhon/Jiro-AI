"""Health Checker for Jiro AI.

Validates API keys, checks system resources, and monitors
the health of all Jiro AI components.
"""

import asyncio
import logging
import platform
import shutil
from typing import Optional

logger = logging.getLogger("jiro.utils.health")


class HealthChecker:
    """Checks health of all Jiro AI components and API keys."""

    def __init__(self, config_manager):
        self.config = config_manager

    async def check_all(self) -> dict:
        """Run all health checks and return a report."""
        results = {}

        api_checks = await self.check_api_keys()
        results["api_keys"] = api_checks

        results["system"] = self.check_system()
        results["dependencies"] = self.check_dependencies()

        all_ok = all(
            v.get("status") == "ok" if isinstance(v, dict) else v == "ok"
            for section in results.values()
            for v in (section.values() if isinstance(section, dict) else [section])
        )
        results["overall"] = "healthy" if all_ok else "degraded"

        return results

    async def check_api_keys(self) -> dict:
        """Validate all configured API keys."""
        results = {}

        providers = {
            "groq": self._check_groq,
            "gemini": self._check_gemini,
            "nvidia": self._check_nvidia,
            "huggingface": self._check_huggingface,
            "openrouter": self._check_openrouter,
        }

        tasks = {}
        for name, checker in providers.items():
            key = self.config.get_api_key(name)
            if key:
                tasks[name] = checker(key)
            else:
                results[name] = {"status": "not_configured", "message": "API key not set"}

        if tasks:
            checked = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            for name, result in zip(tasks.keys(), checked):
                if isinstance(result, Exception):
                    results[name] = {"status": "error", "message": str(result)}
                else:
                    results[name] = result

        return results

    async def _check_groq(self, api_key: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return {"status": "ok", "message": "Groq API key valid"}
                else:
                    return {"status": "invalid", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _check_gemini(self, api_key: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": api_key},
                )
                if response.status_code == 200:
                    return {"status": "ok", "message": "Gemini API key valid"}
                else:
                    return {"status": "invalid", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _check_nvidia(self, api_key: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "meta/llama-3.1-8b-instruct",
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5,
                    },
                )
                if response.status_code == 200:
                    return {"status": "ok", "message": "NVIDIA API key valid"}
                elif response.status_code == 401:
                    return {"status": "invalid", "message": "Invalid API key"}
                else:
                    return {"status": "unknown", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _check_huggingface(self, api_key: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://huggingface.co/api/whoami-v2",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return {"status": "ok", "message": "HuggingFace token valid"}
                else:
                    return {"status": "invalid", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _check_openrouter(self, api_key: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return {"status": "ok", "message": "OpenRouter API key valid"}
                else:
                    return {"status": "invalid", "message": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_system(self) -> dict:
        """Check system resources."""
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/")

        return {
            "platform": platform.system(),
            "python": platform.python_version(),
            "cpu_usage": f"{cpu_percent}%",
            "memory_used": f"{memory.percent}%",
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "status": "ok" if memory.percent < 90 and cpu_percent < 95 else "warning",
        }

    def check_dependencies(self) -> dict:
        """Check if required dependencies are installed."""
        deps = {
            "httpx": "httpx",
            "edge_tts": "edge-tts",
            "sounddevice": "sounddevice",
            "numpy": "numpy",
            "customtkinter": "customtkinter",
            "PIL": "Pillow",
            "mss": "mss",
            "fitz": "PyMuPDF",
            "psutil": "psutil",
        }

        results = {}
        for module, package in deps.items():
            try:
                __import__(module)
                results[package] = "installed"
            except ImportError:
                results[package] = "missing"

        return results

    def format_report(self, results: dict) -> str:
        """Format health check results as a readable report."""
        lines = [f"=== Jiro AI Health Report ==="]
        lines.append(f"Overall: {results.get('overall', 'unknown').upper()}\n")

        lines.append("API Keys:")
        for provider, status in results.get("api_keys", {}).items():
            icon = "OK" if status.get("status") == "ok" else "!!"
            lines.append(f"  [{icon}] {provider}: {status.get('message', 'unknown')}")

        sys_info = results.get("system", {})
        lines.append(f"\nSystem:")
        lines.append(f"  Platform: {sys_info.get('platform', 'unknown')}")
        lines.append(f"  CPU: {sys_info.get('cpu_usage', 'N/A')}")
        lines.append(f"  Memory: {sys_info.get('memory_used', 'N/A')}")
        lines.append(f"  Disk Free: {sys_info.get('disk_free_gb', 'N/A')} GB")

        deps = results.get("dependencies", {})
        missing = [k for k, v in deps.items() if v == "missing"]
        if missing:
            lines.append(f"\nMissing Dependencies: {', '.join(missing)}")
            lines.append(f"  Install: pip install {' '.join(missing)}")
        else:
            lines.append(f"\nAll dependencies installed.")

        return "\n".join(lines)
