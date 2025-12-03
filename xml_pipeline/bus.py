# xml_pipeline/bus.py
# Version 1.0.1 — November 2025 — Battle-tested patch release

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    overload,
)

from . import pipeline
from .circuit import CircuitBreaker
from .errors import (
    SwarmTimeoutError,
    UnrepairableMessageError,
    ListenerNotFoundError,
    CircuitOpenError,
)

__all__ = ["MessageBus", "listener", "Response"]

log = logging.getLogger("xml_pipeline.bus")

ListenerFunc = Callable[[bytes], Awaitable[Optional[bytes]]]
T = TypeVar("T")

@dataclass(frozen=True)
class Response:
    xml: bytes
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    tombstone: bool = False
    outcome: Optional[str] = None  # success|failed|cancelled


@dataclass
class _PendingRequest:
    future: asyncio.Future[bytes]
    cardinality: str
    required_replies: int = 1
    received_replies: int = 0
    replies: List[bytes] = None  # type: ignore


class _Listener:
    def __init__(
        self,
        func: ListenerFunc,
        roots: Tuple[str, ...],
        version: str = "*",
        priority: int = 0,
    ):
        self.func = func
        self.roots = roots
        self.version = version
        self.priority = priority
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(10)
        # One circuit per (root, version) pair to avoid cross-contamination
        self.circuits: Dict[Tuple[str, str], CircuitBreaker] = {}

    def get_circuit(self, root: str, version: str | None) -> CircuitBreaker:
        key = (root, version or "*")
        return self.circuits.setdefault(key, CircuitBreaker())

    def matches(self, root: str, version: str | None) -> bool:
        return root in self.roots and (self.version == "*" or self.version == version)


