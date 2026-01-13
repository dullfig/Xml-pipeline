"""
Shell tool - sandboxed command execution.
"""

from typing import Optional
from .base import tool, ToolResult


# TODO: Configure command restrictions
ALLOWED_COMMANDS: list = []  # Empty = allow all (dangerous!)
BLOCKED_COMMANDS: list = ["rm", "del", "format", "mkfs", "dd"]


@tool
async def run_command(
    command: str,
    timeout: int = 30,
    cwd: Optional[str] = None,
) -> ToolResult:
    """
    Execute a shell command (sandboxed).

    Args:
        command: Command to execute
        timeout: Timeout in seconds (default: 30)
        cwd: Working directory

    Returns:
        exit_code, stdout, stderr

    Security:
        - Command allowlist (or blocklist dangerous commands)
        - No shell expansion by default
        - Resource limits (CPU, memory)
        - Chroot to safe directory
        - Timeout enforced
    """
    # TODO: Implement with asyncio.subprocess
    # import asyncio
    # try:
    #     proc = await asyncio.create_subprocess_shell(
    #         command,
    #         stdout=asyncio.subprocess.PIPE,
    #         stderr=asyncio.subprocess.PIPE,
    #         cwd=cwd,
    #     )
    #     try:
    #         stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    #     except asyncio.TimeoutError:
    #         proc.kill()
    #         return ToolResult(success=False, error=f"Command timed out after {timeout}s")
    #
    #     return ToolResult(success=True, data={
    #         "exit_code": proc.returncode,
    #         "stdout": stdout.decode(),
    #         "stderr": stderr.decode(),
    #     })
    # except Exception as e:
    #     return ToolResult(success=False, error=str(e))

    return ToolResult(success=False, error="Not implemented")
