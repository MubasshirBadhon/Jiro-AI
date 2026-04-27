"""Attendance Tracker Plugin - Track class attendance."""

from plugins.plugin_loader import PluginBase
import json, re
from datetime import date
from pathlib import Path

ATT_FILE = Path(__file__).parent.parent / "data" / "memory" / "attendance.json"


class AttendancePlugin(PluginBase):
    name = "attendance"
    description = "Track class attendance percentage"
    triggers = ["attendance", "present", "absent", "my attendance", "class attended",
                 "attended class", "missed class"]

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if ATT_FILE.exists():
            try: return json.loads(ATT_FILE.read_text(encoding="utf-8"))
            except Exception: pass
        return {"subjects": {}}

    def _save(self):
        ATT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ATT_FILE.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Mark present
        present_match = re.search(r'(?:attended|present|went to)\s+(.+?)(?:\s+class)?$', lower)
        if present_match:
            subject = present_match.group(1).strip().title()
            self._data["subjects"].setdefault(subject, {"present": 0, "total": 0})
            self._data["subjects"][subject]["present"] += 1
            self._data["subjects"][subject]["total"] += 1
            self._save()
            s = self._data["subjects"][subject]
            pct = (s["present"] / s["total"]) * 100
            return f"Marked present for {subject}. Attendance: {pct:.0f}% ({s['present']}/{s['total']})"

        # Mark absent
        absent_match = re.search(r'(?:missed|absent|skipped)\s+(.+?)(?:\s+class)?$', lower)
        if absent_match:
            subject = absent_match.group(1).strip().title()
            self._data["subjects"].setdefault(subject, {"present": 0, "total": 0})
            self._data["subjects"][subject]["total"] += 1
            self._save()
            s = self._data["subjects"][subject]
            pct = (s["present"] / s["total"]) * 100 if s["total"] > 0 else 0
            return f"Marked absent for {subject}. Attendance: {pct:.0f}% ({s['present']}/{s['total']})"

        # Show attendance
        if not self._data["subjects"]:
            return "No attendance data. Mark with: 'attended Physics' or 'missed Math'"
        result = "Attendance Report:\n"
        for subj, s in self._data["subjects"].items():
            pct = (s["present"] / s["total"]) * 100 if s["total"] > 0 else 0
            warning = " (LOW!)" if pct < 75 else ""
            result += f"  {subj}: {pct:.0f}% ({s['present']}/{s['total']}){warning}\n"
        return result
