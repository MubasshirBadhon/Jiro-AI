"""Short-term Memory - Current session memory for Jiro AI."""

import logging
from collections import deque
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("jiro.memory.short")


class ShortTermMemory:
    """In-memory storage for the current session."""

    def __init__(self, max_size: int = 200):
        self._conversations: deque = deque(maxlen=max_size)
        self._context: dict = {}
        self._session_start = datetime.now()

    def add(self, role: str, content: str) -> None:
        self._conversations.append({
            "role": role, "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def get_recent(self, n: int = 20) -> list[dict]:
        return list(self._conversations)[-n:]

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = {"value": value, "time": datetime.now().isoformat()}

    def get_context(self, key: str) -> Optional[Any]:
        ctx = self._context.get(key)
        return ctx["value"] if ctx else None

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        return [c for c in self._conversations if q in c.get("content", "").lower()]

    def clear(self) -> None:
        self._conversations.clear()
        self._context.clear()

    def get_history_for_ai(self) -> list[dict]:
        return [{"role": c["role"], "content": c["content"]} for c in self._conversations]
