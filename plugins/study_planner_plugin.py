"""Study Planner Plugin - Plan study sessions, track subjects, manage exams."""

from plugins.plugin_loader import PluginBase
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

PLAN_FILE = Path(__file__).parent.parent / "data" / "memory" / "study_plan.json"


class StudyPlannerPlugin(PluginBase):
    name = "study_planner"
    description = "Plan study sessions, track subjects, manage exam schedule"
    triggers = ["study plan", "study session", "exam", "test date", "subject",
                 "study schedule", "revision", "syllabus", "study time"]

    def __init__(self):
        self._data = self._load()

    def _load(self) -> dict:
        if PLAN_FILE.exists():
            try:
                return json.loads(PLAN_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"subjects": [], "exams": [], "sessions": []}

    def _save(self) -> None:
        PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
        PLAN_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Add exam
        exam_match = re.search(r'(?:exam|test)\s+(.+?)\s+(?:on|at|date)\s+(.+)', lower)
        if exam_match:
            subject = exam_match.group(1).strip()
            date = exam_match.group(2).strip()
            self._data["exams"].append({
                "subject": subject, "date": date,
                "added": datetime.now().isoformat(),
            })
            self._save()
            return f"Exam added: {subject} on {date}"

        # Add subject
        subj_match = re.search(r'(?:add|new)\s+subject[:\s]+(.+)', lower)
        if subj_match:
            subject = subj_match.group(1).strip()
            self._data["subjects"].append({
                "name": subject,
                "total_hours": 0,
                "added": datetime.now().isoformat(),
            })
            self._save()
            return f"Subject added: {subject}"

        # Log study session
        sess_match = re.search(r'(?:studied|study)\s+(.+?)\s+(?:for\s+)?(\d+)\s*(hour|hr|minute|min)', lower)
        if sess_match:
            subject = sess_match.group(1).strip()
            amount = int(sess_match.group(2))
            unit = sess_match.group(3)
            hours = amount if "hour" in unit or "hr" in unit else amount / 60
            self._data["sessions"].append({
                "subject": subject, "hours": hours,
                "date": datetime.now().isoformat(),
            })
            for s in self._data["subjects"]:
                if s["name"].lower() == subject:
                    s["total_hours"] += hours
            self._save()
            return f"Logged: {hours:.1f} hours studying {subject}. Keep it up!"

        # Show plan
        if any(w in lower for w in ["show", "list", "my plan", "overview"]):
            result = "Study Plan:\n"
            if self._data["subjects"]:
                result += "\nSubjects:\n"
                for s in self._data["subjects"]:
                    result += f"  - {s['name']} ({s.get('total_hours', 0):.1f} hrs total)\n"
            if self._data["exams"]:
                result += "\nUpcoming Exams:\n"
                for e in self._data["exams"]:
                    result += f"  - {e['subject']}: {e['date']}\n"
            if not self._data["subjects"] and not self._data["exams"]:
                result = "No study plan yet. Add subjects and exams to get started!"
            return result

        # Suggest study plan
        if "suggest" in lower or "plan" in lower:
            exams = self._data.get("exams", [])
            if not exams:
                return "Add your exams first: 'exam Physics on December 15'"
            result = "Suggested study plan:\n"
            for e in exams:
                result += f"  {e['subject']}: Study 1-2 hours daily until {e['date']}\n"
            return result

        return ("Study Planner commands:\n"
                "  'add subject: Physics'\n"
                "  'exam Physics on December 15'\n"
                "  'studied Physics for 2 hours'\n"
                "  'show study plan'\n"
                "  'suggest study plan'")
