"""Text-to-Speech for Jiro AI - Local-first, no API needed.

Priority chain:
1. pyttsx3 (Windows SAPI5 / Linux espeak) - fully offline, instant
2. edge-tts + pygame playback - better quality, needs internet
3. PowerShell MediaPlayer (Windows fallback)

Speaks sentence-by-sentence for natural feel.
"""

import asyncio
import logging
import platform
import re
from typing import AsyncGenerator

logger = logging.getLogger("jiro.voice.tts")


class TextToSpeech:
    """Local-first TTS. Uses pyttsx3 (offline) with edge-tts as quality upgrade."""

    def __init__(self, config: dict):
        self._config = config
        tts_config = config.get("tts", {})
        self.rate = tts_config.get("rate_wpm", 180)  # Words per minute for pyttsx3
        self.volume = tts_config.get("volume_level", 0.9)
        self.is_speaking = False
        self._stop = asyncio.Event()
        self._sentence_re = re.compile(r'[^.!?\n]+[.!?\n]+|[^.!?\n]+$')
        self._engine = None
        self._method = self._init_engine()
        logger.info("TTS method: %s", self._method)

    def _init_engine(self) -> str:
        """Initialize the best available TTS engine."""
        # Try pyttsx3 first (local, offline, works on Windows/Linux/Mac)
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self.rate)
            self._engine.setProperty('volume', self.volume)
            # Try to set a good English voice
            voices = self._engine.getProperty('voices')
            for v in voices:
                if 'english' in v.name.lower() or 'david' in v.name.lower() or 'zira' in v.name.lower():
                    self._engine.setProperty('voice', v.id)
                    break
            return "pyttsx3"
        except Exception as e:
            logger.warning("pyttsx3 not available: %s", e)

        # Check if edge-tts + a playback method works
        try:
            import edge_tts
            return "edge_tts"
        except ImportError:
            pass

        # On Windows, we can use PowerShell Add-Type for speech
        if platform.system() == "Windows":
            return "powershell_speech"

        return "none"

    def split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in self._sentence_re.findall(text) if s.strip()]

    async def speak_sentence(self, sentence: str) -> None:
        """Speak a single sentence using the best available method."""
        if self._stop.is_set():
            return

        self.is_speaking = True
        try:
            if self._method == "pyttsx3":
                await self._speak_pyttsx3(sentence)
            elif self._method == "edge_tts":
                await self._speak_edge_tts(sentence)
            elif self._method == "powershell_speech":
                await self._speak_powershell(sentence)
            else:
                logger.warning("No TTS available. Install pyttsx3: pip install pyttsx3")
        except Exception as e:
            logger.error("TTS error: %s", e)
        finally:
            self.is_speaking = False

    async def _speak_pyttsx3(self, text: str) -> None:
        """Speak using pyttsx3 (local, offline)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._pyttsx3_say, text)

    def _pyttsx3_say(self, text: str) -> None:
        """Blocking pyttsx3 speak (runs in executor)."""
        if self._engine is None:
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            logger.error("pyttsx3 say failed: %s", e)
            # Re-init engine on failure
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty('rate', self.rate)
                self._engine.setProperty('volume', self.volume)
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass

    async def _speak_edge_tts(self, sentence: str) -> None:
        """Speak using edge-tts + playback."""
        import tempfile
        from pathlib import Path

        try:
            import edge_tts
            comm = edge_tts.Communicate(sentence, "en-US-GuyNeural",
                                         rate="+15%", volume="+0%")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            await comm.save(tmp_path)

            if not self._stop.is_set():
                await self._play_file(tmp_path)

            Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.error("edge-tts error: %s", e)

    async def _play_file(self, path: str) -> None:
        """Play an audio file using best available method."""
        # Try pygame
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._stop.is_set():
                await asyncio.sleep(0.1)
            pygame.mixer.music.unload()
            return
        except Exception:
            pass

        # Try ffplay
        import shutil
        if shutil.which("ffplay"):
            proc = await asyncio.create_subprocess_exec(
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return

        # PowerShell fallback on Windows
        if platform.system() == "Windows":
            await self._play_powershell(path)

    async def _play_powershell(self, path: str) -> None:
        """Play audio via PowerShell on Windows."""
        ps_cmd = (
            f'Add-Type -AssemblyName presentationCore; '
            f'$p = New-Object System.Windows.Media.MediaPlayer; '
            f'$p.Open("{path}"); $p.Play(); '
            f'Start-Sleep -Milliseconds 500; '
            f'while($p.Position -lt $p.NaturalDuration.TimeSpan){{ Start-Sleep -Milliseconds 100 }}; '
            f'$p.Close()'
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-Command", ps_cmd,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            logger.warning("PowerShell playback failed: %s", e)

    async def _speak_powershell(self, text: str) -> None:
        """Speak using Windows built-in speech synthesis via PowerShell."""
        clean = text.replace("'", "''").replace('"', '`"')
        ps_cmd = (
            f'Add-Type -AssemblyName System.Speech; '
            f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
            f'$s.Rate = 2; $s.Speak("{clean}"); $s.Dispose()'
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-Command", ps_cmd,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception as e:
            logger.warning("PowerShell speech failed: %s", e)

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
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
