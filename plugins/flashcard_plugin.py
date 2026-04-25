"""Flashcard Plugin - Create and review flashcards for studying."""

from plugins.plugin_loader import PluginBase
import json
import random
import re
from datetime import datetime
from pathlib import Path

CARDS_FILE = Path(__file__).parent.parent / "data" / "memory" / "flashcards.json"


class FlashcardPlugin(PluginBase):
    name = "flashcard"
    description = "Create, review, and manage study flashcards"
    triggers = ["flashcard", "flash card", "study card", "quiz me", "review cards",
                 "add card", "create card"]

    def __init__(self):
        self._cards = self._load()

    def _load(self) -> dict:
        if CARDS_FILE.exists():
            try:
                return json.loads(CARDS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"decks": {"general": []}}

    def _save(self) -> None:
        CARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CARDS_FILE.write_text(json.dumps(self._cards, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Add card
        add_match = re.search(r'(?:add|create)\s*(?:flash)?card[:\s]+(.+?)\s*[|/]\s*(.+)', command, re.IGNORECASE)
        if add_match:
            q, a = add_match.group(1).strip(), add_match.group(2).strip()
            deck = "general"
            deck_match = re.search(r'(?:to|in|deck)\s+(\w+)', lower)
            if deck_match:
                deck = deck_match.group(1)
            self._cards["decks"].setdefault(deck, []).append({
                "question": q, "answer": a,
                "created": datetime.now().isoformat(),
                "correct": 0, "incorrect": 0,
            })
            self._save()
            return f"Flashcard added to '{deck}' deck!\n  Q: {q}\n  A: {a}"

        # Review/quiz
        if any(w in lower for w in ["quiz", "review", "test"]):
            deck = "general"
            deck_match = re.search(r'(?:quiz|review|test)\s+(\w+)', lower)
            if deck_match and deck_match.group(1) not in ("me", "cards"):
                deck = deck_match.group(1)

            cards = self._cards["decks"].get(deck, [])
            if not cards:
                return f"No cards in '{deck}' deck. Add with: 'add card: question | answer'"

            card = random.choice(cards)
            return f"FLASHCARD ({deck}):\n\n  Q: {card['question']}\n\n  (Say 'answer' to see the answer)"

        # Show answer
        if lower in ("answer", "show answer", "reveal"):
            for deck_name, cards in self._cards["decks"].items():
                if cards:
                    card = cards[-1]
                    return f"  A: {card['answer']}"
            return "No card to show answer for"

        # List decks
        if "list" in lower or "decks" in lower:
            if not self._cards["decks"]:
                return "No flashcard decks"
            result = "Flashcard Decks:\n"
            for name, cards in self._cards["decks"].items():
                result += f"  {name}: {len(cards)} cards\n"
            return result

        # Stats
        if "stats" in lower:
            total = sum(len(c) for c in self._cards["decks"].values())
            return f"Flashcard stats: {total} cards across {len(self._cards['decks'])} decks"

        return ("Flashcard commands:\n"
                "  'add card: question | answer'\n"
                "  'quiz me' - random card\n"
                "  'list decks' - show all decks\n"
                "  Format: 'add card: What is H2O? | Water'")
