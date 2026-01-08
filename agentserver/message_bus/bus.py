"""
bus.py — The central MessageBus and pump for AgentServer v2.1

This is the beating heart of the organism:
- Owns all pipelines (one per listener + permanent system pipeline)
- Maintains the routing table (root_tag → Listener(s))
- Orchestrates ingress from sockets/gateways
- Dispatches prepared messages to handlers
- Processes handler responses (multi-payload extraction, provenance injection)
- Guarantees thread continuity and diagnostic injection

Fully aligned with:
  - listener-class-v2.1.md
  - configuration-v2.1.md
  - message-pump-v2.1.md
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Awaitable, List
from uuid import uuid4

from lxml import etree

from agentserver.message_bus.message_state import MessageState, HandlerMetadata
from agentserver.message_bus.steps.repair import repair_step
from agentserver.message_bus.steps.c14n import c14n_step
from agentserver.message_bus.steps.envelope_validation import envelope_validation_step
from agentserver.message_bus.steps.payload_extraction import payload_extraction_step
from agentserver.message_bus.steps.thread_assignment import thread_assignment_step
from agentserver.message_bus.steps.xsd_validation import xsd_validation_step
from agentserver.message_bus.steps.deserialization import deserialization_step
from agentserver.message_bus.steps.routing_resolution import routing_resolution_step

# Type alias for pipeline steps
PipelineStep = Callable[[MessageState], Awaitable[MessageState]]


@dataclass
class Listener:
    """Registered capability — defined in listener.py, referenced here."""
    name: str
    payload_class: type
    handler: Callable
    description: str
    is_agent: bool = False
    peers: list[str] | None = None
    broadcast: bool = False
    pipeline: "Pipeline" | None = None
    schema: etree.XMLSchema | None = None  # cached at registration


class Pipeline:
    """One dedicated pipeline per listener (plus system pipeline)."""
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps

    async def process(self, initial_state: MessageState) -> None:
        """Run the full ordered pipeline on a message."""
        state = initial_state
        for step in self.steps:
            try:
                state = await step(state)
                if state.error:
                    break
            except Exception as exc:  # pylint: disable=broad-except
                state.error = f"Pipeline step {step.__name__} crashed: {exc}"
                break

        # After all steps — dispatch if routable
        if state.target_listeners:
            await MessageBus.get_instance().dispatcher(state)
        else:
            # Fall back to system pipeline for diagnostics
            await MessageBus.get_instance().system_pipeline.process(state)


class MessageBus:
    """Singleton message bus — the pump."""
    _instance: "MessageBus" | None = None

    def __init__(self):
        self.routing_table: dict[str, List[Listener]] = {}  # root_tag → listener(s)
        self.listeners: dict[str, Listener] = {}           # name → Listener
        self.system_pipeline = Pipeline(self._build_system_steps())

    @classmethod
    def get_instance(cls) -> "MessageBus":
        if cls._instance is None:
            cls._instance = MessageBus()
        return cls._instance

    # ------------------------------------------------------------------ #
    # Default step lists
    # ------------------------------------------------------------------ #
    def _build_default_listener_steps(self) -> List[PipelineStep]:
        return [
            repair_step,
            c14n_step,
            envelope_validation_step,
            payload_extraction_step,
            thread_assignment_step,
            xsd_validation_step,
            deserialization_step,
            routing_resolution_step,
        ]

    def _build_system_steps(self) -> List[PipelineStep]:
        """Shorter, fixed steps — no XSD/deserialization."""
        return [
            repair_step,
            c14n_step,
            envelope_validation_step,
            payload_extraction_step,
            thread_assignment_step,
            # system-specific handler that emits <huh>, boot, etc.
            self.system_handler_step,
        ]

    # ------------------------------------------------------------------ #
    # Registration (called from listener.py)
    # ------------------------------------------------------------------ #
    def register_listener(self, listener: Listener) -> None:
        root_tag = f"{listener.name.lower()}.{listener.payload_class.__name__.lower()}"

        if root_tag in self.routing_table and not listener.broadcast:
            raise ValueError(f"Root tag collision: {root_tag} already registered by {self.routing_table[root_tag][0].name}")

        # Build dedicated pipeline
        steps = self._build_default_listener_steps()
        # Inject listener-specific schema for xsd_validation_step
        for step in steps:
            if step.__name__ == "xsd_validation_step":
                # We'll modify state.metadata in pipeline construction instead
                pass
        listener.pipeline = Pipeline(steps)

        # Insert into routing
        self.routing_table.setdefault(root_tag, []).append(listener)
        self.listeners[listener.name] = listener

    # ------------------------------------------------------------------ #
    # Dispatcher — dumb fire-and-await
    # ------------------------------------------------------------------ #
    async def dispatcher(self, state: MessageState) -> None:
        if not state.target_listeners:
            return

        metadata = HandlerMetadata(
            thread_id=state.thread_id or "",
            from_id=state.from_id or "unknown",
            own_name=state.target_listeners[0].name if state.target_listeners[0].is_agent else None,
            is_self_call=(state.from_id == state.target_listeners[0].name) if state.from_id else False,
        )

        if len(state.target_listeners) == 1:
            listener = state.target_listeners[0]
            await self._process_single_handler(state, listener, metadata)
        else:
            # Broadcast — fire all in parallel, process responses as they complete
            tasks = [
                self._process_single_handler(state, listener, metadata)
                for listener in state.target_listeners
            ]
            for future in asyncio.as_completed(tasks):
                await future

    async def _process_single_handler(self, state: MessageState, listener: Listener, metadata: HandlerMetadata) -> None:
        try:
            response_bytes = await listener.handler(state.payload, metadata)

            if response_bytes is None or not isinstance(response_bytes, bytes):
                response_bytes = b"<huh>Handler failed to return valid bytes — missing return or wrong type</huh>"

            payloads = await self._multi_payload_extract(response_bytes)

            for payload_bytes in payloads:
                new_state = MessageState(
                    raw_bytes=payload_bytes,
                    thread_id=state.thread_id,
                    from_id=listener.name,
                )
                # Route the new payload through normal pipelines
                root_tag = self._derive_root_tag(payload_bytes)
                targets = self.routing_table.get(root_tag)
                if targets:
                    new_state.target_listeners = targets
                    await targets[0].pipeline.process(new_state)
                else:
                    await self.system_pipeline.process(new_state)

        except Exception as exc:  # pylint: disable=broad-except
            error_state = MessageState(
                raw_bytes=b"<huh>Handler crashed</huh>",
                thread_id=state.thread_id,
                from_id=listener.name,
                error=f"Handler {listener.name} crashed: {exc}",
            )
            await self.system_pipeline.process(error_state)

    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #
    async def _multi_payload_extract(self, raw_bytes: bytes) -> List[bytes]:
        # Same logic as before — dummy wrap, repair, extract all root elements
        # (implementation can be moved to a shared util later)
        # For now, placeholder — we'll flesh this out in response_processing.py
        return [raw_bytes]  # temporary — will be full extraction

    def _derive_root_tag(self, payload_bytes: bytes) -> str:
        # Quick parse to get root tag — used only for routing extracted payloads
        try:
            tree = etree.fromstring(payload_bytes)
            tag = tree.tag
            if tag.startswith("{"):
                return tag.split("}", 1)[1]  # strip namespace
            return tag
        except Exception:
            return ""

    async def system_handler_step(self, state: MessageState) -> MessageState:
        # Emit <huh> or boot message — placeholder for now
        state.error = state.error or "Unhandled by any listener"
        return state