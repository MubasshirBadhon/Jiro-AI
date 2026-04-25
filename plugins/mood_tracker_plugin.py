"""Mood Tracker Plugin - Track daily mood and emotions."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import datetime, date
from pathlib import Path

MOOD_FILE = Path(__file__).parent.parent / "data" / "memory" / "mood.json"

MOODS = {"happy": 5, "great": 5, "good": 4, "okay": 3, "ok": 3, "fine": 3,
         "meh": 2, "tired": 2, "sad": 1, "bad": 1, "terrible": 0, "stressed": 1,
         "anxious": 1, "excited": 5, "bored": 2, "angry": 1, "calm": 4, "motivated": 5}


class MoodTrackerPlugin(PluginBase):
    name = "mood_tracker"
    description = "Track daily mood and emotional patterns"
    triggers = ["mood", "feeling", "how am i feeling", "i feel", "emotional",
                 "log mood", "my mood"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if MOOD_FILE.exists():
            try: return json.loads(MOOD_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"entries": []}

    def _save(self):
        MOOD_FILE.parent.mkdir(parents=True, exist_ok=True)
        MOOD_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        for mood, score in MOODS.items():
            if mood in lower:
                self._data["entries"].append({
                    "mood": mood, "score": score,
                    "date": datetime.now().isoformat(),
                })
                self._save()
                if score >= 4:
                    return f"Glad you're feeling {mood}! Keep up the positive vibes!"
                elif score >= 2:
                    return f"Noted: feeling {mood}. Remember, every day is a new opportunity!"
                else:
                    return f"Sorry you're feeling {mood}. Take a break, go for a walk, or talk to someone you trust."

        if any(w in lower for w in ["stats", "history", "pattern"]):
            if not self._data["entries"]:
                return "No mood data yet. Tell me how you feel: 'I feel happy'"
            recent = self._data["entries"][-7:]
            avg = sum(e["score"] for e in recent) / len(recent)
            moods = [e["mood"] for e in recent]
            return f"Mood (last {len(recent)} entries): avg {avg:.1f}/5\n  Recent: {', '.join(moods)}"

        return "How are you feeling? Say: 'I feel happy/tired/stressed/excited'"
