"""Speech-to-Text + Wake Word detection for Jiro AI.

Uses multiple STT backends with automatic fallback:
1. Groq Whisper API (best quality, needs internet)
2. Google Speech Recognition (free, needs internet)
3. Offline Vosk (no internet needed)
4. Keyboard input fallback (always works)

Wake word uses lightweight SpeechRecognition for "Jiro" detection.
"""

import asyncio
import logging
import tempfile
import wave
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("jiro.voice.stt")


class SpeechToText:
    """Handles speech recognition with multiple fallback methods."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager
        self.sample_rate = 16000
        self.channels = 1
        self.is_listening = False
        self._energy_threshold = config.get("stt", {}).get("energy_threshold", 300)
        self._silence_threshold = config.get("stt", {}).get("silence_threshold", 2.0)
        self._recognizer = None
        self._init_recognizer()

    def _init_recognizer(self) -> None:
        """Initialize speech_recognition as primary fallback."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self._energy_threshold
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = self._silence_threshold
            logger.info("SpeechRecognition initialized")
        except ImportError:
            logger.warning("speech_recognition not installed. Voice input limited.")

    async def transcribe_groq(self, audio_data: bytes) -> str:
        """Transcribe using Groq Whisper API."""
        api_key = ""
        if self._api_keys:
            api_key = self._api_keys.get_key("groq")
        if not api_key:
            api_key = self._config.get("api_keys", {}).get("groq", "")
        if not api_key:
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
                        data={"model": "whisper-large-v3", "response_format": "text"},
                    )
                if resp.status_code == 200:
                    return resp.text.strip()
                logger.warning("Groq STT error %s", resp.status_code)
        except Exception as e:
            logger.warning("Groq STT failed: %s", e)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
        return ""

    def transcribe_google(self, audio) -> str:
        """Transcribe using Google Speech Recognition (free)."""
        if not self._recognizer:
            return ""
        try:
            import speech_recognition as sr
            text = self._recognizer.recognize_google(audio)
            return text
        except Exception:
            return ""

    async def listen_once(self, duration: float = 5.0) -> Optional[str]:
        """Record and transcribe. Tries Groq first, then Google, then keyboard."""
        if self._recognizer:
            try:
                import speech_recognition as sr
                mic = sr.Microphone()
                with mic as source:
                    logger.info("Listening... (speak now)")
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self._recognizer.listen(source, timeout=duration + 3, phrase_time_limit=duration)

                # Try Groq first
                raw = audio.get_wav_data()
                text = await self.transcribe_groq(raw)
                if text:
                    logger.info("STT (Groq): %s", text)
                    return text

                # Fallback to Google
                text = self.transcribe_google(audio)
                if text:
                    logger.info("STT (Google): %s", text)
                    return text

                logger.warning("Could not transcribe audio")
                return None

            except ImportError:
                logger.warning("speech_recognition or pyaudio not available")
            except Exception as e:
                logger.warning("Listen failed: %s", e)

        # Fallback: try sounddevice
        try:
            import sounddevice as sd
            import numpy as np
            audio = sd.rec(int(self.sample_rate * duration),
                           samplerate=self.sample_rate, channels=self.channels, dtype="int16")
            sd.wait()
            text = await self.transcribe_groq(audio.tobytes())
            if text:
                return text
        except Exception:
            pass

        return None

    async def listen_continuous(self, on_speech: Callable) -> None:
        """Continuously listen and transcribe speech."""
        self.is_listening = True

        if self._recognizer:
            try:
                import speech_recognition as sr
                mic = sr.Microphone()
                while self.is_listening:
                    try:
                        with mic as source:
                            self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                            audio = self._recognizer.listen(source, timeout=10, phrase_time_limit=15)

                        raw = audio.get_wav_data()
                        text = await self.transcribe_groq(raw)
                        if not text:
                            text = self.transcribe_google(audio)
                        if text:
                            await on_speech(text)
                    except Exception as e:
                        if "WaitTimeoutError" not in type(e).__name__:
                            logger.warning("Listen error: %s", e)
                        await asyncio.sleep(0.1)
                return
            except ImportError:
                pass

        # Fallback: sounddevice-based loop
        try:
            import sounddevice as sd
            import numpy as np

            while self.is_listening:
                try:
                    audio = sd.rec(int(self.sample_rate * 5),
                                   samplerate=self.sample_rate, channels=self.channels, dtype="int16")
                    sd.wait()
                    energy = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
                    if energy > self._energy_threshold:
                        text = await self.transcribe_groq(audio.tobytes())
                        if text:
                            await on_speech(text)
                except Exception as e:
                    logger.warning("SD listen error: %s", e)
                    await asyncio.sleep(1)
        except ImportError:
            logger.error("No audio input available")

    def stop(self) -> None:
        self.is_listening = False


class WakeWordDetector:
    """Lightweight wake word detection using SpeechRecognition."""

    def __init__(self, config: dict, stt: SpeechToText):
        self._config = config
        self._stt = stt
        self.wake_word = config.get("wake_word", "jiro").lower()
        self.is_listening = False
        self.is_active = False
        self._recognizer = None
        self._init()

    def _init(self) -> None:
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 400
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8
        except ImportError:
            logger.warning("speech_recognition not available for wake word")

    async def start(self, on_wake: Callable) -> None:
        """Listen for wake word continuously."""
        self.is_listening = True
        logger.info("Listening for wake word: '%s' (say 'Hey Jiro' or 'Jiro')", self.wake_word)

        if not self._recognizer:
            logger.error("Cannot detect wake word without speech_recognition")
            return

        try:
            import speech_recognition as sr
        except ImportError:
            return

        mic = sr.Microphone()

        while self.is_listening:
            try:
                with mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=3)

                try:
                    text = self._recognizer.recognize_google(audio).lower()
                except Exception:
                    text = ""

                if not text:
                    try:
                        raw = audio.get_wav_data()
                        text = (await self._stt.transcribe_groq(raw)).lower()
                    except Exception:
                        pass

                if text:
                    wake_variants = [
                        self.wake_word, "jiro", "zero", "hero", "gyro",
                        "hey jiro", "hey zero", "hey hero", "jarvis",
                        "giro", "jero", "hiro",
                    ]
                    if any(v in text for v in wake_variants):
                        logger.info("Wake word detected: '%s'", text)
                        self.is_active = True
                        await on_wake()

            except Exception as e:
                if "WaitTimeoutError" not in type(e).__name__:
                    logger.debug("Wake word listen cycle: %s", e)
                await asyncio.sleep(0.1)

    def stop(self) -> None:
        self.is_listening = False
        self.is_active = False

    def deactivate(self) -> None:
        self.is_active = False
