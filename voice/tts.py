"""Text-to-Speech for Jiro AI - Streaming sentence-by-sentence.

Speaks each sentence as soon as it's ready while the AI continues
generating the rest in the background. Sounds natural and human-like.
"""

import asyncio
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger("jiro.voice.tts")


class TextToSpeech:
    """Streaming TTS - speaks sentence by sentence for human-like delivery."""

    def __init__(self, config: dict):
        self._config = config
        tts_config = config.get("tts", {})
        self.voice = tts_config.get("voice", "en-US-GuyNeural")
        self.rate = tts_config.get("rate", "+0%")
        self.volume = tts_config.get("volume", "+0%")
        self.is_speaking = False
        self._stop = asyncio.Event()
        self._sentence_re = re.compile(r'[^.!?\n]+[.!?\n]+|[^.!?\n]+$')
        self._playback_method = self._detect_playback()

    def _detect_playback(self) -> str:
        """Detect best available audio playback method."""
        import shutil
        if shutil.which("ffplay"):
            return "ffplay"
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        try:
            import sounddevice
            return "sounddevice"
        except ImportError:
            pass
        try:
            import winsound
            return "winsound"
        except ImportError:
            pass
        return "none"

    def split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in self._sentence_re.findall(text) if s.strip()]

    async def speak_sentence(self, sentence: str) -> None:
        """Speak a single sentence."""
        if self._stop.is_set():
            return

        try:
            import edge_tts
            comm = edge_tts.Communicate(sentence, self.voice, rate=self.rate, volume=self.volume)

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            await comm.save(tmp_path)

            if not self._stop.is_set():
                self.is_speaking = True
                await self._play(tmp_path)
                self.is_speaking = False

            Path(tmp_path).unlink(missing_ok=True)
        except ImportError:
            logger.error("edge-tts not installed. Run: pip install edge-tts")
        except Exception as e:
            logger.error("TTS error: %s", e)
            self.is_speaking = False

    async def speak_streaming(self, text_gen: AsyncGenerator[str, None]) -> None:
        """Stream TTS: speak sentences as they arrive from AI generation."""
        self._stop.clear()
        buffer = ""

        async for chunk in text_gen:
            if self._stop.is_set():
                break
            buffer += chunk
            sentences = self.split_sentences(buffer)
            if len(sentences) > 1:
                for s in sentences[:-1]:
                    await self.speak_sentence(s)
                buffer = sentences[-1]

        if buffer.strip() and not self._stop.is_set():
            await self.speak_sentence(buffer.strip())

    async def speak(self, text: str) -> None:
        """Speak full text sentence by sentence."""
        self._stop.clear()
        for sentence in self.split_sentences(text):
            if self._stop.is_set():
                break
            await self.speak_sentence(sentence)

    def stop(self) -> None:
        self._stop.set()
        self.is_speaking = False

    async def _play(self, path: str) -> None:
        """Play audio file using best available method."""
        if self._playback_method == "ffplay":
            proc = await asyncio.create_subprocess_exec(
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

        elif self._playback_method == "ffmpeg":
            try:
                import sounddevice as sd
                proc = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-i", path, "-f", "s16le", "-ar", "24000",
                    "-ac", "1", "-loglevel", "quiet", "-",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                if stdout and not self._stop.is_set():
                    import numpy as np
                    audio = np.frombuffer(stdout, dtype=np.int16)
                    sd.play(audio, samplerate=24000)
                    sd.wait()
            except ImportError:
                proc = await asyncio.create_subprocess_exec(
                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()

        elif self._playback_method == "winsound":
            import winsound
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: winsound.PlaySound(path, winsound.SND_FILENAME)
            )

        elif self._playback_method == "sounddevice":
            try:
                import sounddevice as sd
                import numpy as np
                proc = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-i", path, "-f", "s16le", "-ar", "24000",
                    "-ac", "1", "-loglevel", "quiet", "-",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                )
                stdout, _ = await proc.communicate()
                if stdout:
                    audio = np.frombuffer(stdout, dtype=np.int16)
                    sd.play(audio, samplerate=24000)
                    sd.wait()
            except Exception as e:
                logger.warning("Audio playback failed: %s", e)
        else:
            logger.warning("No audio playback method available. Install ffmpeg.")