class MessageBus:
    def __init__(
        self,
        *,
        schema_paths: List[str] | None = None,
        default_timeout: float = 300.0,
        healthcheck_interval: float = 10.0,
        max_concurrent_per_listener: int = 10,
        persistence: str | None = None,
    ):
        self.default_timeout = default_timeout
        self.healthcheck_interval = healthcheck_interval
        self.max_concurrent_per_listener = max_concurrent_per_listener

        self._listeners: List[_Listener] = []
        self._pending: Dict[str, _PendingRequest] = {}  # message-id → request state
        self._locks = asyncio.Lock()

        self.pipeline = pipeline.Pipeline(schema_paths=schema_paths or [])
        self._health_task = None  # Lazy-initialized when event loop is running
    
    def _ensure_health_task(self):
        """Ensure health checker task is running (lazy initialization)."""
        if self._health_task is None:
            try:
                loop = asyncio.get_running_loop()
                self._health_task = loop.create_task(self._health_checker())
            except RuntimeError:
                # No event loop running yet, that's ok
                pass

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def request(
        self,
        xml: str | bytes,
        *,
        timeout: float | None = None,
        cardinality: str = "one",        # one | any | all
        flow: str = "request-response",
    ) -> bytes | List[bytes]:
        self._ensure_health_task()  # Start health checker if needed
        
        if flow != "request-response":
            raise ValueError("request() requires flow='request-response'")

        processed, root, version = await self.pipeline.process(xml)
        msg_id = pipeline.extract_message_id(processed) or str(uuid.uuid4())

        future: asyncio.Future[bytes | List[bytes]] = asyncio.Future()
        req = _PendingRequest(
            future=future,
            cardinality=cardinality,
            required_replies=0,  # will be set after routing
            replies=[] if cardinality == "all" else None,
        )

        async with self._locks:
            self._pending[msg_id] = req

        await self._route(processed, root, version, cardinality, flow, original_id=msg_id)

        try:
            result = await asyncio.wait_for(future, timeout or self.default_timeout)
            return result
        except asyncio.TimeoutError as e:
            async with self._locks:
                self._pending.pop(msg_id, None)
            raise SwarmTimeoutError(f"Request {msg_id[:8]} timed out") from e

    async def publish(
        self,
        xml: str | bytes,
        *,
        cardinality: str = "any",
        flow: str = "fire-and-forget",
        return_canonical: bool = False,
    ) -> None | Tuple[bytes, str, str, str | None]:
        processed, root, version = await self.pipeline.process(xml)
        msg_id = pipeline.extract_message_id(processed) or str(uuid.uuid4())

        await self._route(processed, root, version, cardinality, flow, original_id=msg_id)

        if return_canonical:
            return processed, msg_id, root or "", version

        return None

    async def reply(
        self,
        response: Union[str, bytes, Response],
        *,
        original_message: bytes | None = None,
        original_id: str | None = None,
    ) -> None:
        if isinstance(response, Response):
            xml = response.xml
            msg_id = response.message_id or str(uuid.uuid4())
            in_reply_to = response.in_reply_to or original_id
            tombstone = response.tombstone
            outcome = response.outcome
        else:
            xml = response if isinstance(response, bytes) else response.encode("utf-8")
            msg_id = str(uuid.uuid4())
            in_reply_to = original_id
            tombstone = False
            outcome = None

        if in_reply_to is None:
            raise ValueError("reply() requires original_id or in_reply_to")

        processed, _, _ = await self.pipeline.process(
            xml,
            inject_correlation={
                "message-id": msg_id,
                "in-reply-to": in_reply_to,
                "tombstone": tombstone,
                "outcome": outcome,
            },
        )

        await self._route(
            processed,
            root=None,
            version=None,
            cardinality="one",
            flow="fire-and-forget",
            original_id=in_reply_to,  # critical: this is the request we’re answering
        )

    # ------------------------------------------------------------------ #
    # Listener registration
    # ------------------------------------------------------------------ #

    @overload
    def listener(self, *roots: str, version: str = "*") -> Callable[[ListenerFunc], ListenerFunc]:
        ...

    @overload
    def listener(
        self,
        *roots: str,
        version: str = "*",
        priority: int = 0,
    ) -> Callable[[ListenerFunc], ListenerFunc]:
        ...

    def listener(
        self,
        *roots: str,
        version: str = "*",
        priority: int = 0,
    ) -> Callable[[ListenerFunc], ListenerFunc]:
        def decorator(func: ListenerFunc) -> ListenerFunc:
            lst = _Listener(func, roots, version, priority)
            lst.semaphore = asyncio.Semaphore(self.max_concurrent_per_listener)
            self._listeners.append(lst)
            self._listeners.sort(key=lambda l: l.priority, reverse=True)
            return func
        return decorator

    # ------------------------------------------------------------------ #
    # Core routing & delivery
    # ------------------------------------------------------------------ #

    async def _route(
        self,
        canonical_xml: bytes,
        root: str | None,
        version: str | None,
        cardinality: str,
        flow: str,
        original_id: str | None = None,
    ) -> None:
        msg_id = pipeline.extract_message_id(canonical_xml) or "no-id"
        matching = [
            lst for lst in self._listeners
            if lst.matches(root or "", version)
        ]

        if not matching and flow == "request-response" and original_id:
            # Auto-nack unknown request
            log.warning("No listener for %s (id=%s)", root, msg_id[:8])
            await self._complete_request(original_id, None)
            return

        # Count matching listeners *before* circuit filtering for correct "all" semantics
        viable = [lst for lst in matching if not lst.get_circuit(root or "", version).is_open()]
        expected = len(viable)

        if flow == "request-response" and original_id and expected > 0:
            async with self._locks:
                if original_id in self._pending:
                    self._pending[original_id].required_replies = (
                        expected if cardinality == "all" else 1
                    )

        tasks = []
        for lst in viable:
            task = asyncio.create_task(
                self._deliver_to_listener(lst, canonical_xml, root, version, original_id)
            )
            tasks.append(task)
            if cardinality == "one":
                break

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver_to_listener(
        self,
        lst: _Listener,
        xml: bytes,
        root: str | None,
        version: str | None,
        reply_to_id: str | None,
    ) -> None:
        circuit = lst.get_circuit(root or "", version or "*")
        async with lst.semaphore:
            try:
                result = await asyncio.wait_for(lst.func(xml), timeout=self.default_timeout)
                circuit.record_success()
            except Exception as exc:
                circuit.record_failure()
                log.exception("Listener %s failed", lst.func.__name__)
                return

            if result is None:
                return

            # Build reply
            if isinstance(result, Response):
                reply_xml = result.xml
                in_reply_to = result.in_reply_to or reply_to_id
            else:
                reply_xml = result if isinstance(result, bytes) else result.encode("utf-8")
                in_reply_to = reply_to_id

            if in_reply_to is None:
                return  # fire-and-forget reply with no destination

            processed, _, _ = await self.pipeline.process(
                reply_xml,
                inject_correlation={"in-reply-to": in_reply_to},
            )

            await self._complete_request(in_reply_to, processed)

    async def _complete_request(self, request_id: str, reply_xml: bytes | None) -> None:
        async with self._locks:
            req = self._pending.get(request_id)
            if not req or req.future.done():
                return

            if reply_xml is None:
                # NACK path
                req.future.set_exception(ListenerNotFoundError(f"No listener for {request_id[:8]}"))
                self._pending.pop(request_id, None)
                return

            if req.cardinality == "all":
                req.replies.append(reply_xml)
                req.received_replies += 1
                if req.received_replies >= req.required_replies:
                    req.future.set_result(req.replies)
                    self._pending.pop(request_id, None)
            else:
                # "one" or "any" — first reply wins
                req.future.set_result(reply_xml)
                self._pending.pop(request_id, None)

    async def _health_checker(self) -> None:
        while True:
            await asyncio.sleep(self.healthcheck_interval)
            ping = f'<ping timestamp="{datetime.now(timezone.utc).isoformat()}"/>'.encode()
            try:
                await self.publish(ping, cardinality="any")
            except Exception:
                pass

    async def close(self) -> None:
        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        async with self._locks:
            for req in self._pending.values():
                if not req.future.done():
                    req.future.cancel()
            self._pending.clear()


# Global default bus
default_bus = MessageBus()

def listener(*args, **kwargs):
    return default_bus.listener(*args, **kwargs)