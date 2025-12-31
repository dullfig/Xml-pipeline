"""
xmllistener.py — The Sovereign Contract for All Capabilities

In xml-pipeline, there are no "agents", no "tools", no "services".
There are only bounded, reactive XMLListeners.

Every capability in the organism — whether driven by an LLM,
a pure function, a remote gateway, or privileged logic —
must inherit from this class.

This file is intentionally verbose and heavily documented.
It is the constitution that all organs must obey.
"""

from __future__ import annotations

import uuid
from typing import Optional, List, ClassVar
from lxml import etree

class XMLListener:
    """
    Base class for all reactive capabilities in the organism.

    Key Invariants (never break these):
    1. Listeners are passive. They never initiate. They only react.
    2. They declare what they listen to via class variable.
    3. They have a globally unique agent_name.
    4. They receive the full parsed envelope tree (not raw XML).
    5. They return only payload XML (never the envelope).
    6. The MessageBus owns routing, threading, and envelope wrapping.
    """

    # ===================================================================
    # Required class declarations — must be overridden in subclasses
    # ===================================================================

    listens_to: ClassVar[List[str]] = []
    """
    List of full XML tags this listener reacts to.
    Example: ["{https://example.org/chat}message", "{https://example.org/calc}request"]
    """

    agent_name: ClassVar[str] = ""
    """
    Globally unique name for this instance.
    Enforced by MessageBus at registration.
    Used in <from/>, routing, logging, and known_peers prompts.
    """

    # ===================================================================
    # Core handler — the only method that does work
    # ===================================================================

    async def handle(
        self,
        envelope_tree: etree._Element,
        convo_id: str,
        sender_name: Optional[str],
    ) -> Optional[str]:
        """
        React to an incoming enveloped message.

        Parameters:
            envelope_tree: Full <env:message> root (parsed, post-repair/C14N)
            convo_id: Current conversation UUID (injected or preserved by bus)
            sender_name: The <from/> value (mandatory)

        Returns:
            Payload XML string (no envelope) if responding, else None.

        The organism guarantees:
            - envelope_tree is valid against envelope.xsd
            - <from/> is present and matches sender_name
            - convo_id is a valid UUID

        To reply in the current thread: omit convo_id in response → bus preserves it
        To start a new thread: include <env:convo_id>new-uuid</env:convo_id> in returned envelope
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement handle()"
        )

    # ===================================================================
    # Optional convenience helpers (can be overridden)
    # ===================================================================

    def make_response(
        self,
        payload: str | etree._Element,
        *,
        to: Optional[str] = None,
        convo_id: Optional[str] = None,
    ) -> str:
        """
        Helper for building correct response payloads.
        Use this in subclasses to avoid envelope boilerplate.

        - If convo_id is None → reply in current thread
        - If convo_id provided → force/start new thread
        - to overrides default reply-to-sender
        """
        # Implementation tomorrow — but declared here for contract clarity
        raise NotImplementedError