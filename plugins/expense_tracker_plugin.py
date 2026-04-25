"""Expense Tracker Plugin - Track daily expenses and budgets."""

from plugins.plugin_loader import PluginBase
import json
import re
from datetime import datetime, date
from pathlib import Path

EXPENSE_FILE = Path(__file__).parent.parent / "data" / "memory" / "expenses.json"


class ExpenseTrackerPlugin(PluginBase):
    name = "expense_tracker"
    description = "Track daily expenses, set budgets, view spending"
    triggers = ["expense", "spent", "budget", "money", "cost", "taka",
                 "how much spent", "spending", "add expense"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if EXPENSE_FILE.exists():
            try:
                return json.loads(EXPENSE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"expenses": [], "budget": {"daily": 0, "monthly": 0}}

    def _save(self):
        EXPENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        EXPENSE_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Add expense
        exp_match = re.search(r'(?:spent|expense|cost|paid)\s+(\d+(?:\.\d+)?)\s*(?:taka|tk|bdt|usd|\$)?\s*(?:on|for)?\s*(.*)', lower)
        if exp_match:
            amount = float(exp_match.group(1))
            category = exp_match.group(2).strip() or "general"
            self._data["expenses"].append({
                "amount": amount, "category": category,
                "date": datetime.now().isoformat(),
            })
            self._save()
            today_total = sum(e["amount"] for e in self._data["expenses"]
                            if e["date"].startswith(date.today().isoformat()))
            return f"Recorded: {amount} on {category}. Today's total: {today_total:.0f}"

        # Set budget
        budget_match = re.search(r'budget\s+(\d+)\s*(?:taka|tk|bdt)?\s*(?:per\s+)?(daily|monthly|day|month)', lower)
        if budget_match:
            amount = float(budget_match.group(1))
            period = "daily" if "day" in budget_match.group(2) else "monthly"
            self._data["budget"][period] = amount
            self._save()
            return f"{period.title()} budget set: {amount}"

        # Show summary
        if any(w in lower for w in ["summary", "report", "how much", "show", "today"]):
            today = date.today().isoformat()
            today_expenses = [e for e in self._data["expenses"] if e["date"].startswith(today)]
            today_total = sum(e["amount"] for e in today_expenses)

            month = datetime.now().strftime("%Y-%m")
            month_expenses = [e for e in self._data["expenses"] if e["date"].startswith(month)]
            month_total = sum(e["amount"] for e in month_expenses)

            result = f"Expense Summary:\n  Today: {today_total:.0f}\n  This month: {month_total:.0f}\n"
            if self._data["budget"]["daily"]:
                remaining = self._data["budget"]["daily"] - today_total
                result += f"  Daily budget remaining: {remaining:.0f}\n"
            if today_expenses:
                result += "\nToday's expenses:\n"
                for e in today_expenses:
                    result += f"  {e['amount']:.0f} - {e['category']}\n"
            return result

        return ("Expense Tracker:\n"
                "  'spent 50 on food' - add expense\n"
                "  'budget 500 daily' - set budget\n"
                "  'expense summary' - view spending")
