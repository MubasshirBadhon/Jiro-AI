"""
JIRO AI - Your Personal AI Assistant
=====================================

Entry point that boots and orchestrates all Jiro AI components.

Usage:
    python main.py              # Full mode with GUI + voice + monitoring
    python main.py --cli        # CLI text-only mode
    python main.py --health     # Run health check
    python main.py --setup      # Interactive first-time setup
    python main.py --dashboard  # Show monitoring dashboard
    python main.py --set-passkey # Set/change passkey
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.permission_manager import PermissionManager
from core.api_key_manager import APIKeyManager
from core.health_checker import HealthChecker
from core.self_fixer import SelfFixer
from core.offline_model_manager import OfflineModelManager
from voice.stt import SpeechToText, WakeWordDetector
from voice.tts import TextToSpeech
from ai.brain import Brain
from monitoring.screen_monitor import ScreenMonitor
from monitoring.activity_recorder import ActivityRecorder
from monitoring.message_reader import MessageReader
from automation.alarm_manager import AlarmManager
from automation.schedule_manager import ScheduleManager
from automation.tab_controller import TabController
from automation.reminder_extractor import ReminderExtractor
from plugins.plugin_loader import PluginLoader
from plugins.plugin_generator import PluginGenerator
from plugins.api_key_prompter import APIKeyPrompter
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from memory.self_trainer import SelfTrainer
from security.passkey import PasskeyManager
from security.integrity_checker import IntegrityChecker
from ui.overlay import JiroOverlay
from ui.pdf_analyzer import PDFAnalyzer
from ui.dashboard import Dashboard

for d in ["data/memory", "data/recordings/screenshots", "data/models", "data/logs"]:
    (PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "data" / "logs" / "jiro.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("jiro")


def load_config() -> dict:
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        logger.error("config.json not found! Run: python main.py --setup")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


class Jiro:
    """Main Jiro AI orchestrator."""

    def __init__(self):
        logger.info("=" * 40)
        logger.info("  JIRO AI - Initializing...")
        logger.info("=" * 40)

        self.config = load_config()

        # Core
        self.permissions = PermissionManager()
        self.api_keys = APIKeyManager(self.config)
        self.passkey = PasskeyManager(self.config)
        self.offline_mgr = OfflineModelManager(self.config)

        # AI
        self.brain = Brain(self.config, self.api_keys)
        self.self_fixer = SelfFixer(self.config, self.brain)

        # Voice
        self.stt = SpeechToText(self.config, self.api_keys)
        self.tts = TextToSpeech(self.config)
        self.wake_word = WakeWordDetector(self.config, self.stt)

        # Memory
        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory()
        self.trainer = SelfTrainer(self.config, self.long_memory)

        # Monitoring
        self.screen = ScreenMonitor(self.config)
        self.activity = ActivityRecorder(self.config)
        self.msg_reader = MessageReader(self.config, self.brain)
        self.tab_ctrl = TabController(self.config)

        # Automation
        self.alarms = AlarmManager(self.config)
        self.schedule = ScheduleManager(self.config)
        self.reminders = ReminderExtractor(self.config, self.alarms)

        # Plugins
        self.plugins = PluginLoader(self.config, self.brain, self.self_fixer)
        self.plugin_gen = PluginGenerator(self.config, self.brain)
        self.api_prompter = APIKeyPrompter(self.config)

        # UI
        self.pdf = PDFAnalyzer(self.config, self.brain)
        self.dashboard = Dashboard(self.config, self.activity, self.schedule, self.alarms)
        self.integrity = IntegrityChecker()
        self.health = HealthChecker(self.config, self.api_keys)

        self.gui: JiroOverlay | None = None
        self._shutdown = asyncio.Event()

    async def initialize(self) -> None:
        """Initialize all components."""
        # Load API keys from Supabase if configured
        await self.api_keys.fetch_from_supabase()

        # Load plugins
        self.plugins.load_all()
        plugin_list = self.plugins.list_plugins()
        logger.info("Loaded %d plugins: %s", len(plugin_list), [p["name"] for p in plugin_list])

        # Check for missing API keys in plugins
        missing_keys = self.api_prompter.check_all_plugins(plugin_list)

        # Wire up monitoring callbacks
        self.screen.on_activity_change(self._on_activity)
        self.alarms.on_alarm(self._on_alarm)

        # Restore conversation history from long-term memory
        history = self.long_memory.get_conversations(20)
        self.brain.conversation_history = [
            {"role": c["role"], "content": c["content"]} for c in history
        ]

        logger.info("Jiro AI initialized successfully!")

    async def _on_activity(self, activity: dict) -> None:
        """Handle activity changes from screen monitor."""
        self.activity.record(activity)
        self.trainer.learn_from_activity(activity)

        # Check for distractions
        if activity["category"] == "distraction":
            warning = await self.tab_ctrl.handle_distraction(
                activity["window"], activity["duration"]
            )
            if warning:
                await self._speak(warning)

        # Check study topics for auto-quiz
        unquizzed = self.activity.get_unquizzed_topics()
        if unquizzed:
            from datetime import datetime
            topic = unquizzed[0]
            topic_time = datetime.fromisoformat(topic["timestamp"])
            elapsed = (datetime.now() - topic_time).total_seconds() / 60
            quiz_interval = self.config.get("proactive", {}).get("study_quiz_interval_minutes", 30)

            if elapsed >= quiz_interval:
                question = await self.brain.process(
                    f"Generate one quick review question about: '{topic['topic']}'. Just ask directly."
                )
                await self._speak(f"Quick quiz! {question}")
                self.activity.mark_quizzed(topic["topic"])

    async def _on_alarm(self, alarm: dict) -> None:
        """Handle triggered alarms."""
        await self._speak(f"Alarm! {alarm['message']}")

    async def _speak(self, text: str) -> None:
        """Speak and display text."""
        if self.gui:
            self.gui.display("Jiro", text)
        await self.tts.speak(text)

    async def process(self, text: str) -> str:
        """Process user input through the full pipeline."""
        self.short_memory.add("user", text)
        self.long_memory.add_conversation("user", text)

        if self.gui:
            self.gui.set_status("Thinking...", "#ffaa00")

        try:
            # Check for reminder extraction
            if self.reminders.should_extract(text):
                extracted = self.reminders.extract_and_set(text)
                if extracted:
                    for r in extracted:
                        from datetime import datetime
                        t = datetime.fromisoformat(r["time"])
                        await self._speak(f"I've set a reminder for {t.strftime('%I:%M %p')}.")

            # Check plugins first
            plugin = self.plugins.find_match(text)
            if plugin:
                logger.info("Routing to plugin: %s", plugin.name)
                response = await plugin.execute(text)
            # Check special commands
            elif any(w in text.lower() for w in ["schedule", "free", "busy", "calendar"]):
                response = self.schedule.format_today()
            elif any(w in text.lower() for w in ["alarm", "remind", "timer"]):
                alarm = self.alarms.set_alarm(text)
                if alarm:
                    from datetime import datetime
                    t = datetime.fromisoformat(alarm["time"])
                    response = f"Alarm set for {t.strftime('%I:%M %p')}!"
                else:
                    response = await self.brain.process(text)
            elif any(w in text.lower() for w in ["pdf", "analyze pdf", "read pdf"]):
                path = self.pdf.extract_path(text)
                if path:
                    response = await self.pdf.analyze(path)
                else:
                    response = "Please provide a PDF file path."
            elif text.lower() in ("health", "health check", "status"):
                report = await self.health.full_check()
                response = self.health.format_report(report)
            elif text.lower() in ("dashboard", "stats", "activity"):
                response = self.dashboard.format_dashboard()
            elif text.lower() in ("plugins", "list plugins"):
                plugins = self.plugins.list_plugins()
                response = "Loaded plugins:\n" + "\n".join(
                    f"  [{'+' if p['enabled'] else '-'}] {p['name']}: {p['description']}"
                    for p in plugins
                )
            elif text.lower().startswith("generate plugin"):
                desc = text[len("generate plugin"):].strip()
                if desc:
                    path = await self.plugin_gen.generate_plugin(desc)
                    if path:
                        self.plugins.reload_all()
                        response = f"Plugin generated and loaded: {path.name}"
                    else:
                        response = "Failed to generate plugin."
                else:
                    response = "Describe the plugin. Example: 'generate plugin weather checker'"
            elif text.lower() == "insights":
                response = self.trainer.get_insights()
            else:
                response = await self.brain.process(text)

        except Exception as e:
            logger.error("Processing error: %s", e)
            fix = await self.self_fixer.diagnose_and_fix(e, context=f"processing: {text}")
            if fix.get("fixed"):
                response = f"I fixed an issue ({fix['action']}) and am retrying..."
                response = await self.brain.process(text)
            else:
                response = f"I encountered an error: {e}. {fix.get('action', '')}"

        self.short_memory.add("assistant", response)
        self.long_memory.add_conversation("assistant", response)
        self.trainer.learn_from_conversation(text, response)

        if self.gui:
            self.gui.display("Jiro", response)
            self.gui.set_status("Online", "#00ff88")

        asyncio.create_task(self.tts.speak(response))
        return response

    async def _on_text(self, text: str) -> None:
        await self.process(text)

    async def _on_voice_start(self) -> None:
        if self.gui:
            self.gui.set_status("Listening...", "#ff6b6b")

    async def _on_voice_stop(self) -> None:
        pass

    async def _on_wake(self) -> None:
        logger.info("Wake word detected!")
        if self.gui:
            self.gui.set_status("Active", "#00ff88")
        await self._speak("Yes? I'm listening.")

        async def on_speech(text):
            await self.process(text)

        await self.stt.listen_continuous(on_speech)

    async def run_gui(self) -> None:
        """Run with full GUI."""
        # Permissions check
        perms = self.permissions.check_all_permissions(use_gui=True)

        # Passkey check
        if not self.passkey.authenticate_gui():
            logger.error("Authentication failed")
            print("Authentication failed. Exiting.")
            return

        await self.initialize()

        self.gui = JiroOverlay(
            self.config,
            on_text=self._on_text,
            on_voice_start=self._on_voice_start,
            on_voice_stop=self._on_voice_stop,
        )

        # Start background tasks
        tasks = []
        if self.permissions.is_granted("screen_monitoring"):
            tasks.append(asyncio.create_task(self.screen.run()))
        tasks.append(asyncio.create_task(self.alarms.alarm_loop()))

        if self.permissions.is_granted("microphone"):
            tasks.append(asyncio.create_task(self.wake_word.start(self._on_wake)))

        self.gui.run_threaded()

        try:
            await self._shutdown.wait()
        except asyncio.CancelledError:
            pass
        finally:
            self.screen.stop()
            self.wake_word.stop()
            self.stt.stop()
            self.tts.stop()
            self.long_memory.close()
            if self.gui:
                self.gui.destroy()

    async def run_cli(self) -> None:
        """Run in CLI text-only mode."""
        self.permissions.check_all_permissions(use_gui=False)

        if not self.passkey.authenticate_cli():
            return

        await self.initialize()

        # Start alarm loop in background
        alarm_task = asyncio.create_task(self.alarms.alarm_loop())

        print("\n" + "=" * 45)
        print("  JIRO AI - CLI Mode")
        print("=" * 45)
        print("  Commands: health, dashboard, plugins, insights,")
        print("  generate plugin <desc>, quit")
        print("=" * 45 + "\n")

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("You: ")
                )
                if user_input.lower() in ("quit", "exit", "bye"):
                    print("Jiro: Goodbye! See you later.")
                    break
                if not user_input.strip():
                    continue

                response = await self.process(user_input)
                print(f"\nJiro: {response}\n")

            except (KeyboardInterrupt, EOFError):
                print("\nJiro: Goodbye!")
                break

        alarm_task.cancel()
        self.long_memory.close()

    async def run_health(self) -> None:
        """Run health check."""
        report = await self.health.full_check()
        print(self.health.format_report(report))

    async def run_setup(self) -> None:
        """Interactive first-time setup."""
        print("\n" + "=" * 50)
        print("  JIRO AI - First Time Setup")
        print("=" * 50)

        # Permissions
        print("\n--- Permissions ---")
        self.permissions.check_all_permissions(use_gui=False)

        # API Keys
        print("\n--- API Keys ---")
        providers = ["groq", "gemini", "nvidia", "huggingface", "openrouter"]
        for provider in providers:
            current = self.config.get("api_keys", {}).get(provider, "")
            if current:
                print(f"  {provider}: configured")
            else:
                key = input(f"  Enter {provider} API key (Enter to skip): ").strip()
                if key:
                    self.api_keys.set_key(provider, key)
                    print(f"  {provider}: saved!")

        # Supabase
        print("\n--- Supabase (optional) ---")
        for field in ["backend_url", "anon_key"]:
            current = self.config.get("supabase", {}).get(field, "")
            if not current:
                val = input(f"  Enter Supabase {field} (Enter to skip): ").strip()
                if val:
                    self.config.setdefault("supabase", {})[field] = val

        # Save config
        with open(PROJECT_ROOT / "config.json", "w") as f:
            json.dump(self.config, f, indent=4)

        # Passkey
        print("\n--- Security ---")
        set_pass = input("  Set a passkey? (y/n): ").strip().lower()
        if set_pass == "y":
            passkey = input("  Enter passkey: ").strip()
            if passkey:
                self.passkey.set_passkey(passkey)

        # Integrity baseline
        self.integrity.save_baseline()

        # Offline model
        print("\n--- Offline Model ---")
        print(f"  {self.offline_mgr.get_status()}")
        dl = input("  Download offline model? (y/n): ").strip().lower()
        if dl == "y":
            await self.offline_mgr.download_model(
                progress_callback=lambda p: print(f"\r  Downloading: {p:.1f}%", end="")
            )
            print("\n  Done!")

        # Health check
        print("\n--- Health Check ---")
        report = await self.health.full_check()
        print(self.health.format_report(report))

        print("\n" + "=" * 50)
        print("  Setup complete! Run: python main.py")
        print("=" * 50 + "\n")

    def shutdown(self) -> None:
        logger.info("Shutting down Jiro AI...")
        self._shutdown.set()


def main():
    parser = argparse.ArgumentParser(description="Jiro AI - Your Personal Assistant")
    parser.add_argument("--cli", action="store_true", help="CLI text-only mode")
    parser.add_argument("--health", action="store_true", help="Run health check")
    parser.add_argument("--setup", action="store_true", help="First-time setup")
    parser.add_argument("--dashboard", action="store_true", help="Show dashboard")
    parser.add_argument("--set-passkey", action="store_true", help="Set/change passkey")
    args = parser.parse_args()

    jiro = Jiro()

    def sig_handler(sig, frame):
        jiro.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    if args.health:
        asyncio.run(jiro.run_health())
    elif args.setup:
        asyncio.run(jiro.run_setup())
    elif args.dashboard:
        print(jiro.dashboard.format_dashboard())
    elif args.set_passkey:
        passkey = input("Enter new passkey: ").strip()
        if passkey:
            jiro.passkey.set_passkey(passkey)
            print("Passkey set!")
    elif args.cli:
        asyncio.run(jiro.run_cli())
    else:
        asyncio.run(jiro.run_gui())


if __name__ == "__main__":
    main()
