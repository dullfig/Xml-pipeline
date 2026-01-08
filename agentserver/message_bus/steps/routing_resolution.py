"""
routing_resolution.py — Resolve routing based on derived root tag.

This is the final preparation step before dispatch.
It computes the root tag from the deserialized payload and looks it up in the
global routing table (root_tag → list[Listener]).

On success: state.target_listeners is set
On failure: state.error is set → message falls to system pipeline for <huh>

Part of AgentServer v2.1 message pump.
"""

from agentserver.message_bus.message_state import MessageState
from agentserver.message_bus.bus import MessageBus


async def routing_resolution_step(state: MessageState) -> MessageState:
    """
    Resolve which listener(s) should handle this payload.

    Root tag = f"{from_id.lower()}.{payload_class_name.lower()}"
    (from_id is trustworthy — injected by pump)

    Supports:
      - Normal unique routing (one listener)
      - Broadcast (multiple listeners if broadcast: true and same root tag)

    If no match → error, falls to system pipeline.
    """
    if state.payload is None:
        state.error = "routing_resolution_step: no deserialized payload (previous step failed)"
        return state

    if state.from_id is None:
        state.error = "routing_resolution_step: missing from_id (provenance error)"
        return state

    payload_class_name = type(state.payload).__name__.lower()
    root_tag = f"{state.from_id.lower()}.{payload_class_name}"

    bus = MessageBus.get_instance()
    targets = bus.routing_table.get(root_tag)

    if not targets:
        state.error = f"routing_resolution_step: unknown capability root tag '{root_tag}'"
        return state

    state.target_listeners = targets
    return state