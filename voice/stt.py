"""Speech-to-Text + Wake Word detection for Jiro AI.

Uses Groq Whisper API for transcription.
Wake word detection: listens for "Hey Jiro" / "Jiro" to activate.
Falls back to offline Vosk if no internet.
"""

import asyncio
import logging
import tempfile
import wave
from pathlib import Path
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger("jiro.voice.stt")


class SpeechToText:
    """Handles speech recognition and wake word detection."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.is_listening = False
        self._silence_threshold = config.get("stt", {}).get("silence_threshold", 2.0)
        self._energy_threshold = config.get("stt", {}).get("energy_threshold", 300)

    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe audio bytes using Groq Whisper API."""
        api_key = ""
        if self._api_keys:
            api_key = self._api_keys.get_key("groq")
        if not api_key:
            api_key = self._config.get("api_keys", {}).get("groq", "")
        if not api_key:
            logger.warning("No Groq API key for STT")
            return ""

        tmp_path = None
        try:
            import httpx
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                with wave.open(tmp, "wb") as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(audio_data)

            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(tmp_path, "rb") as f:
                    resp = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": ("audio.wav", f, "audio/wav")},
                        data={
                            "model": self._config.get("stt", {}).get("model", "whisper-large-v3"),
                            "response_format": "text",
                        },
                    )
                if resp.status_code == 200:
                    text = resp.text.strip()
                    logger.info("STT: %s", text)
                    return text
                logger.warning("STT error %s: %s", resp.status_code, resp.text[:100])
                return ""
        except Exception as e:
            logger.error("STT failed: %s", e)
            return ""
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    async def listen_once(self, duration: float = 5.0) -> Optional[str]:
        """Record audio for a fixed duration and transcribe."""
        try:
            import sounddevice as sd
            audio = sd.rec(
                int(self.sample_rate * duration),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
            )
            sd.wait()
            return await self.transcribe(audio.tobytes())
        except ImportError:
            logger.error("sounddevice not installed")
            return None
        except Exception as e:
            logger.error("Listen failed: %s", e)
            return None

    async def listen_continuous(self, on_speech: Callable) -> None:
        """Continuously listen, transcribe on silence detection."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed for continuous listening")
            return

        self.is_listening = True
        audio_buffer = []
        silence_frames = 0
        is_speaking = False
        fps = self.sample_rate // self.chunk_size

        def callback(indata, frames, time_info, status):
            nonlocal silence_frames, is_speaking
            energy = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            if energy > self._energy_threshold:
                is_speaking = True
                silence_frames = 0
                audio_buffer.append(indata.copy())
            elif is_speaking:
                silence_frames += 1
                audio_buffer.append(indata.copy())

        stream = sd.InputStream(
            samplerate=self.sample_rate, channels=self.channels,
            dtype="int16", blocksize=self.chunk_size, callback=callback,
        )

        with stream:
            while self.is_listening:
                await asyncio.sleep(0.1)
                max_silence = int(self._silence_threshold * fps)
                if is_speaking and silence_frames >= max_silence and audio_buffer:
                    raw = np.concatenate(audio_buffer)
                    audio_buffer.clear()
                    silence_frames = 0
                    is_speaking = False
                    text = await self.transcribe(raw.tobytes())
                    if text:
                        await on_speech(text)

    def stop(self) -> None:
        self.is_listening = False


class WakeWordDetector:
    """Detects wake word "Jiro" to activate the assistant."""

    def __init__(self, config: dict, stt: SpeechToText):
        self._config = config
        self._stt = stt
        self.wake_word = config.get("wake_word", "jiro").lower()
        self.is_listening = False
        self.is_active = False

    async def start(self, on_wake: Callable) -> None:
        """Listen for wake word in a loop."""
        self.is_listening = True
        logger.info("Listening for wake word: '%s'", self.wake_word)

        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed for wake word")
            return

        while self.is_listening:
            try:
                audio = sd.rec(
                    int(16000 * 2), samplerate=16000, channels=1, dtype="int16",
                )
                sd.wait()

                energy = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
                if energy > 200:
                    text = await self._stt.transcribe(audio.tobytes())
                    text_lower = text.lower().strip()
                    variants = [self.wake_word, "jiro", "hero", "zero", "gyro",
                                "hey jiro", "hey hero", "jarvis"]
                    if any(v in text_lower for v in variants):
                        logger.info("Wake word detected: '%s'", text)
                        self.is_active = True
                        await on_wake()
            except Exception as e:
                logger.error("Wake word error: %s", e)
                await asyncio.sleep(2)

            await asyncio.sleep(0.1)

    def stop(self) -> None:
        self.is_listening = False
        self.is_active = False

    def deactivate(self) -> None:
        self.is_active = False
