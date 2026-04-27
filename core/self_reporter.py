"""Self Reporter - Generates reports about missing features, failed tasks, system health.

Jiro makes reports about itself:
- Failed task reports
- Missing feature/plugin reports
- System health reports
- Performance reports
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("jiro.reporter")

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"


class SelfReporter:
    """Generates self-assessment reports."""

    def __init__(self, config: dict):
        self._config = config
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self._failed_tasks: list[dict] = []
        self._missing_features: list[str] = []
        self._errors: list[dict] = []

    def log_failure(self, task: str, error: str) -> None:
        """Log a failed task."""
        self._failed_tasks.append({
            "task": task, "error": error,
            "time": datetime.now().isoformat(),
        })

    def log_missing_feature(self, feature: str) -> None:
        """Log a missing feature request."""
        if feature not in self._missing_features:
            self._missing_features.append(feature)

    def log_error(self, component: str, error: str) -> None:
        """Log a system error."""
        self._errors.append({
            "component": component, "error": error,
            "time": datetime.now().isoformat(),
        })

    def generate_report(self) -> str:
        """Generate a comprehensive self-report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "failed_tasks": self._failed_tasks[-20:],
            "missing_features": self._missing_features,
            "recent_errors": self._errors[-20:],
            "stats": {
                "total_failures": len(self._failed_tasks),
                "total_errors": len(self._errors),
                "missing_features_count": len(self._missing_features),
            },
        }

        # Save to file
        report_file = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.write_text(json.dumps(report, indent=2))
        logger.info("Report saved: %s", report_file)

        # Human-readable summary
        lines = [
            "=== Jiro AI Self-Report ===",
            f"Generated: {report['generated_at']}",
            "",
        ]

        if self._failed_tasks:
            lines.append(f"Failed Tasks ({len(self._failed_tasks)}):")
            for t in self._failed_tasks[-5:]:
                lines.append(f"  - {t['task']}: {t['error']}")
            lines.append("")

        if self._missing_features:
            lines.append(f"Missing Features ({len(self._missing_features)}):")
            for f in self._missing_features:
                lines.append(f"  - {f}")
            lines.append("")

        if self._errors:
            lines.append(f"Recent Errors ({len(self._errors)}):")
            for e in self._errors[-5:]:
                lines.append(f"  - [{e['component']}] {e['error']}")
            lines.append("")

        if not (self._failed_tasks or self._missing_features or self._errors):
            lines.append("All systems operational. No issues to report.")

        return "\n".join(lines)

    def get_summary(self) -> str:
        """Get a quick summary of system status."""
        issues = len(self._failed_tasks) + len(self._errors)
        if issues == 0:
            return "All systems operational, boss."
        return (f"I have {issues} issue(s) to report: "
                f"{len(self._failed_tasks)} failed tasks, "
                f"{len(self._errors)} errors. "
                f"Say 'show report' for details.")
