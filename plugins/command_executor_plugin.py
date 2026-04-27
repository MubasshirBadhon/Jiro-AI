"""Command Executor Plugin - Run system commands (cmd/powershell).

Gives Jiro kernel-level access to run CLI commands on the system.
"""

import asyncio
import logging
import platform
import subprocess

logger = logging.getLogger("jiro.plugins.command_executor")

PLUGIN_NAME = "command_executor"
PLUGIN_DESCRIPTION = "Execute system commands (cmd, powershell, bash)"
PLUGIN_COMMANDS = [
    "run command", "execute", "run cmd", "powershell", "cmd",
    "terminal", "shell", "run shell", "system command",
]

# Commands that should never be executed for safety
BLOCKED_COMMANDS = [
    "format", "del /s", "rm -rf /", "shutdown", "restart",
    ":(){:|:&};:", "mkfs", "dd if=",
]


async def handle(command: str, context: dict = None) -> str:
    """Execute a system command and return the output."""
    lower = command.lower()
    for prefix in PLUGIN_COMMANDS:
        if lower.startswith(prefix):
            cmd = command[len(prefix):].strip()
            break
    else:
        cmd = command

    if not cmd:
        return "Please specify a command. Example: 'run command dir' or 'powershell Get-Process'"

    # Safety check
    cmd_lower = cmd.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return f"Command blocked for safety: contains '{blocked}'"

    is_windows = platform.system() == "Windows"

    try:
        if is_windows:
            # Determine if powershell or cmd
            if cmd_lower.startswith("powershell "):
                cmd = cmd[len("powershell "):].strip()
                proc = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    "cmd", "/c", cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
        else:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        output = stdout.decode(errors='replace').strip()
        errors = stderr.decode(errors='replace').strip()

        result = []
        if output:
            result.append(f"Output:\n{output}")
        if errors:
            result.append(f"Errors:\n{errors}")
        if proc.returncode != 0:
            result.append(f"Exit code: {proc.returncode}")

        if not result:
            return "Command executed successfully (no output)."
        return "\n".join(result)

    except asyncio.TimeoutError:
        return "Command timed out after 30 seconds."
    except Exception as e:
        logger.error("Command execution failed: %s", e)
        return f"Failed to execute command: {e}"
