"""Text-to-Speech module for Jiro AI. Streams speech sentence-by-sentence."""

import asyncio
import io
import logging
import re
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional

logger = logging.getLogger("jiro.tts")


class TextToSpeech:
    """Handles TTS with streaming sentence-by-sentence playback.

    Speaks each sentence as soon as it's ready while the AI continues
    generating the rest of the response in the background.
    """

    def __init__(self, config_manager):
        self.config = config_manager
        self.voice = config_manager.get("tts.voice", "en-US-GuyNeural")
        self.rate = config_manager.get("tts.rate", "+0%")
        self.volume = config_manager.get("tts.volume", "+0%")
        self.is_speaking = False
        self._stop_event = asyncio.Event()
        self._sentence_pattern = re.compile(r'[^.!?\n]+[.!?\n]+|[^.!?\n]+$')

    def split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences for streaming playback."""
        sentences = self._sentence_pattern.findall(text)
        return [s.strip() for s in sentences if s.strip()]

    async def speak_sentence(self, sentence: str) -> None:
        """Speak a single sentence using edge-tts."""
        if self._stop_event.is_set():
            return

        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                sentence, self.voice, rate=self.rate, volume=self.volume
            )

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name

            await communicate.save(tmp_path)

            if not self._stop_event.is_set():
                self.is_speaking = True
                await self._play_audio(tmp_path)
                self.is_speaking = False

            Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error("TTS failed for sentence: %s", e)
            self.is_speaking = False

    async def speak_streaming(self, text_generator: AsyncGenerator[str, None]) -> None:
        """Speak text as it streams in from the AI, sentence by sentence.

        This is the key feature: it starts speaking the first sentence
        while the AI is still generating the rest.
        """
        self._stop_event.clear()
        buffer = ""
        speak_tasks = []

        async for chunk in text_generator:
            if self._stop_event.is_set():
                break

            buffer += chunk
            sentences = self.split_into_sentences(buffer)

            if len(sentences) > 1:
                for sentence in sentences[:-1]:
                    task = asyncio.create_task(self._queue_speak(sentence))
                    speak_tasks.append(task)
                buffer = sentences[-1]

        if buffer.strip() and not self._stop_event.is_set():
            task = asyncio.create_task(self._queue_speak(buffer.strip()))
            speak_tasks.append(task)

        for task in speak_tasks:
            await task

    async def _queue_speak(self, sentence: str) -> None:
        """Queue a sentence for sequential speaking."""
        while self.is_speaking and not self._stop_event.is_set():
            await asyncio.sleep(0.05)
        if not self._stop_event.is_set():
            await self.speak_sentence(sentence)

    async def speak(self, text: str) -> None:
        """Speak full text, split into sentences for natural delivery."""
        self._stop_event.clear()
        sentences = self.split_into_sentences(text)

        for sentence in sentences:
            if self._stop_event.is_set():
                break
            await self.speak_sentence(sentence)

    def stop(self) -> None:
        """Stop current speech."""
        self._stop_event.set()
        self.is_speaking = False
        logger.info("Speech stopped")

    async def _play_audio(self, file_path: str) -> None:
        """Play an audio file."""
        try:
            import sounddevice as sd
            import numpy as np

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-i", file_path, "-f", "s16le", "-ar", "24000",
                "-ac", "1", "-loglevel", "quiet", "-",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()

            if stdout and not self._stop_event.is_set():
                audio_data = np.frombuffer(stdout, dtype=np.int16)
                sd.play(audio_data, samplerate=24000)
                sd.wait()

        except FileNotFoundError:
            import subprocess
            subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).wait()
        except Exception as e:
            logger.error("Audio playback failed: %s", e)

    async def list_voices(self) -> list[dict]:
        """List available TTS voices."""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [{"name": v["Name"], "locale": v["Locale"], "gender": v["Gender"]}
                    for v in voices]
        except Exception as e:
            logger.error("Failed to list voices: %s", e)
            return []
