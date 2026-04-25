"""Memory System for Jiro AI.

Persistent memory for conversations, user preferences, learned patterns,
and contextual information that helps Jiro be a better assistant.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jiro.utils.memory")

MEMORY_FILE = Path(__file__).parent.parent / "data" / "memory" / "jiro_memory.json"


class Memory:
    """Persistent memory system for Jiro AI."""

    def __init__(self, config_manager):
        self.config = config_manager
        self._data: dict = {
            "conversations": [],
            "user_preferences": {},
            "learned_patterns": [],
            "reminders": [],
            "context": {},
        }
        self._load()

    def _load(self) -> None:
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load memory: %s", e)

    def _save(self) -> None:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)

    def add_conversation(self, role: str, content: str) -> None:
        """Store a conversation turn."""
        max_convos = self.config.get("memory.max_conversation_history", 100)
        self._data["conversations"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self._data["conversations"] = self._data["conversations"][-max_convos:]
        self._save()

    def get_recent_conversations(self, n: int = 20) -> list[dict]:
        """Get the N most recent conversation turns."""
        return self._data["conversations"][-n:]

    def set_preference(self, key: str, value: Any) -> None:
        """Store a user preference."""
        self._data["user_preferences"][key] = value
        self._save()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self._data["user_preferences"].get(key, default)

    def add_pattern(self, pattern: dict) -> None:
        """Record a learned behavior pattern."""
        pattern["learned_at"] = datetime.now().isoformat()
        self._data["learned_patterns"].append(pattern)
        self._data["learned_patterns"] = self._data["learned_patterns"][-200:]
        self._save()

    def add_reminder(self, reminder: dict) -> None:
        """Add a reminder."""
        reminder["created_at"] = datetime.now().isoformat()
        self._data["reminders"].append(reminder)
        self._save()

    def get_pending_reminders(self) -> list[dict]:
        """Get reminders that haven't been triggered yet."""
        now = datetime.now()
        return [
            r for r in self._data["reminders"]
            if not r.get("triggered") and
            datetime.fromisoformat(r.get("time", now.isoformat())) <= now
        ]

    def set_context(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self._data["context"][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
        }
        self._save()

    def get_context(self, key: str) -> Optional[Any]:
        """Get a context variable."""
        ctx = self._data["context"].get(key)
        return ctx["value"] if ctx else None

    def get_summary(self) -> str:
        """Get a summary of stored memory."""
        return (
            f"Memory: {len(self._data['conversations'])} conversations, "
            f"{len(self._data['user_preferences'])} preferences, "
            f"{len(self._data['learned_patterns'])} patterns, "
            f"{len(self._data['reminders'])} reminders"
        )

    def search_conversations(self, query: str) -> list[dict]:
        """Search through conversation history."""
        query_lower = query.lower()
        return [
            c for c in self._data["conversations"]
            if query_lower in c.get("content", "").lower()
        ]

    def clear(self, section: Optional[str] = None) -> None:
        """Clear memory, optionally only a specific section."""
        if section:
            if section in self._data:
                if isinstance(self._data[section], list):
                    self._data[section] = []
                elif isinstance(self._data[section], dict):
                    self._data[section] = {}
        else:
            self._data = {
                "conversations": [],
                "user_preferences": {},
                "learned_patterns": [],
                "reminders": [],
                "context": {},
            }
        self._save()
