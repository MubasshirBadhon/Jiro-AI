"""Integrity Checker - Detects if any Jiro AI files were tampered with.

Computes checksums of all source files and alerts if any have
been modified outside of Jiro's own update process.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.security.integrity")

PROJECT_ROOT = Path(__file__).parent.parent
CHECKSUMS_FILE = PROJECT_ROOT / "data" / "memory" / "file_checksums.json"


class IntegrityChecker:
    """Checks file integrity to detect tampering."""

    def __init__(self):
        self._checksums: dict = {}
        self._load()

    def _load(self) -> None:
        if CHECKSUMS_FILE.exists():
            try:
                with open(CHECKSUMS_FILE, "r") as f:
                    self._checksums = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self) -> None:
        CHECKSUMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CHECKSUMS_FILE, "w") as f:
            json.dump(self._checksums, f, indent=2)

    def _hash_file(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def compute_checksums(self) -> dict:
        """Compute checksums for all Python files."""
        checksums = {}
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            rel = str(py_file.relative_to(PROJECT_ROOT))
            checksums[rel] = self._hash_file(py_file)
        return checksums

    def save_baseline(self) -> None:
        """Save current file checksums as the baseline."""
        self._checksums = self.compute_checksums()
        self._save()
        logger.info("Baseline checksums saved (%d files)", len(self._checksums))

    def check(self) -> dict:
        """Check all files against baseline checksums."""
        if not self._checksums:
            return {"status": "no_baseline", "message": "No baseline. Run save_baseline() first."}

        current = self.compute_checksums()
        modified = []
        deleted = []
        new_files = []

        for path, checksum in self._checksums.items():
            if path not in current:
                deleted.append(path)
            elif current[path] != checksum:
                modified.append(path)

        for path in current:
            if path not in self._checksums:
                new_files.append(path)

        ok = not modified and not deleted
        return {
            "status": "ok" if ok else "tampered",
            "modified": modified,
            "deleted": deleted,
            "new_files": new_files,
        }

    def format_report(self, result: dict) -> str:
        lines = ["File Integrity Check:"]
        if result["status"] == "ok":
            lines.append("  All files intact.")
        elif result["status"] == "no_baseline":
            lines.append("  No baseline checksums found.")
        else:
            if result.get("modified"):
                lines.append("  MODIFIED files:")
                for f in result["modified"]:
                    lines.append(f"    ! {f}")
            if result.get("deleted"):
                lines.append("  DELETED files:")
                for f in result["deleted"]:
                    lines.append(f"    - {f}")
            if result.get("new_files"):
                lines.append("  NEW files:")
                for f in result["new_files"]:
                    lines.append(f"    + {f}")
        return "\n".join(lines)
