"""Auto Updater - Pull latest code from GitHub automatically.

Checks the Jiro AI GitHub repo for updates and applies them.
Can run on startup or be triggered manually.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jiro.updater")

PROJECT_ROOT = Path(__file__).parent.parent
REPO_URL = "https://github.com/MubasshirBadhon/Jiro-AI.git"


class AutoUpdater:
    """Handles automatic updates from GitHub."""

    def __init__(self, config: dict):
        self._config = config
        self._repo_url = config.get("update", {}).get("repo_url", REPO_URL)
        self._auto_update = config.get("update", {}).get("auto_update", True)
        self._branch = config.get("update", {}).get("branch", "main")

    def check_for_updates(self) -> dict:
        """Check if there are new updates available."""
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
        """Pull latest changes from GitHub."""
        try:
            is_git = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
            )
            if is_git.returncode != 0:
                return self._clone_fresh()

            stash = subprocess.run(
                ["git", "stash"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
            )

            pull = subprocess.run(
                ["git", "pull", "origin", self._branch, "--rebase"],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=60,
            )

            if stash.stdout and "No local changes" not in stash.stdout:
                subprocess.run(
                    ["git", "stash", "pop"],
                    cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10,
                )

            if pull.returncode == 0:
                self._install_deps()
                logger.info("Jiro AI updated successfully!")
                return {"success": True, "message": "Updated to latest version!"}
            else:
                return {"success": False, "message": f"Update failed: {pull.stderr[:200]}"}

        except FileNotFoundError:
            return {"success": False, "message": "git not installed"}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Update timed out"}
        except Exception as e:
            return {"success": False, "message": str(e)}

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
                import shutil
                temp = PROJECT_ROOT / "_update_temp"
                for item in temp.iterdir():
                    if item.name == ".git":
                        continue
                    dest = PROJECT_ROOT / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
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
                return {"success": True, "message": "Fresh install from GitHub complete!"}

            return {"success": False, "message": f"Clone failed: {result.stderr[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

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

    def auto_update_on_start(self) -> Optional[str]:
        """Run auto-update on startup if enabled."""
        if not self._auto_update:
            return None

        check = self.check_for_updates()
        if check.get("available"):
            logger.info("Updates available (%d commits). Updating...", check.get("commits", 0))
            result = self.update()
            if result["success"]:
                return f"Jiro updated! ({check.get('commits', 0)} new changes)"
            else:
                logger.warning("Auto-update failed: %s", result["message"])
        return None
