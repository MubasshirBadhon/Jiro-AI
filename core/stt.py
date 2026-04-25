"""Speech-to-Text module for Jiro AI. Uses Groq Whisper API for transcription."""

import asyncio
import io
import logging
import wave
import tempfile
from pathlib import Path
from typing import Optional, Callable

import numpy as np

logger = logging.getLogger("jiro.stt")


class SpeechToText:
    """Handles speech recognition using Groq Whisper API."""

    def __init__(self, config_manager):
        self.config = config_manager
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.is_listening = False
        self._audio_buffer = []
        self._silence_threshold = config_manager.get("stt.silence_threshold", 2.0)
        self._energy_threshold = config_manager.get("stt.energy_threshold", 300)

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio bytes using Groq Whisper API."""
        api_key = self.config.get_api_key("groq")
        if not api_key:
            logger.error("Groq API key not configured for STT")
            return ""

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
                with open(tmp_path, "rb") as audio_file:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": ("audio.wav", audio_file, "audio/wav")},
                        data={
                            "model": self.config.get("stt.model", "whisper-large-v3"),
                            "response_format": "text",
                        },
                    )

                if response.status_code == 200:
                    text = response.text.strip()
                    logger.info("Transcribed: %s", text)
                    return text
                else:
                    logger.error("Groq STT error %s: %s", response.status_code, response.text)
                    return ""
        except Exception as e:
            logger.error("STT transcription failed: %s", e)
            return ""
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def listen_continuous(self, on_speech: Callable[[str], None]) -> None:
        """Continuously listen for speech and call callback with transcribed text."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed. Run: pip install sounddevice")
            return

        self.is_listening = True
        logger.info("Starting continuous listening...")

        audio_buffer = []
        silence_frames = 0
        is_speaking = False
        frames_per_second = self.sample_rate // self.chunk_size

        def audio_callback(indata, frames, time_info, status):
            nonlocal silence_frames, is_speaking

            if status:
                logger.warning("Audio status: %s", status)

            energy = np.sqrt(np.mean(indata**2)) * 1000

            if energy > self._energy_threshold:
                is_speaking = True
                silence_frames = 0
                audio_buffer.append(indata.copy())
            elif is_speaking:
                silence_frames += 1
                audio_buffer.append(indata.copy())

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.chunk_size,
            callback=audio_callback,
        )

        with stream:
            while self.is_listening:
                await asyncio.sleep(0.1)

                max_silence = int(self._silence_threshold * frames_per_second)
                if is_speaking and silence_frames >= max_silence and audio_buffer:
                    raw_audio = np.concatenate(audio_buffer)
                    audio_bytes = raw_audio.tobytes()

                    audio_buffer.clear()
                    silence_frames = 0
                    is_speaking = False

                    text = await self.transcribe_audio(audio_bytes)
                    if text:
                        await on_speech(text)

    def stop_listening(self) -> None:
        """Stop continuous listening."""
        self.is_listening = False
        logger.info("Stopped listening")

    async def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file."""
        with open(file_path, "rb") as f:
            audio_data = f.read()
        return await self.transcribe_audio(audio_data)
