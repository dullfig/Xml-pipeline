"""
deserialization.py — Convert validated payload_tree into typed dataclass instance.

After xsd_validation_step confirms the payload conforms to the listener's contract,
this step uses the xmlable library to deserialize the lxml Element into the
registered @xmlify dataclass.

The resulting instance is placed in state.payload and handed to the handler.

Part of AgentServer v2.1 message pump.
"""

from xmlable import from_xml  # from the xmlable library
from agentserver.message_bus.message_state import MessageState


async def deserialization_step(state: MessageState) -> MessageState:
    """
    Deserialize the validated payload_tree into the listener's dataclass.

    Requires:
      - state.payload_tree valid against listener XSD
      - state.metadata["payload_class"] set to the target dataclass (set at registration)

    On success: state.payload = dataclass instance
    On failure: state.error set with clear message
    """
    if state.payload_tree is None:
        state.error = "deserialization_step: no payload_tree (previous step failed)"
        return state

    payload_class = state.metadata.get("payload_class")
    if payload_class is None:
        state.error = "deserialization_step: no payload_class in metadata (listener misconfigured)"
        return state

    try:
        # xmlable.from_xml handles namespace-aware deserialization
        instance = from_xml(payload_class, state.payload_tree)
        state.payload = instance

    except Exception as exc:  # pylint: disable=broad-except
        state.error = f"deserialization_step failed: {exc}"

    return state