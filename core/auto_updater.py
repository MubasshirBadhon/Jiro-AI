"""Auto Updater - Pull latest code from GitHub on every startup.

Runs automatically when Jiro starts:
1. Check for updates from GitHub
2. If updates available: git pull + pip install
3. Restart Jiro with new code

Also handles auto-start registration on Windows.
"""

import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.updater")

PROJECT_ROOT = Path(__file__).parent.parent
REPO_URL = "https://github.com/MubasshirBadhon/Jiro-AI.git"


class AutoUpdater:
    """Auto-update from GitHub on every startup."""

    def __init__(self, config: dict):
        self._config = config
        self._repo_url = config.get("update", {}).get("repo_url", REPO_URL)
        self._auto_update = config.get("update", {}).get("auto_update", True)
        self._branch = config.get("update", {}).get("branch", "main")

    def check_for_updates(self) -> dict:
        """Check if there are new commits on the remote."""
        try:
            result = subprocess.run(
                ["git", "fetch", "origin", self._branch],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return {"available": False, "error": result.stderr.strip()}

            result = subprocess.run(
                ["git", "log", f"HEAD..origin/{self._branch}", "--oneline"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
            )
            commits = result.stdout.strip().split("\n") if result.stdout.strip() else []
            return {
                "available": len(commits) > 0,
                "commits": len(commits),
                "details": commits[:10],
            }
        except FileNotFoundError:
            return {"available": False, "error": "git not installed"}
        except subprocess.TimeoutExpired:
            return {"available": False, "error": "Timeout checking for updates"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def update(self) -> dict:
        """Pull latest changes and install dependencies."""
        try:
            is_git = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
            )
            if is_git.returncode != 0:
                return self._clone_fresh()

            # Stash local changes
            stash = subprocess.run(
                ["git", "stash"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
            )

            # Pull latest
            pull = subprocess.run(
                ["git", "pull", "origin", self._branch, "--rebase"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=60,
            )

            # Restore stashed changes
            if stash.stdout and "No local changes" not in stash.stdout:
                subprocess.run(
                    ["git", "stash", "pop"],
                    cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
                )

            if pull.returncode == 0:
                self._install_deps()
                return {"success": True, "updated": True,
                        "message": "Updated to latest version!"}
            else:
                return {"success": False, "updated": False,
                        "message": f"Update failed: {pull.stderr[:200]}"}

        except FileNotFoundError:
            return {"success": False, "updated": False, "message": "git not installed"}
        except subprocess.TimeoutExpired:
            return {"success": False, "updated": False, "message": "Update timed out"}
        except Exception as e:
            return {"success": False, "updated": False, "message": str(e)}

    def _clone_fresh(self) -> dict:
        """Clone the repo fresh if not a git directory."""
        try:
            import shutil
            backup = PROJECT_ROOT.parent / "jiro_backup"
            if backup.exists():
                shutil.rmtree(backup)

            important = ["config.json", "permissions.json", "data"]
            for item in important:
                src = PROJECT_ROOT / item
                dst = backup / item
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)

            result = subprocess.run(
                ["git", "clone", self._repo_url, str(PROJECT_ROOT / "_update_temp")],
                capture_output=True, text=True, timeout=120,
            )

            if result.returncode == 0:
                temp = PROJECT_ROOT / "_update_temp"
                for f in temp.iterdir():
                    if f.name == ".git":
                        continue
                    dest = PROJECT_ROOT / f.name
                    if f.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(f, dest)
                    else:
                        shutil.copy2(f, dest)
                shutil.rmtree(temp)

                for item in important:
                    src = backup / item
                    dst = PROJECT_ROOT / item
                    if src.exists() and not dst.exists():
                        if src.is_dir():
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)

                self._install_deps()
                return {"success": True, "updated": True,
                        "message": "Fresh install from GitHub complete!"}

            return {"success": False, "updated": False,
                    "message": f"Clone failed: {result.stderr[:200]}"}
        except Exception as e:
            return {"success": False, "updated": False, "message": str(e)}

    def _install_deps(self) -> None:
        """Install/update dependencies after update."""
        req = PROJECT_ROOT / "requirements.txt"
        if req.exists():
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req), "-q"],
                    cwd=str(PROJECT_ROOT), capture_output=True, timeout=300,
                )
                logger.info("Dependencies updated")
            except Exception as e:
                logger.warning("Dependency update failed: %s", e)

    def auto_update_on_startup(self) -> dict:
        """Run auto-update on every startup. Returns update result."""
        if not self._auto_update:
            return {"updated": False, "message": "Auto-update disabled"}

        logger.info("Checking for updates from %s...", self._repo_url)
        check = self.check_for_updates()

        if check.get("available"):
            count = check.get("commits", 0)
            logger.info("Updates available (%d commits). Updating...", count)
            result = self.update()
            if result.get("updated"):
                logger.info("Updated successfully! %d new changes applied.", count)
                return {"updated": True,
                        "message": f"Updated! {count} new changes applied."}
            else:
                logger.warning("Auto-update failed: %s", result.get("message"))
                return {"updated": False, "message": result.get("message", "")}
        else:
            logger.info("Jiro is up to date.")
            return {"updated": False, "message": "Already up to date"}

    def restart_jiro(self) -> None:
        """Restart Jiro after an update."""
        logger.info("Restarting Jiro AI with updated code...")
        os.execl(sys.executable, sys.executable, *sys.argv)

    def register_autostart(self) -> str:
        """Register Jiro to auto-start when Windows boots."""
        if platform.system() != "Windows":
            return "Auto-start registration is only available on Windows."

        try:
            startup_folder = Path(os.environ.get("APPDATA", "")) / \
                "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

            if not startup_folder.exists():
                return f"Startup folder not found: {startup_folder}"

            bat_content = f'''@echo off
cd /d "{PROJECT_ROOT}"
start /min pythonw main.py
'''
            bat_path = startup_folder / "JiroAI.bat"
            bat_path.write_text(bat_content)
            return f"Auto-start registered: {bat_path}"
        except Exception as e:
            return f"Failed to register auto-start: {e}"
