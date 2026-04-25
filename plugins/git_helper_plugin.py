"""Git Helper Plugin - Common git commands reference."""

from plugins.plugin_loader import PluginBase


class GitHelperPlugin(PluginBase):
    name = "git_helper"
    description = "Git commands reference and help"
    triggers = ["git", "commit", "push", "pull", "branch", "merge",
                 "git help", "how to git"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if "commit" in lower:
            return ("Git Commit:\n"
                    "  git add .                    # Stage all changes\n"
                    "  git add <file>               # Stage specific file\n"
                    "  git commit -m \"message\"      # Commit with message\n"
                    "  git commit -am \"message\"     # Add + commit tracked files")

        if "branch" in lower:
            return ("Git Branches:\n"
                    "  git branch                   # List branches\n"
                    "  git branch <name>            # Create branch\n"
                    "  git checkout <name>          # Switch branch\n"
                    "  git checkout -b <name>       # Create + switch\n"
                    "  git branch -d <name>         # Delete branch")

        if "push" in lower or "pull" in lower:
            return ("Git Remote:\n"
                    "  git push origin <branch>     # Push to remote\n"
                    "  git pull origin <branch>     # Pull from remote\n"
                    "  git fetch                    # Fetch without merge\n"
                    "  git remote -v                # Show remotes")

        if "merge" in lower:
            return ("Git Merge:\n"
                    "  git merge <branch>           # Merge branch\n"
                    "  git merge --abort            # Abort merge\n"
                    "  git rebase <branch>          # Rebase onto branch")

        if "undo" in lower or "reset" in lower:
            return ("Git Undo:\n"
                    "  git checkout -- <file>       # Discard file changes\n"
                    "  git reset HEAD <file>        # Unstage file\n"
                    "  git reset --soft HEAD~1      # Undo last commit (keep changes)\n"
                    "  git stash                    # Stash changes\n"
                    "  git stash pop                # Apply stashed changes")

        return ("Git Quick Reference:\n"
                "  git init                     # Initialize repo\n"
                "  git clone <url>              # Clone repo\n"
                "  git status                   # Check status\n"
                "  git log --oneline            # View history\n"
                "  git diff                     # View changes\n\n"
                "  Say 'git commit', 'git branch', 'git push', 'git merge' for more")
