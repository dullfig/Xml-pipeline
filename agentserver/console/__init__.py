"""
console — Console interfaces for xml-pipeline.

Provides:
- SecureConsole: Local keyboard-only console (no network)
- ConsoleClient: Network client connecting to server with auth
"""

from agentserver.console.secure_console import SecureConsole, PasswordManager
from agentserver.console.client import ConsoleClient

__all__ = ["SecureConsole", "PasswordManager", "ConsoleClient"]
