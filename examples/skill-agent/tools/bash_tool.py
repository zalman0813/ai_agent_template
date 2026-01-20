"""Bash execution tool with safety checks."""

import subprocess
import shlex
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


# Commands that are blocked for safety
BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){:|:&};:",  # fork bomb
}

# Only allow these command prefixes for safety
ALLOWED_PREFIXES = [
    "python",
    "python3",
    "cat",
    "head",
    "tail",
    "ls",
    "pwd",
    "echo",
    "grep",
    "wc",
]


def is_safe_command(command: str) -> tuple[bool, str]:
    """Check if a command is safe to execute.

    Args:
        command: The command to check.

    Returns:
        Tuple of (is_safe, reason).
    """
    command_lower = command.lower().strip()

    # Check blocked commands
    for blocked in BLOCKED_COMMANDS:
        if blocked in command_lower:
            return False, f"Blocked command pattern detected: {blocked}"

    # Check allowed prefixes
    first_word = command.split()[0] if command.split() else ""
    if not any(first_word.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return False, f"Command not in allowed list. Allowed: {ALLOWED_PREFIXES}"

    return True, "OK"


@tool
def bash_tool(command: str, timeout: int = 30) -> str:
    """Execute a bash command for skill scripts.

    This tool executes shell commands with safety restrictions.
    Only certain commands are allowed (python, cat, ls, etc.).

    Args:
        command: The bash command to execute.
        timeout: Maximum execution time in seconds (default: 30).

    Returns:
        Command output (stdout + stderr) or error message.
    """
    # Safety check
    is_safe, reason = is_safe_command(command)
    if not is_safe:
        return f"Error: Command blocked - {reason}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent,  # Run from project root
        )

        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(f"[stderr]\n{result.stderr}")
        if result.returncode != 0:
            output_parts.append(f"[exit code: {result.returncode}]")

        return "\n".join(output_parts) if output_parts else "(no output)"

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"
