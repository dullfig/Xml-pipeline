from dataclasses import dataclass, field
from lxml.etree import Element
from typing import Any

"""
default_listener_steps = [
    repair_step,                  # raw bytes → repaired bytes
    c14n_step,                    # bytes → lxml Element
    envelope_validation_step,     # Element → validated Element
    payload_extraction_step,      # Element → payload Element
    xsd_validation_step,          # payload Element + cached XSD → validated
    deserialization_step,         # payload Element → dataclass instance
    routing_resolution_step,      # attaches target_listeners (or error)
]
"""

@dataclass
class HandlerMetadata:
    """Trustworthy context passed to every handler."""
    thread_id: str
    from_id: str
    own_name: str | None = None          # Only for agent: true listeners
    is_self_call: bool = False           # Convenience flag


@dataclass
class MessageState:
    """Universal intermediate representation flowing through all pipelines."""
    raw_bytes: bytes | None = None
    envelope_tree: Element | None = None
    payload_tree: Element | None = None
    payload: Any | None = None           # Deserialized @xmlify instance

    thread_id: str | None = None
    from_id: str | None = None

    target_listeners: list['Listener'] | None = None   # Forward reference

    error: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)  # Extension point