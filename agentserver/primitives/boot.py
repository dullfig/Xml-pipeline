"""
boot.py — System boot primitive.

The <boot> message is the first message in every organism's lifetime.
It establishes the root thread from which all other threads descend.

The boot handler:
1. Logs organism startup
2. Initializes any system-level state
3. Sends initial ConsolePrompt to start the console REPL

All external messages that arrive without a known thread parent
will be registered as children of the boot thread.
"""

from dataclasses import dataclass
import logging

from third_party.xmlable import xmlify
from agentserver.message_bus.message_state import HandlerMetadata, HandlerResponse

logger = logging.getLogger(__name__)


@xmlify
@dataclass
class Boot:
    """
    System boot message — first message in organism lifetime.

    Injected automatically at startup. Establishes root thread context.
    """
    organism_name: str = ""
    timestamp: str = ""
    listener_count: int = 0


@xmlify
@dataclass
class ConsolePrompt:
    """
    Prompt message to the console.

    Duplicated here to avoid circular import with handlers.console.
    The pump will route based on payload class name.
    """
    output: str = ""
    source: str = ""
    show_banner: bool = False


async def handle_boot(payload: Boot, metadata: HandlerMetadata) -> HandlerResponse:
    """
    Handle the system boot message.

    Logs the boot event and sends initial ConsolePrompt to start the REPL.
    """
    logger.info(
        f"Organism '{payload.organism_name}' booted at {payload.timestamp} "
        f"with {payload.listener_count} listeners. "
        f"Root thread: {metadata.thread_id}"
    )

    # Could initialize system state here:
    # - Warm up LLM connections
    # - Load cached schemas
    # - Pre-populate routing caches

    # Send initial prompt to console to start the REPL
    return HandlerResponse(
        payload=ConsolePrompt(
            output=f"Organism '{payload.organism_name}' ready.\n{payload.listener_count} listeners registered.",
            source="system",
            show_banner=True,
        ),
        to="console",
    )
