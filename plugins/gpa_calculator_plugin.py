"""GPA Calculator Plugin - Calculate GPA/CGPA from grades."""

from plugins.plugin_loader import PluginBase
import re


GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F": 0.0,
}


class GPACalculatorPlugin(PluginBase):
    name = "gpa_calculator"
    description = "Calculate GPA/CGPA from letter grades or marks"
    triggers = ["gpa", "cgpa", "grade point", "calculate gpa", "my grades"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        # Parse grades: "A+, B, A-, C+"
        grades = re.findall(r'\b([A-Da-d][+-]?|[Ff])\b', command)
        if grades:
            points = [GRADE_POINTS.get(g.upper(), 0) for g in grades]
            gpa = sum(points) / len(points)
            grade_list = ", ".join(f"{g.upper()}({GRADE_POINTS.get(g.upper(), 0)})" for g in grades)
            return f"Grades: {grade_list}\nGPA: {gpa:.2f}/4.0"

        # Parse marks: "85, 72, 90, 65"
        marks = re.findall(r'\b(\d{1,3})\b', command)
        marks = [int(m) for m in marks if 0 <= int(m) <= 100]
        if marks:
            avg = sum(marks) / len(marks)
            if avg >= 90: letter = "A+"
            elif avg >= 85: letter = "A"
            elif avg >= 80: letter = "A-"
            elif avg >= 75: letter = "B+"
            elif avg >= 70: letter = "B"
            elif avg >= 65: letter = "B-"
            elif avg >= 60: letter = "C+"
            elif avg >= 55: letter = "C"
            elif avg >= 50: letter = "D"
            else: letter = "F"
            gpa = GRADE_POINTS[letter]
            return f"Average: {avg:.1f}% → Grade: {letter} → GPA: {gpa:.1f}/4.0"

        return ("GPA Calculator:\n"
                "  Enter grades: 'gpa A+, B, A-, C+'\n"
                "  Enter marks: 'gpa 85, 72, 90, 65'\n"
                "  Grade scale: A+(4.0) to F(0.0)")
