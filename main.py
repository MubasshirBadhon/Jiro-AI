"""
JIRO AI - Your Personal AI Assistant (LOCAL-FIRST)
====================================================

Entry point that boots and orchestrates all Jiro AI components.
Auto-updates from GitHub on every startup.

Usage:
    python main.py              # Full mode with GUI + voice + monitoring
    python main.py --cli        # CLI text-only mode
    python main.py --health     # Run health check
    python main.py --setup      # Interactive first-time setup
    python main.py --dashboard  # Show monitoring dashboard
    python main.py --set-passkey # Set/change passkey
    python main.py --update     # Check for updates from GitHub
    python main.py --fix        # Run self-fixer diagnostics
    python main.py --report     # Show self-report of issues
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
from core.auto_updater import AutoUpdater
from core.self_reporter import SelfReporter
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

for d in ["data/memory", "data/recordings/screenshots", "data/models",
          "data/logs", "data/reports"]:
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
        SelfFixer({})._create_default_config()
        logger.info("Created default config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


class Jiro:
    """Main Jiro AI orchestrator - LOCAL-FIRST architecture."""

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
        self.updater = AutoUpdater(self.config)
        self.reporter = SelfReporter(self.config)

        # AI
        self.brain = Brain(self.config, self.api_keys)
        self.self_fixer = SelfFixer(self.config, self.brain)

        # Voice (local-first: pyttsx3 for TTS, Google free for STT)
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
        """Initialize all components. Auto-update runs FIRST."""
        # Auto-update from GitHub on every startup
        try:
            result = self.updater.auto_update_on_startup()
            if result.get("updated"):
                logger.info("Updated from GitHub! Restarting...")
                self.updater.restart_jiro()
                return
            else:
                logger.info("Update check: %s", result.get("message", ""))
        except Exception as e:
            logger.warning("Auto-update check failed: %s", e)
            self.reporter.log_error("auto_updater", str(e))

        # Run self-fixer startup checks
        fixes = await self.self_fixer.startup_check()
        for fix in fixes:
            if fix.get("action"):
                logger.info("Startup fix: %s", fix["action"])

        # Load API keys from Supabase if configured
        try:
            await self.api_keys.fetch_from_supabase()
        except Exception as e:
            logger.warning("Supabase fetch skipped: %s", e)

        # Check available providers
        providers = self.brain.get_available_providers()
        if not providers:
            logger.warning("No AI providers configured! Run: python main.py --setup")

        # Load plugins with error recovery
        self.plugins.load_all()
        plugin_list = self.plugins.list_plugins()
        logger.info("Loaded %d plugins", len(plugin_list))

        # Check for missing API keys in plugins
        self.api_prompter.check_all_plugins(plugin_list)

        # Wire up monitoring callbacks
        self.screen.on_activity_change(self._on_activity)
        self.alarms.on_alarm(self._on_alarm)

        # Restore conversation history from long-term memory
        history = self.long_memory.get_conversations(30)
        if history:
            self.brain.conversation_history = [
                {"role": c["role"], "content": c["content"]} for c in history
            ]
            logger.info("Restored %d messages from memory", len(history))

        # Load learned patterns
        failed_tasks = self.long_memory.get_patterns("failed_task", 10)
        for ft in failed_tasks:
            self.brain.log_failed_task(ft["data"].get("task", ""), ft["data"].get("error", ""))

        logger.info("Jiro AI ready! (%d providers, %d plugins, %d memories)",
                     len(providers), len(plugin_list), len(history))

    async def _on_activity(self, activity: dict) -> None:
        self.activity.record(activity)
        self.trainer.learn_from_activity(activity)

        if activity.get("category") == "distraction":
            warning = await self.tab_ctrl.handle_distraction(
                activity.get("window", ""), activity.get("duration", 0)
            )
            if warning:
                await self._speak(warning)

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
        await self._speak(f"Alarm! {alarm['message']}")

    async def _speak(self, text: str) -> None:
        if self.gui:
            self.gui.display("Jiro", text)
        try:
            await self.tts.speak(text)
        except Exception as e:
            logger.warning("TTS error: %s", e)
            self.reporter.log_error("tts", str(e))

    async def process(self, text: str) -> str:
        """Process user input through the full pipeline."""
        self.short_memory.add("user", text)
        self.long_memory.add_conversation("user", text)

        if self.gui:
            self.gui.set_status("Thinking...", "#ffaa00")

        try:
            lower = text.lower().strip()

            # Identity
            if lower in ("who are you", "what is your name", "what's your name"):
                response = ("I'm Jiro AI, pronounced like 'Zero'. I'm your personal AI assistant, "
                            "like JARVIS but for your daily life. How can I help you, boss?")

            # Open URL / website
            elif lower.startswith(("open ", "go to ", "visit ", "browse ")) and (
                "http" in lower or ".com" in lower or ".org" in lower or
                ".net" in lower or ".io" in lower or "www." in lower
            ):
                import re as _re
                url_match = _re.search(r'(https?://\S+|www\.\S+|\S+\.(?:com|org|net|io|edu|gov)\S*)', text)
                if url_match:
                    url = url_match.group(1)
                    if not url.startswith("http"):
                        url = "https://" + url
                    try:
                        import webbrowser
                        webbrowser.open(url)
                        response = f"Opening {url} in your browser!"
                    except Exception as e:
                        response = f"Could not open browser: {e}"
                else:
                    response = "I couldn't find a URL in your command."

            # Open apps
            elif lower.startswith(("open ", "launch ", "start ")) and "http" not in lower:
                import re as _re
                app_name = _re.sub(r'^(open|launch|start)\s+', '', lower).strip()
                if app_name:
                    plugin = self.plugins.find_match(text)
                    if plugin:
                        response = await plugin.execute(text)
                    else:
                        try:
                            import subprocess as _sp
                            import platform as _plat
                            if _plat.system() == "Windows":
                                _sp.Popen(["start", app_name], shell=True)
                            else:
                                _sp.Popen(["xdg-open", app_name])
                            response = f"Opening {app_name}!"
                        except Exception as e:
                            response = f"Could not open {app_name}: {e}"
                else:
                    response = await self.brain.process(text)

            # File creation commands
            elif any(lower.startswith(p) for p in [
                "create doc", "create document", "make doc", "write doc",
                "create pdf", "make pdf", "generate pdf",
                "create ppt", "create presentation", "make ppt",
                "create folder", "make folder", "new folder", "mkdir",
            ]):
                plugin = self.plugins.find_match(text)
                if plugin:
                    response = await plugin.execute(text)
                else:
                    # Direct handling if plugin not loaded
                    response = await self._handle_file_creation(text)

            # CLI command execution
            elif any(lower.startswith(p) for p in [
                "run command", "execute", "run cmd", "powershell",
                "cmd ", "terminal", "shell", "run shell", "system command",
            ]):
                plugin = self.plugins.find_match(text)
                if plugin:
                    response = await plugin.execute(text)
                else:
                    response = await self._handle_command(text)

            # Update command
            elif lower in ("update", "update yourself", "check for updates"):
                check = self.updater.check_for_updates()
                if check.get("available"):
                    result = self.updater.update()
                    response = result["message"]
                else:
                    response = "I'm already up to date!"

            # Self-report
            elif lower in ("report", "show report", "status report", "self report"):
                response = self.reporter.generate_report()

            # Download offline model
            elif lower in ("download model", "offline model", "download offline"):
                await self._speak("Checking your system and downloading the best offline model...")
                try:
                    result = await self.self_fixer.install_offline_llm()
                    if result.get("fixed"):
                        dl = await self.offline_mgr.download_model(
                            progress_callback=lambda p: logger.info("Download: %.1f%%", p)
                        )
                        if dl:
                            response = "Offline model downloaded! I can now work without internet."
                        else:
                            response = "Model download failed. Check your internet and try again."
                    else:
                        response = f"Could not set up offline mode: {result.get('action', 'Unknown error')}"
                except Exception as e:
                    response = f"Offline model setup failed: {e}"

            # Self-fix
            elif lower in ("fix yourself", "self fix", "diagnose"):
                fixes = await self.self_fixer.fix_all_issues()
                fixed = [f for f in fixes if f.get("fixed")]
                failed = [f for f in fixes if not f.get("fixed") and f.get("action")]
                parts = []
                if fixed:
                    parts.append(f"Fixed {len(fixed)} issues: " +
                                 ", ".join(f["action"] for f in fixed))
                if failed:
                    parts.append(f"Could not fix: " +
                                 ", ".join(f["action"] for f in failed))
                if not parts:
                    parts.append("Everything looks good! No issues found.")
                response = " ".join(parts)

            # Auto-start registration
            elif lower in ("register autostart", "auto start", "startup"):
                msg = self.updater.register_autostart()
                response = msg

            # Reminder extraction
            elif self.reminders.should_extract(text):
                extracted = self.reminders.extract_and_set(text)
                if extracted:
                    from datetime import datetime
                    msgs = []
                    for r in extracted:
                        t = datetime.fromisoformat(r["time"])
                        msgs.append(f"reminder for {t.strftime('%I:%M %p')}")
                    response = f"I've set a {', '.join(msgs)}."
                    response += " " + await self.brain.process(text)
                else:
                    response = await self.brain.process(text)

            # Check plugins
            else:
                plugin = self.plugins.find_match(text)
                if plugin:
                    logger.info("Routing to plugin: %s", plugin.name)
                    try:
                        response = await plugin.execute(text)
                    except Exception as e:
                        self.reporter.log_failure(f"plugin:{plugin.name}", str(e))
                        fix = await self.self_fixer.fix_plugin(
                            Path(f"plugins/{type(plugin).__module__.split('.')[-1]}.py"), e
                        )
                        response = f"Plugin error. {fix.get('action', str(e))}"

                elif any(w in lower for w in ["schedule", "free", "busy", "calendar"]):
                    response = self.schedule.format_today()
                elif any(w in lower for w in ["alarm", "remind", "timer"]):
                    alarm = self.alarms.set_alarm(text)
                    if alarm:
                        from datetime import datetime
                        t = datetime.fromisoformat(alarm["time"])
                        response = f"Alarm set for {t.strftime('%I:%M %p')}!"
                    else:
                        response = await self.brain.process(text)
                elif any(w in lower for w in ["pdf", "analyze pdf", "read pdf"]):
                    path = self.pdf.extract_path(text)
                    if path:
                        response = await self.pdf.analyze(path, text)
                    else:
                        response = await self.pdf.analyze_recent(text)
                elif lower in ("health", "health check", "status"):
                    report = await self.health.full_check()
                    response = self.health.format_report(report)
                elif lower in ("dashboard", "stats", "activity"):
                    response = self.dashboard.format_dashboard()
                elif lower in ("plugins", "list plugins"):
                    plugins = self.plugins.list_plugins()
                    response = "Loaded plugins:\n" + "\n".join(
                        f"  [{'+' if p['enabled'] else '-'}] {p['name']}: {p['description']}"
                        for p in plugins
                    )
                elif lower.startswith("generate plugin"):
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
                elif lower == "insights":
                    response = self.trainer.get_insights()
                elif any(w in lower for w in ["remember", "recall", "what did i say",
                                               "what did we talk", "past conversation"]):
                    search_term = lower.replace("remember", "").replace("recall", "").strip()
                    if search_term:
                        results = self.long_memory.search_conversations(search_term, 5)
                    else:
                        results = self.long_memory.get_conversations(10)
                    if results:
                        parts = ["Here's what I remember:\n"]
                        for r in results:
                            role = "You" if r["role"] == "user" else "Me"
                            content = r["content"][:100]
                            parts.append(f"  {role}: {content}")
                        response = "\n".join(parts)
                    else:
                        response = "I don't have any past conversations to recall yet."
                elif lower in ("what can you do", "help", "commands"):
                    response = (
                        "Here's what I can do, boss:\n\n"
                        "  Voice: Say 'Jiro' to wake me up, then speak your command\n"
                        "  Create files: 'create doc report', 'create pdf notes', 'create ppt slides'\n"
                        "  Create folders: 'create folder MyProject'\n"
                        "  Run commands: 'run command dir', 'powershell Get-Process'\n"
                        "  Open URLs: 'open google.com'\n"
                        "  Open apps: 'open notepad', 'open chrome'\n"
                        "  Screenshot: 'what's on my screen' (uses local OCR first)\n"
                        "  PDF: 'analyze pdf' or 'read pdf <path>'\n"
                        "  Memory: 'remember <topic>' to search past conversations\n"
                        "  Study: flashcards, quizzes, GPA calculator, study planner\n"
                        "  Schedule: 'my schedule', 'add event'\n"
                        "  Alarms: 'set alarm for 5pm'\n"
                        "  Offline: 'download model' for offline AI\n"
                        "  Updates: 'update yourself' (also auto-updates on startup)\n"
                        "  Auto-start: 'register autostart' to start with Windows\n"
                        "  Self-fix: 'fix yourself'\n"
                        "  Reports: 'show report' for self-assessment\n"
                        "  Health: 'health check'\n"
                        "  And 69+ plugins! Type 'list plugins' to see all."
                    )
                else:
                    response = await self.brain.process(text)

        except Exception as e:
            logger.error("Processing error: %s", e)
            self.brain.log_failed_task(text, str(e))
            self.long_memory.add_pattern("failed_task", {"task": text, "error": str(e)})
            self.reporter.log_failure(text, str(e))

            fix = await self.self_fixer.diagnose_and_fix(e, context=f"processing: {text}")
            if fix.get("fixed"):
                try:
                    response = await self.brain.process(text)
                except Exception:
                    response = f"I fixed an issue ({fix['action']}) but still having trouble. Try again?"
            else:
                response = f"Sorry boss, I hit an error: {fix.get('action', str(e))}"

        self.short_memory.add("assistant", response)
        self.long_memory.add_conversation("assistant", response)
        self.trainer.learn_from_conversation(text, response)

        if self.gui:
            self.gui.display("Jiro", response)
            self.gui.set_status("Online", "#00ff88")

        # Speak in background
        try:
            asyncio.ensure_future(self.tts.speak(response))
        except Exception:
            pass
        return response

    async def _handle_file_creation(self, text: str) -> str:
        """Handle file creation commands directly."""
        lower = text.lower()
        if "doc" in lower:
            try:
                from plugins.doc_creator_plugin import handle
                return await handle(text)
            except Exception as e:
                return f"Doc creation failed: {e}"
        elif "pdf" in lower:
            try:
                from plugins.pdf_creator_plugin import handle
                return await handle(text)
            except Exception as e:
                return f"PDF creation failed: {e}"
        elif "ppt" in lower or "presentation" in lower:
            try:
                from plugins.pptx_creator_plugin import handle
                return await handle(text)
            except Exception as e:
                return f"PPT creation failed: {e}"
        elif "folder" in lower or "mkdir" in lower:
            try:
                from plugins.folder_creator_plugin import handle
                return await handle(text)
            except Exception as e:
                return f"Folder creation failed: {e}"
        return "I can create: doc, pdf, ppt, or folders. Example: 'create doc report My content here'"

    async def _handle_command(self, text: str) -> str:
        """Handle CLI command execution directly."""
        try:
            from plugins.command_executor_plugin import handle
            return await handle(text)
        except Exception as e:
            return f"Command execution failed: {e}"

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
        await self._speak("Yes boss?")

        # Listen for ONE command, process it, then return to wake word
        text = await self.stt.listen_once(duration=10.0)
        if text:
            logger.info("Command after wake: %s", text)
            await self.process(text)
        else:
            await self._speak("I didn't catch that, boss. Say my name again when you need me.")

        if self.gui:
            self.gui.set_status("Listening for wake word...", "#4488ff")

    async def run_gui(self) -> None:
        """Run with full GUI."""
        perms = self.permissions.check_all_permissions(use_gui=True)

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

        tasks = []
        if self.permissions.is_granted("screen_monitoring"):
            tasks.append(asyncio.create_task(self.screen.run()))
        tasks.append(asyncio.create_task(self.alarms.alarm_loop()))

        if self.permissions.is_granted("microphone"):
            tasks.append(asyncio.create_task(self.wake_word.start(self._on_wake)))

        asyncio.create_task(self._speak(
            "Jiro AI online. Ready to assist you, boss."
        ))

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

        alarm_task = asyncio.create_task(self.alarms.alarm_loop())

        print("\n" + "=" * 50)
        print("  JIRO AI - CLI Mode (pronounced 'Zero')")
        print("  LOCAL-FIRST: Offline LLM -> API fallback")
        print("=" * 50)
        providers = self.brain.get_available_providers()
        print(f"  Providers: {', '.join(providers) if providers else 'NONE - run --setup'}")
        print(f"  Plugins: {len(self.plugins.list_plugins())}")
        print()
        print("  New commands: create doc/pdf/ppt, create folder,")
        print("  run command <cmd>, powershell <cmd>, show report,")
        print("  register autostart, voice, quit")
        print("=" * 50 + "\n")

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("You: ")
                )
                if user_input.lower() in ("quit", "exit", "bye"):
                    print("\nJiro: Goodbye boss! See you later.")
                    break
                if not user_input.strip():
                    continue

                if user_input.lower() == "voice":
                    print("Jiro: I'm listening... (speak now)")
                    text = await self.stt.listen_once(duration=8.0)
                    if text:
                        print(f"  [Heard: {text}]")
                        user_input = text
                    else:
                        print("  [Could not hear anything. Try again or type instead.]")
                        continue

                response = await self.process(user_input)
                print(f"\nJiro: {response}\n")

            except (KeyboardInterrupt, EOFError):
                print("\nJiro: Goodbye boss!")
                break

        alarm_task.cancel()
        self.long_memory.close()

    async def run_health(self) -> None:
        report = await self.health.full_check()
        print(self.health.format_report(report))

    async def run_fix(self) -> None:
        print("\n--- Jiro AI Self-Fixer ---\n")
        fixes = await self.self_fixer.fix_all_issues()
        for fix in fixes:
            status = "FIXED" if fix.get("fixed") else "INFO"
            print(f"  [{status}] {fix.get('action', 'Unknown')}")
        print(f"\nTotal: {len(fixes)} items checked")

    async def run_update(self) -> None:
        print("\n--- Jiro AI Auto-Updater ---\n")
        check = self.updater.check_for_updates()
        if check.get("available"):
            print(f"  {check['commits']} new update(s) available!")
            for detail in check.get("details", []):
                print(f"    {detail}")
            confirm = input("\n  Apply updates? (y/n): ").strip().lower()
            if confirm == "y":
                result = self.updater.update()
                print(f"  {result['message']}")
            else:
                print("  Skipped.")
        elif check.get("error"):
            print(f"  Error: {check['error']}")
        else:
            print("  Already up to date!")

    async def run_report(self) -> None:
        """Show self-assessment report."""
        print(self.reporter.generate_report())

    async def run_setup(self) -> None:
        """Interactive first-time setup."""
        print("\n" + "=" * 50)
        print("  JIRO AI - First Time Setup")
        print("  (Your personal JARVIS-like assistant)")
        print("  LOCAL-FIRST: Works offline, APIs enhance it")
        print("=" * 50)

        print("\n--- Auto-fixing dependencies ---")
        fixes = await self.self_fixer.startup_check()
        for fix in fixes:
            if fix.get("action"):
                status = "OK" if fix.get("fixed") else "WARN"
                print(f"  [{status}] {fix['action']}")

        print("\n--- Permissions ---")
        self.permissions.check_all_permissions(use_gui=False)

        print("\n--- API Keys (optional - Jiro works offline too) ---")
        print("  Get free API keys from:")
        print("    Groq (recommended): https://console.groq.com")
        print("    Gemini: https://aistudio.google.com")
        print("    HuggingFace: https://huggingface.co/settings/tokens")
        print("    OpenRouter: https://openrouter.ai/keys")
        print()

        providers = ["groq", "gemini", "huggingface", "openrouter"]
        for provider in providers:
            current = self.config.get("api_keys", {}).get(provider, "")
            if current:
                print(f"  {provider}: already configured")
            else:
                key = input(f"  Enter {provider} API key (Enter to skip): ").strip()
                if key:
                    self.api_keys.set_key(provider, key)
                    print(f"  {provider}: saved!")

        print("\n--- Supabase (optional) ---")
        for field in ["backend_url", "anon_key"]:
            current = self.config.get("supabase", {}).get(field, "")
            if not current:
                val = input(f"  Enter Supabase {field} (Enter to skip): ").strip()
                if val:
                    self.config.setdefault("supabase", {})[field] = val

        with open(PROJECT_ROOT / "config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

        print("\n--- Security ---")
        set_pass = input("  Set a passkey? (y/n): ").strip().lower()
        if set_pass == "y":
            passkey = input("  Enter passkey: ").strip()
            if passkey:
                self.passkey.set_passkey(passkey)

        self.integrity.save_baseline()

        print("\n--- Offline Model ---")
        print(f"  {self.offline_mgr.get_status()}")
        dl = input("  Download offline model? (y/n): ").strip().lower()
        if dl == "y":
            result = await self.self_fixer.install_offline_llm()
            print(f"  {result['action']}")
            if result.get("fixed"):
                await self.offline_mgr.download_model(
                    progress_callback=lambda p: print(f"\r  Downloading: {p:.1f}%", end="")
                )
                print("\n  Done!")

        print("\n--- Auto-Start ---")
        autostart = input("  Register Jiro to start with Windows? (y/n): ").strip().lower()
        if autostart == "y":
            msg = self.updater.register_autostart()
            print(f"  {msg}")

        print("\n--- Final Health Check ---")
        report = await self.health.full_check()
        print(self.health.format_report(report))

        print("\n" + "=" * 50)
        print("  Setup complete! Run: python main.py")
        print("  Or for text-only: python main.py --cli")
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
    parser.add_argument("--update", action="store_true", help="Check for updates")
    parser.add_argument("--fix", action="store_true", help="Run self-fixer")
    parser.add_argument("--report", action="store_true", help="Show self-report")
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
    elif args.update:
        asyncio.run(jiro.run_update())
    elif args.fix:
        asyncio.run(jiro.run_fix())
    elif args.report:
        asyncio.run(jiro.run_report())
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
