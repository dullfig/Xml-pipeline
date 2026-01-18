"""
Console client that connects to the agent server.

Provides SSH-style login with username/password authentication.
"""

from __future__ import annotations

import asyncio
import getpass
import json
import sys
from typing import Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_LOGIN_ATTEMPTS = 3


class ConsoleClient:
    """
    Text-based console client for the agent server.

    Usage:
        client = ConsoleClient()
        asyncio.run(client.run())
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.running = False

    async def login(self) -> bool:
        """
        Perform SSH-style login.

        Returns:
            True if login successful, False otherwise
        """
        print(f"Connecting to {self.host}:{self.port}...")

        for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
            try:
                username = input("Username: ")
                password = getpass.getpass("Password: ")
            except (EOFError, KeyboardInterrupt):
                print("\nLogin cancelled.")
                return False

            if not username or not password:
                print("Username and password required.")
                continue

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/auth/login",
                        json={"username": username, "password": password},
                    ) as resp:
                        data = await resp.json()

                        if resp.status == 200:
                            self.token = data["token"]
                            self.username = username
                            print(f"Welcome, {username}!")
                            return True
                        else:
                            error = data.get("error", "Authentication failed")
                            remaining = MAX_LOGIN_ATTEMPTS - attempt
                            if remaining > 0:
                                print(f"{error}. {remaining} attempt(s) remaining.")
                            else:
                                print(f"{error}. No attempts remaining.")
            except aiohttp.ClientError as e:
                print(f"Connection error: {e}")
                return False

        return False

    async def connect_ws(self) -> bool:
        """Connect to WebSocket after authentication."""
        if not self.token:
            return False

        try:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.token}"}
            )
            self.ws = await self.session.ws_connect(self.ws_url)

            # Wait for connected message
            msg = await self.ws.receive_json()
            if msg.get("type") == "connected":
                return True
            return False
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            return False

    async def send_command(self, cmd: str) -> Optional[dict]:
        """Send a command via WebSocket and get response."""
        if not self.ws:
            return None

        await self.ws.send_json(cmd)
        return await self.ws.receive_json()

    def print_help(self):
        """Print available commands."""
        print("""
Available commands:
  /help       - Show this help
  /status     - Show server status
  /listeners  - List available targets
  /targets    - Alias for /listeners
  /quit       - Disconnect and exit

Send messages:
  @target message   - Send message to a target listener
                      Example: @greeter Hello there!
""")

    async def handle_command(self, line: str) -> bool:
        """
        Handle a command line.

        Returns:
            False if should quit, True otherwise
        """
        line = line.strip()
        if not line:
            return True

        if line == "/help":
            self.print_help()
        elif line == "/quit" or line == "/exit":
            return False
        elif line == "/status":
            resp = await self.send_command({"type": "status"})
            if resp:
                threads = resp.get("threads", 0)
                print(f"Active threads: {threads}")
        elif line == "/listeners" or line == "/targets":
            resp = await self.send_command({"type": "listeners"})
            if resp:
                listeners = resp.get("listeners", [])
                if listeners:
                    print("Available targets:")
                    for name in listeners:
                        print(f"  - {name}")
                else:
                    print("No targets available (pipeline not running)")
        elif line.startswith("/"):
            print(f"Unknown command: {line}")
        elif line.startswith("@"):
            # Send message to target: @target message
            resp = await self.send_command({"type": "send", "raw": line})
            if resp:
                if resp.get("type") == "sent":
                    thread_id = resp.get("thread_id", "")[:8]
                    target = resp.get("target", "unknown")
                    print(f"Sent to {target} (thread: {thread_id}...)")
                elif resp.get("type") == "error":
                    print(f"Error: {resp.get('error')}")
        else:
            print("Use @target message to send. Example: @greeter Hello!")
            print("Type /listeners to see available targets.")

        return True

    async def run(self):
        """Main client loop."""
        if not AIOHTTP_AVAILABLE:
            print("Error: aiohttp not installed")
            sys.exit(1)

        # Login
        if not await self.login():
            print("Authentication failed.")
            sys.exit(1)

        # Connect WebSocket
        if not await self.connect_ws():
            print("Failed to connect to server.")
            sys.exit(1)

        print("Connected. Type /help for commands, /quit to exit.")

        self.running = True

        try:
            if PROMPT_TOOLKIT_AVAILABLE:
                await self._run_prompt_toolkit()
            else:
                await self._run_simple()
        finally:
            await self.cleanup()

    async def _run_prompt_toolkit(self):
        """Run with prompt_toolkit for better UX."""
        style = Style.from_dict({
            "prompt": "ansicyan bold",
        })

        session = PromptSession(
            history=InMemoryHistory(),
            style=style,
        )

        while self.running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: session.prompt(f"{self.username}> ")
                )
                if not await self.handle_command(line):
                    break
            except (EOFError, KeyboardInterrupt):
                break

    async def _run_simple(self):
        """Run with simple input (fallback)."""
        while self.running:
            try:
                line = input(f"{self.username}> ")
                if not await self.handle_command(line):
                    break
            except (EOFError, KeyboardInterrupt):
                break

    async def cleanup(self):
        """Clean up connections."""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
        print("Disconnected.")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="XML Pipeline Console")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    args = parser.parse_args()

    client = ConsoleClient(host=args.host, port=args.port)
    asyncio.run(client.run())


if __name__ == "__main__":
    main()
