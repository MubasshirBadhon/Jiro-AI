"""Offline AI Handler - Local LLM inference using llama-cpp-python.

Runs when no internet is available or for privacy-sensitive tasks.
Uses GGUF models downloaded by OfflineModelManager.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.ai.offline")

MODELS_DIR = Path(__file__).parent.parent / "data" / "models"


class OfflineHandler:
    """Handles offline AI inference using local GGUF models."""

    def __init__(self, config: dict):
        self._config = config
        self._llm = None
        self._model_path: Optional[Path] = None

    def _find_model(self) -> Optional[Path]:
        """Find a downloaded GGUF model."""
        if self._model_path and self._model_path.exists():
            return self._model_path

        for gguf in MODELS_DIR.glob("*.gguf"):
            self._model_path = gguf
            return gguf
        return None

    def _load_model(self) -> bool:
        """Load the offline model into memory."""
        if self._llm is not None:
            return True

        model_path = self._find_model()
        if not model_path:
            logger.info("No offline model available")
            return False

        try:
            from llama_cpp import Llama
            logger.info("Loading offline model: %s", model_path.name)
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False,
            )
            logger.info("Offline model loaded successfully")
            return True
        except ImportError:
            logger.warning("llama-cpp-python not installed for offline mode")
            return False
        except Exception as e:
            logger.error("Failed to load offline model: %s", e)
            return False

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a response using the local model."""
        if not self._load_model():
            return ""

        try:
            full_prompt = f"### System:\n{system_prompt}\n\n### User:\n{prompt}\n\n### Assistant:\n"

            output = self._llm(
                full_prompt,
                max_tokens=512,
                temperature=0.7,
                stop=["### User:", "### System:"],
                echo=False,
            )

            response = output["choices"][0]["text"].strip()
            logger.info("Offline response generated (%d chars)", len(response))
            return response

        except Exception as e:
            logger.error("Offline generation failed: %s", e)
            return ""

    def is_available(self) -> bool:
        return self._find_model() is not None

    def unload(self) -> None:
        self._llm = None
        logger.info("Offline model unloaded")
