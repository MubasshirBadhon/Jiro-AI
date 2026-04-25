"""
Jiro AI - Your Personal AI Assistant

Main entry point that orchestrates all Jiro AI components:
- Speech-to-Text (STT) via Groq Whisper
- Text-to-Speech (TTS) with streaming sentence-by-sentence
- Multi-provider AI Engine (NVIDIA, Groq, Gemini, HuggingFace, OpenRouter)
- Dynamic Plugin System
- Always-on-top GUI
- Screen Monitoring & Productivity Tracking
- Proactive Assistant
- Wake Word Detection

Usage:
    python main.py              # Start with GUI
    python main.py --no-gui     # Start without GUI (voice only)
    python main.py --health     # Run health check
    python main.py --cli        # CLI mode (text only)
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import ConfigManager
from core.stt import SpeechToText
from core.tts import TextToSpeech
from core.ai_engine import AIEngine
from core.plugin_loader import PluginLoader
from core.wake_word import WakeWordDetector
from gui.overlay import JiroGUI
from monitoring.screen_monitor import ScreenMonitor
from monitoring.activity_tracker import ActivityTracker
from monitoring.proactive_assistant import ProactiveAssistant
from utils.health_checker import HealthChecker
from utils.memory import Memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "data" / "jiro.log"),
    ],
)
logger = logging.getLogger("jiro.main")


class JiroAssistant:
    """Main Jiro AI Assistant orchestrator."""

    def __init__(self):
        logger.info("Initializing Jiro AI...")

        self.config = ConfigManager()
        self.memory = Memory(self.config)
        self.stt = SpeechToText(self.config)
        self.tts = TextToSpeech(self.config)
        self.ai_engine = AIEngine(self.config)
        self.plugin_loader = PluginLoader(self.config, self.ai_engine)
        self.wake_word = WakeWordDetector(self.config, self.stt)
        self.screen_monitor = ScreenMonitor(self.config)
        self.activity_tracker = ActivityTracker(self.config)
        self.proactive = ProactiveAssistant(
            self.config, self.ai_engine, self.activity_tracker, self.screen_monitor
        )
        self.health_checker = HealthChecker(self.config)

        self.gui: JiroGUI | None = None
        self._is_active = False
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize all components."""
        await self.config.load_from_supabase()

        self.plugin_loader.load_all()
        plugins = self.plugin_loader.list_plugins()
        logger.info("Loaded %d plugins: %s", len(plugins), [p["name"] for p in plugins])

        self.screen_monitor.add_activity_callback(self._on_activity_change)
        self.proactive.set_speak_callback(self._speak)

        self.ai_engine.conversation_history = [
            {"role": m["role"], "content": m["content"]}
            for m in self.memory.get_recent_conversations(20)
        ]

        logger.info("Jiro AI initialized successfully!")

    async def _on_activity_change(self, activity: dict) -> None:
        """Handle activity change from screen monitor."""
        self.activity_tracker.record_activity(activity)

        productivity_plugin = self.plugin_loader.get_plugin("productivity")
        if productivity_plugin:
            productivity_plugin.log_activity(
                activity.get("window", "Unknown"),
                activity.get("duration", 0),
            )

    async def _speak(self, text: str) -> None:
        """Speak text through TTS and show in GUI."""
        if self.gui:
            self.gui.display_message("Jiro", text)
        await self.tts.speak(text)

    async def process_input(self, text: str) -> str:
        """Process user input through the AI pipeline."""
        self.memory.add_conversation("user", text)

        if self.gui:
            self.gui.set_status("Thinking...", "#ffaa00")

        matching_plugin = self.plugin_loader.find_matching_plugin(text)
        if matching_plugin:
            logger.info("Routing to plugin: %s", matching_plugin.name)
            response = await matching_plugin.execute(text)
        else:
            response = await self.ai_engine.process(text)

        self.memory.add_conversation("assistant", response)

        if self.gui:
            self.gui.display_message("Jiro", response)
            self.gui.set_status("Online", "#00ff88")

        asyncio.create_task(self.tts.speak(response))

        return response

    async def process_input_streaming(self, text: str) -> None:
        """Process input with streaming TTS for human-like speech."""
        self.memory.add_conversation("user", text)

        if self.gui:
            self.gui.set_status("Thinking...", "#ffaa00")

        matching_plugin = self.plugin_loader.find_matching_plugin(text)
        if matching_plugin:
            response = await matching_plugin.execute(text)
            self.memory.add_conversation("assistant", response)
            if self.gui:
                self.gui.display_message("Jiro", response)
                self.gui.set_status("Online", "#00ff88")
            await self.tts.speak(response)
        else:
            stream = self.ai_engine.stream_process(text)
            await self.tts.speak_streaming(stream)
            if self.gui:
                self.gui.set_status("Online", "#00ff88")

    async def _on_text_input(self, text: str) -> None:
        """Handle text input from GUI."""
        await self.process_input(text)

    async def _on_voice_start(self) -> None:
        """Handle voice recording start."""
        if self.gui:
            self.gui.set_status("Listening...", "#ff6b6b")

    async def _on_voice_stop(self) -> None:
        """Handle voice recording stop."""
        pass

    async def _on_wake_word(self) -> None:
        """Handle wake word detection."""
        self._is_active = True
        logger.info("Wake word detected! Jiro is active.")

        if self.gui:
            self.gui.set_status("Active", "#00ff88")

        await self._speak("Yes? I'm listening.")

        async def on_speech(text: str):
            await self.process_input_streaming(text)

        await self.stt.listen_continuous(on_speech)

    async def run_with_gui(self) -> None:
        """Run Jiro AI with the GUI overlay."""
        await self.initialize()

        self.gui = JiroGUI(
            self.config,
            on_text_input=self._on_text_input,
            on_voice_start=self._on_voice_start,
            on_voice_stop=self._on_voice_stop,
        )

        monitor_task = asyncio.create_task(self.screen_monitor.monitor_loop())
        proactive_task = asyncio.create_task(self.proactive.run())
        wake_task = asyncio.create_task(self.wake_word.start(self._on_wake_word))

        gui_thread = self.gui.run_in_thread()

        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            self.screen_monitor.stop()
            self.proactive.stop()
            self.wake_word.stop()
            self.stt.stop_listening()
            if self.gui:
                self.gui.destroy()

    async def run_cli(self) -> None:
        """Run Jiro AI in CLI mode (text only)."""
        await self.initialize()

        print("\n=== Jiro AI - CLI Mode ===")
        print("Type your message (or 'quit' to exit, 'health' for status):\n")

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("You: ")
                )

                if user_input.lower() in ("quit", "exit", "bye"):
                    print("Jiro: Goodbye! See you later.")
                    break

                if user_input.lower() == "health":
                    results = await self.health_checker.check_all()
                    print(self.health_checker.format_report(results))
                    continue

                if user_input.lower() == "plugins":
                    plugins = self.plugin_loader.list_plugins()
                    for p in plugins:
                        status = "ON" if p["enabled"] else "OFF"
                        print(f"  [{status}] {p['name']}: {p['description']}")
                    continue

                if user_input.lower() == "reload":
                    self.plugin_loader.reload_all()
                    print("Plugins reloaded!")
                    continue

                response = await self.process_input(user_input)
                print(f"Jiro: {response}\n")

            except (KeyboardInterrupt, EOFError):
                print("\nJiro: Goodbye!")
                break

    async def run_health_check(self) -> None:
        """Run health check and print report."""
        results = await self.health_checker.check_all()
        print(self.health_checker.format_report(results))

    def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down Jiro AI...")
        self._shutdown_event.set()
        self.screen_monitor.stop()
        self.proactive.stop()
        self.wake_word.stop()
        self.stt.stop_listening()
        self.tts.stop()


def main():
    parser = argparse.ArgumentParser(description="Jiro AI - Your Personal Assistant")
    parser.add_argument("--no-gui", action="store_true", help="Start without GUI")
    parser.add_argument("--cli", action="store_true", help="CLI mode (text only)")
    parser.add_argument("--health", action="store_true", help="Run health check")
    args = parser.parse_args()

    jiro = JiroAssistant()

    def signal_handler(sig, frame):
        jiro.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.health:
        asyncio.run(jiro.run_health_check())
    elif args.cli:
        asyncio.run(jiro.run_cli())
    elif args.no_gui:
        asyncio.run(jiro.run_with_gui())
    else:
        asyncio.run(jiro.run_with_gui())


if __name__ == "__main__":
    main()
