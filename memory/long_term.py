"""Long-term Memory - SQLite persistent memory for Jiro AI.

Stores conversations, preferences, patterns, and learned behaviors
across sessions using SQLite for reliability and performance.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jiro.memory.long")

DB_PATH = Path(__file__).parent.parent / "data" / "memory" / "jiro_memory.db"


class LongTermMemory:
    """SQLite-backed persistent memory."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                learned_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                time TEXT NOT NULL,
                triggered INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);
            CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(time);
        """)
        self._conn.commit()

    def add_conversation(self, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_conversations(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def search_conversations(self, query: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT role, content, timestamp FROM conversations WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def set_preference(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,),
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return default

    def add_pattern(self, pattern_type: str, data: dict) -> None:
        self._conn.execute(
            "INSERT INTO patterns (type, data, learned_at) VALUES (?, ?, ?)",
            (pattern_type, json.dumps(data), datetime.now().isoformat()),
        )
        self._conn.commit()

    def get_patterns(self, pattern_type: Optional[str] = None, limit: int = 50) -> list[dict]:
        if pattern_type:
            rows = self._conn.execute(
                "SELECT type, data, learned_at FROM patterns WHERE type = ? ORDER BY id DESC LIMIT ?",
                (pattern_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT type, data, learned_at FROM patterns ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"type": r["type"], "data": json.loads(r["data"]), "learned_at": r["learned_at"]}
                for r in rows]

    def add_reminder(self, message: str, time: str) -> int:
        cursor = self._conn.execute(
            "INSERT INTO reminders (message, time, created_at) VALUES (?, ?, ?)",
            (message, time, datetime.now().isoformat()),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_pending_reminders(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, message, time FROM reminders WHERE triggered = 0 AND time <= ?",
            (datetime.now().isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_reminder_done(self, reminder_id: int) -> None:
        self._conn.execute("UPDATE reminders SET triggered = 1 WHERE id = ?", (reminder_id,))
        self._conn.commit()

    def get_stats(self) -> dict:
        convos = self._conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
        prefs = self._conn.execute("SELECT COUNT(*) as c FROM preferences").fetchone()["c"]
        patterns = self._conn.execute("SELECT COUNT(*) as c FROM patterns").fetchone()["c"]
        reminders = self._conn.execute("SELECT COUNT(*) as c FROM reminders WHERE triggered=0").fetchone()["c"]
        return {"conversations": convos, "preferences": prefs,
                "patterns": patterns, "pending_reminders": reminders}

    def close(self) -> None:
        self._conn.close()
