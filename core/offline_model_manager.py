"""Offline Model Manager - Device check + offline LLM downloader.

Checks GPU/RAM capabilities and downloads the best offline model:
  >=16GB RAM + >=8GB VRAM  -> Mistral 7B / LLaMA 3
  >=8GB RAM  + >=4GB VRAM  -> Phi-3 Mini
  Low spec                 -> TinyLlama (quantized GGUF)
  No GPU                   -> CPU-only quantized model
"""

import logging
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.offline")

MODELS_DIR = Path(__file__).parent.parent / "data" / "models"

MODEL_TIERS = {
    "high": {
        "name": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size_gb": 4.4,
        "min_ram_gb": 16,
        "min_vram_gb": 8,
        "description": "Mistral 7B - Best quality offline model",
    },
    "medium": {
        "name": "Phi-3-mini-4k-instruct-q4.gguf",
        "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb": 2.3,
        "min_ram_gb": 8,
        "min_vram_gb": 4,
        "description": "Phi-3 Mini - Good balance of speed and quality",
    },
    "low": {
        "name": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "size_gb": 0.7,
        "min_ram_gb": 4,
        "min_vram_gb": 0,
        "description": "TinyLlama - Lightweight, works on any PC",
    },
}


class OfflineModelManager:
    """Manages offline LLM models based on device capabilities."""

    def __init__(self, config: dict):
        self._config = config
        self._models_dir = MODELS_DIR
        self._models_dir.mkdir(parents=True, exist_ok=True)

    def check_device_capabilities(self) -> dict:
        """Check RAM, GPU, and storage capabilities."""
        info = {
            "ram_gb": 0,
            "gpu_available": False,
            "gpu_name": "None",
            "gpu_vram_gb": 0,
            "disk_free_gb": 0,
            "recommended_tier": "low",
        }

        try:
            import psutil
            info["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except ImportError:
            pass

        disk = shutil.disk_usage(str(self._models_dir))
        info["disk_free_gb"] = round(disk.free / (1024 ** 3), 1)

        info.update(self._check_gpu())

        if info["ram_gb"] >= 16 and info["gpu_vram_gb"] >= 8:
            info["recommended_tier"] = "high"
        elif info["ram_gb"] >= 8 and info["gpu_vram_gb"] >= 4:
            info["recommended_tier"] = "medium"
        elif info["ram_gb"] >= 8:
            info["recommended_tier"] = "medium"
        else:
            info["recommended_tier"] = "low"

        return info

    def _check_gpu(self) -> dict:
        """Detect GPU and VRAM."""
        result = {"gpu_available": False, "gpu_name": "None", "gpu_vram_gb": 0}

        try:
            output = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10,
            )
            if output.returncode == 0 and output.stdout.strip():
                parts = output.stdout.strip().split(",")
                result["gpu_available"] = True
                result["gpu_name"] = parts[0].strip()
                result["gpu_vram_gb"] = round(int(parts[1].strip()) / 1024, 1)
                return result
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            if platform.system() == "Windows":
                output = subprocess.run(
                    ["wmic", "path", "win32_VideoController",
                     "get", "name,AdapterRAM", "/format:csv"],
                    capture_output=True, text=True, timeout=10,
                )
                if output.returncode == 0:
                    for line in output.stdout.strip().split("\n")[1:]:
                        parts = line.strip().split(",")
                        if len(parts) >= 3 and parts[1]:
                            result["gpu_available"] = True
                            result["gpu_name"] = parts[2].strip()
                            try:
                                vram = int(parts[1]) / (1024 ** 3)
                                result["gpu_vram_gb"] = round(vram, 1)
                            except ValueError:
                                pass
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return result

    def get_recommended_model(self) -> dict:
        """Get the recommended model based on device capabilities."""
        caps = self.check_device_capabilities()
        tier = caps["recommended_tier"]
        model = MODEL_TIERS[tier].copy()
        model["tier"] = tier
        model["device_info"] = caps
        return model

    def is_model_downloaded(self, tier: Optional[str] = None) -> bool:
        """Check if the offline model is already downloaded."""
        if tier is None:
            caps = self.check_device_capabilities()
            tier = caps["recommended_tier"]
        model_info = MODEL_TIERS.get(tier, MODEL_TIERS["low"])
        return (self._models_dir / model_info["name"]).exists()

    def get_model_path(self, tier: Optional[str] = None) -> Optional[Path]:
        """Get path to the downloaded model."""
        if tier is None:
            caps = self.check_device_capabilities()
            tier = caps["recommended_tier"]
        model_info = MODEL_TIERS.get(tier, MODEL_TIERS["low"])
        path = self._models_dir / model_info["name"]
        return path if path.exists() else None

    async def download_model(self, tier: Optional[str] = None,
                             progress_callback=None) -> bool:
        """Download the offline model. Tries async httpx, falls back to wget/curl."""
        if tier is None:
            caps = self.check_device_capabilities()
            tier = caps["recommended_tier"]

        model_info = MODEL_TIERS.get(tier, MODEL_TIERS["low"])
        dest = self._models_dir / model_info["name"]

        if dest.exists() and dest.stat().st_size > 1000:
            logger.info("Model already downloaded: %s", model_info["name"])
            return True

        logger.info("Downloading %s (%.1f GB)...", model_info["name"], model_info["size_gb"])

        # Method 1: httpx async download
        try:
            import httpx
            async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=30),
                                         follow_redirects=True) as client:
                async with client.stream("GET", model_info["url"]) as response:
                    if response.status_code != 200:
                        logger.error("Download failed: HTTP %s", response.status_code)
                        raise Exception(f"HTTP {response.status_code}")

                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0

                    with open(dest, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192 * 16):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total:
                                pct = (downloaded / total) * 100
                                progress_callback(pct)

            if dest.exists() and dest.stat().st_size > 1000:
                logger.info("Model downloaded: %s", model_info["name"])
                return True
        except Exception as e:
            logger.warning("httpx download failed, trying fallback: %s", e)
            dest.unlink(missing_ok=True)

        # Method 2: wget/curl fallback
        for cmd in [["wget", "-O", str(dest), model_info["url"]],
                    ["curl", "-L", "-o", str(dest), model_info["url"]]]:
            try:
                logger.info("Trying download with %s...", cmd[0])
                result = subprocess.run(cmd, capture_output=True, text=True,
                                       timeout=3600)
                if result.returncode == 0 and dest.exists() and dest.stat().st_size > 1000:
                    logger.info("Model downloaded via %s", cmd[0])
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        logger.error("All download methods failed for %s", model_info["name"])
        dest.unlink(missing_ok=True)
        return False

    def get_status(self) -> str:
        """Get a summary of offline model status."""
        caps = self.check_device_capabilities()
        tier = caps["recommended_tier"]
        model = MODEL_TIERS[tier]
        downloaded = self.is_model_downloaded(tier)

        return (
            f"Device: {caps['ram_gb']}GB RAM, {caps['gpu_name']} "
            f"({caps['gpu_vram_gb']}GB VRAM)\n"
            f"Recommended: {model['description']} ({model['size_gb']}GB)\n"
            f"Status: {'Downloaded' if downloaded else 'Not downloaded'}"
        )
