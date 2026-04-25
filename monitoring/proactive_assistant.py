"""Proactive Assistant for Jiro AI.

Monitors user behavior and provides unsolicited helpful suggestions,
study quizzes, productivity warnings, and schedule reminders.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger("jiro.monitoring.proactive")


class ProactiveAssistant:
    """Provides proactive, unsolicited assistance based on user activity."""

    def __init__(self, config_manager, ai_engine, activity_tracker, screen_monitor):
        self.config = config_manager
        self.ai_engine = ai_engine
        self.activity_tracker = activity_tracker
        self.screen_monitor = screen_monitor
        self.is_running = False
        self._speak_callback: Optional[Callable] = None
        self._distraction_warned = False

    def set_speak_callback(self, callback: Callable) -> None:
        """Set the callback function for speaking messages."""
        self._speak_callback = callback

    async def _speak(self, message: str) -> None:
        """Speak a message through the TTS system."""
        if self._speak_callback:
            await self._speak_callback(message)
        else:
            logger.info("Proactive message: %s", message)

    async def run(self) -> None:
        """Main proactive assistant loop."""
        self.is_running = True
        logger.info("Proactive assistant started")

        while self.is_running:
            try:
                await self._check_distractions()
                await self._check_study_quiz()
                await self._check_idle()
                await self._check_schedule_reminders()

                await asyncio.sleep(60)

            except Exception as e:
                logger.error("Proactive assistant error: %s", e)
                await asyncio.sleep(30)

    async def _check_distractions(self) -> None:
        """Warn about excessive distraction time."""
        if not self.config.get("monitoring.productivity_alerts", True):
            return

        context = self.screen_monitor.get_current_context()
        if context["window_category"] != "distraction":
            self._distraction_warned = False
            return

        threshold = self.config.get("monitoring.distraction_threshold_minutes", 15)
        time_on_current = context["time_on_current"] / 60

        if time_on_current >= threshold and not self._distraction_warned:
            self._distraction_warned = True

            warnings = [
                "You've been on this for a while. Maybe take a break and do something productive?",
                "You are watching too many reels which is not productive videos.",
                "You are just wasting your time. Let's focus on something meaningful.",
                "Don't spend so much time on distracting content. How about we work on something?",
                f"You've been on this for {time_on_current:.0f} minutes. Time to refocus!",
            ]
            await self._speak(random.choice(warnings))

    async def _check_study_quiz(self) -> None:
        """Quiz the user on recently studied topics."""
        if not self.config.get("proactive.enabled", True):
            return

        quiz_interval = self.config.get("proactive.study_quiz_interval_minutes", 30)
        unquizzed = self.activity_tracker.get_unquizzed_topics()

        if not unquizzed:
            return

        oldest_unquizzed = unquizzed[0]
        topic_time = datetime.fromisoformat(oldest_unquizzed["timestamp"])
        elapsed_minutes = (datetime.now() - topic_time).total_seconds() / 60

        if elapsed_minutes >= quiz_interval:
            topic = oldest_unquizzed["topic"]

            if self.ai_engine:
                question = await self.ai_engine.process(
                    f"Generate one quick review question about: '{topic}'. "
                    f"Make it concise and educational. Just ask the question directly."
                )
                await self._speak(f"Quick study review! {question}")
            else:
                await self._speak(
                    f"You were studying about '{topic}' earlier. "
                    f"Can you recall the key concepts?"
                )

            self.activity_tracker.mark_topic_quizzed(topic)

    async def _check_idle(self) -> None:
        """Engage the user if they've been idle."""
        if not self.config.get("proactive.enabled", True):
            return

        idle_interval = self.config.get("proactive.idle_chat_interval_minutes", 10)
        context = self.screen_monitor.get_current_context()

        if context["time_on_current"] / 60 >= idle_interval and context["window_category"] == "neutral":
            insights = self.activity_tracker.get_pattern_insights()
            if insights:
                await self._speak(insights[0])

    async def _check_schedule_reminders(self) -> None:
        """Check for upcoming schedule events and remind the user."""
        pass

    def stop(self) -> None:
        self.is_running = False
        logger.info("Proactive assistant stopped")
