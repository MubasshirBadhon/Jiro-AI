"""Wake word detection for Jiro AI.

Listens for the wake word "Jiro" to activate the assistant.
Uses a lightweight local detection approach.
"""

import asyncio
import logging
import numpy as np
from typing import Callable, Optional

logger = logging.getLogger("jiro.wake_word")


class WakeWordDetector:
    """Detects the wake word to activate Jiro AI.

    Uses energy-based voice activity detection combined with
    Groq Whisper for short-burst transcription to detect "Jiro".
    """

    def __init__(self, config_manager, stt_engine=None):
        self.config = config_manager
        self.stt = stt_engine
        self.wake_word = config_manager.get("wake_word", "jiro").lower()
        self.is_active = False
        self.is_listening = False
        self.sample_rate = 16000
        self.chunk_duration = 2.0
        self._energy_threshold = 200

    async def start(self, on_wake: Callable) -> None:
        """Start listening for the wake word."""
        self.is_listening = True
        logger.info("Wake word detector started. Listening for '%s'...", self.wake_word)

        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed")
            return

        chunk_samples = int(self.sample_rate * self.chunk_duration)

        while self.is_listening:
            try:
                audio = sd.rec(
                    chunk_samples,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                )
                sd.wait()

                energy = np.sqrt(np.mean(audio.astype(np.float32) ** 2))

                if energy > self._energy_threshold:
                    audio_bytes = audio.tobytes()

                    if self.stt:
                        text = await self.stt.transcribe_audio(audio_bytes)
                        text_lower = text.lower().strip()

                        wake_variants = [
                            self.wake_word, "jiro", "hero", "zero",
                            "gyro", "giro", "jeero",
                        ]

                        if any(variant in text_lower for variant in wake_variants):
                            logger.info("Wake word detected! Transcribed: '%s'", text)
                            self.is_active = True
                            await on_wake()

            except Exception as e:
                logger.error("Wake word detection error: %s", e)
                await asyncio.sleep(1.0)

            await asyncio.sleep(0.1)

    def stop(self) -> None:
        """Stop the wake word detector."""
        self.is_listening = False
        self.is_active = False
        logger.info("Wake word detector stopped")

    def deactivate(self) -> None:
        """Deactivate (go back to listening for wake word)."""
        self.is_active = False
        logger.info("Jiro deactivated, listening for wake word again")
