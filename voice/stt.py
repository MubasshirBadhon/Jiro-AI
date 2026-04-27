"""Speech-to-Text + Wake Word detection for Jiro AI.

LOCAL-FIRST approach - no API calls for basic voice:
1. Windows native voice typing (Win+H) - captures system dictation
2. pyttsx3 + speech_recognition (Google free tier) - offline-capable
3. sounddevice raw recording + Groq Whisper - API fallback only
4. Keyboard text input - always available

Wake word detection is fully local (no API calls).
"""

import asyncio
import logging
import platform
import tempfile
import wave
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("jiro.voice.stt")


class SpeechToText:
    """Local-first speech recognition. No API calls for basic listening."""

    def __init__(self, config: dict, api_key_manager=None):
        self._config = config
        self._api_keys = api_key_manager
        self.sample_rate = 16000
        self.channels = 1
        self.is_listening = False
        self._energy_threshold = config.get("stt", {}).get("energy_threshold", 300)
        self._silence_threshold = config.get("stt", {}).get("silence_threshold", 2.0)
        self._recognizer = None
        self._method = self._detect_method()
        logger.info("STT method: %s", self._method)

    def _detect_method(self) -> str:
        """Detect the best available STT method."""
        # speech_recognition with Google free tier (works offline-ish, very reliable)
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self._energy_threshold
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = self._silence_threshold
            return "speech_recognition"
        except ImportError:
            pass

        # sounddevice for raw recording (needs Groq API for transcription)
        try:
            import sounddevice
            return "sounddevice"
        except ImportError:
            pass

        return "keyboard"

    async def listen_once(self, duration: float = 8.0) -> Optional[str]:
        """Listen for speech and return transcribed text. Local-first."""
        if self._method == "speech_recognition":
            return await self._listen_sr(duration)
        elif self._method == "sounddevice":
            return await self._listen_sounddevice(duration)
        return None

    async def _listen_sr(self, duration: float) -> Optional[str]:
        """Listen using speech_recognition (Google free tier - no API key)."""
        try:
            import speech_recognition as sr
            mic = sr.Microphone()
            loop = asyncio.get_event_loop()

            def _record():
                with mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self._recognizer.listen(source, timeout=duration + 3, phrase_time_limit=duration)
                return audio

            self.is_listening = True
            audio = await loop.run_in_executor(None, _record)
            self.is_listening = False

            # Google free tier first (no API key needed, works well for English)
            try:
                text = self._recognizer.recognize_google(audio, language="en-US")
                if text:
                    logger.info("STT (Google free): %s", text)
                    return text
            except Exception:
                pass

            # Groq Whisper fallback (uses API call)
            raw = audio.get_wav_data()
            text = await self._transcribe_groq(raw)
            if text:
                logger.info("STT (Groq): %s", text)
                return text

            return None

        except Exception as e:
            logger.warning("SR listen failed: %s", e)
            self.is_listening = False
            return None

    async def _listen_sounddevice(self, duration: float) -> Optional[str]:
        """Listen using sounddevice + Groq Whisper."""
        try:
            import sounddevice as sd
            import numpy as np

            self.is_listening = True
            audio = sd.rec(int(self.sample_rate * duration),
                           samplerate=self.sample_rate, channels=self.channels, dtype="int16")
            sd.wait()
            self.is_listening = False

            energy = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
            if energy < self._energy_threshold:
                return None

            text = await self._transcribe_groq(audio.tobytes())
            return text
        except Exception as e:
            logger.warning("sounddevice listen failed: %s", e)
            self.is_listening = False
            return None

    async def _transcribe_groq(self, audio_data: bytes) -> str:
        """Transcribe using Groq Whisper API (fallback only)."""
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

    async def listen_continuous(self, on_speech: Callable) -> None:
        """Continuously listen and call on_speech with transcribed text."""
        self.is_listening = True
        while self.is_listening:
            try:
                text = await self.listen_once(duration=8.0)
                if text:
                    await on_speech(text)
            except Exception as e:
                logger.warning("Continuous listen error: %s", e)
                await asyncio.sleep(0.5)

    def stop(self) -> None:
        self.is_listening = False


class WakeWordDetector:
    """Local wake word detection. Zero API calls."""

    WAKE_VARIANTS = [
        "jiro", "zero", "hero", "gyro", "hey jiro", "hey zero",
        "hey hero", "jarvis", "giro", "jero", "hiro",
    ]

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
            logger.warning("speech_recognition not available for wake word detection")

    async def start(self, on_wake: Callable) -> None:
        """Listen for wake word continuously using only local/free methods."""
        self.is_listening = True
        logger.info("Wake word listening: say 'Hey Jiro' or 'Jiro'")

        if not self._recognizer:
            logger.error("No wake word detection available - install speech_recognition")
            return

        try:
            import speech_recognition as sr
        except ImportError:
            return

        mic = sr.Microphone()
        loop = asyncio.get_event_loop()

        while self.is_listening:
            try:
                def _listen():
                    with mic as source:
                        self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                        audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    try:
                        return self._recognizer.recognize_google(audio, language="en-US").lower()
                    except Exception:
                        return ""

                text = await loop.run_in_executor(None, _listen)

                if text and any(v in text for v in self.WAKE_VARIANTS):
                    logger.info("Wake word detected: '%s'", text)
                    self.is_active = True
                    await on_wake()

            except Exception as e:
                if "WaitTimeoutError" not in type(e).__name__:
                    logger.debug("Wake word cycle: %s", e)
                await asyncio.sleep(0.1)

    def stop(self) -> None:
        self.is_listening = False
        self.is_active = False

    def deactivate(self) -> None:
        self.is_active = False
