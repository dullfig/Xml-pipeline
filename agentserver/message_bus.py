import asyncio
import uuid
from typing import Dict, Optional

from lxml import etree

from .xmllistener import XMLListener

ENV_NS = "https://xml-pipeline.org/ns/envelope/1"
ENV = f"{{{ENV_NS}}}"


class MessageBus:
    """
    The central nervous system of the organism.

    Responsibilities:
    - Register/unregister listeners with global agent_name uniqueness
    - Immediate routing by payload root tag (± targeted <to>)
    - Envelope handling (convo_id injection on ingress if missing)
    - Response envelope construction
    - Privileged message fast-path detection
    """

    def __init__(self):
        # root_tag → {agent_name → XMLListener}
        self.listeners: Dict[str, Dict[str, XMLListener]] = {}
        # global reverse lookup for error messages and future cross-tag targeting
        self.global_names: Dict[str, XMLListener] = {}

    async def register_listener(self, listener: XMLListener) -> None:
        """Register a listener. Enforces global agent_name uniqueness."""
        if not hasattr(listener, "agent_name") or not listener.agent_name:
            raise ValueError("Listener must have a non-empty agent_name")

        if listener.agent_name in self.global_names:
            raise ValueError(f"Agent name already registered: {listener.agent_name}")

        if not hasattr(listener, "listens_to") or not listener.listens_to:
            raise ValueError(f"Listener {listener.agent_name} must declare listens_to")

        self.global_names[listener.agent_name] = listener

        for tag in listener.listens_to:
            tag_dict = self.listeners.setdefault(tag, {})
            if listener.agent_name in tag_dict:
                raise ValueError(
                    f"{listener.agent_name} already registered for tag <{tag}>"
                )
            tag_dict[listener.agent_name] = listener

    async def unregister_listener(self, agent_name: str) -> None:
        """Remove a listener completely."""
        listener = self.global_names.pop(agent_name, None)
        if listener:
            for tag_dict in self.listeners.values():
                tag_dict.pop(agent_name, None)
            # Clean up empty tag entries
            empty_tags = [tag for tag, d in self.listeners.items() if not d]
            for tag in empty_tags:
                del self.listeners[tag]

    async def dispatch(
        self,
        envelope_xml: str,               # repaired, validated, exclusive C14N
        client_id: Optional[str] = None, # originating connection identifier
    ) -> Optional[str]:
        """
        Main entry point for normal (non-privileged) traffic.
        Returns serialized response envelope if any listener replied, else None.
        """
        tree = etree.fromstring(envelope_xml.encode("utf-8"))

        # Fast-path privileged messages — bypass envelope processing
        root_tag = tree.tag
        if root_tag == "{https://xml-pipeline.org/ns/privileged/1}privileged-msg":
            # In real implementation this will go to PrivilegedMsgListener
            # For now, just acknowledge
            return None

        meta = tree.find(f"{ENV}meta")
        if meta is None:
            # This should never happen after validation, but be defensive
            return None

        from_name = meta.findtext(f"{ENV}from")
        to_name = meta.findtext(f"{ENV}to")
        convo_id_elem = meta.find(f"{ENV}convo_id")
        convo_id = convo_id_elem.text if convo_id_elem is not None else None

        # Inject convo_id on first ingress if missing
        if convo_id is None:
            convo_id = str(uuid.uuid4())
            # Insert into tree for listeners to see
            new_elem = etree.Element(f"{ENV}convo_id")
            new_elem.text = convo_id
            meta.append(new_elem)

        # Find the single payload element (foreign namespace)
        payload_candidates = [
            child for child in tree if child.tag[:len(ENV)] != ENV
        ]
        if not payload_candidates:
            return None
        payload_elem = payload_candidates[0]
        payload_tag = payload_elem.tag

        listeners_for_tag = self.listeners.get(payload_tag, {})

        if to_name:
            # Targeted delivery
            target = listeners_for_tag.get(to_name) or self.global_names.get(to_name)
            if target:
                response_payload = await target.handle(
                    tree, convo_id, from_name or client_id
                )
                return self._build_response_envelope(
                    response_payload, target.agent_name, from_name or client_id, tree
                )
            # Unknown target — silent drop or error envelope (future)
            return None

        else:
            # Fan-out to all listeners for this tag
            tasks = [
                listener.handle(tree, convo_id, from_name or client_id)
                for listener in listeners_for_tag.values()
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # For v1: return the first non-None response (if any)
            # Future: could support multi-response merging
            for resp in responses:
                if isinstance(resp, Exception):
                    continue  # log in real impl
                if resp:
                    # Use the agent_name of the first responding listener
                    responding_listener = next(
                        l for l in listeners_for_tag.values() if l is not None
                    )
                    return self._build_response_envelope(
                        resp,
                        responding_listener.agent_name,
                        from_name or client_id,
                        tree,
                    )
            return None

    def _build_response_envelope(
        self,
        payload_xml: Optional[str],
        from_agent: str,
        original_sender: Optional[str],
        incoming_tree: etree._Element,
    ) -> Optional[str]:
        """Build a proper response envelope from listener payload."""
        if not payload_xml:
            return None

        # Parse the payload the listener returned
        payload_tree = etree.fromstring(payload_xml.encode("utf-8"))

        # Extract convo_id from incoming envelope (default reply-in-thread)
        incoming_convo = incoming_tree.findtext(f"{ENV}convo_id")

        # Check if listener explicitly overrode convo_id in its returned envelope
        # (future-proof — listeners could return full envelope)
        if payload_tree.tag == f"{ENV}message":
            response_meta = payload_tree.find(f"{ENV}meta")
            response_convo = (
                response_meta.findtext(f"{ENV}convo_id") if response_meta is not None else None
            )
            response_to = (
                response_meta.findtext(f"{ENV}to") if response_meta is not None else None
            )
            convo_id = response_convo or incoming_convo
            to_name = response_to or original_sender
            actual_payload = next(
                (c for c in payload_tree if c.tag[:len(ENV)] != ENV), None
            )
        else:
            convo_id = incoming_convo
            to_name = original_sender
            actual_payload = payload_tree

        if actual_payload is None:
            return None

        # Build fresh envelope
        response_root = etree.Element(f"{ENV}message")
        meta = etree.SubElement(response_root, f"{ENV}meta")
        etree.SubElement(meta, f"{ENV}from").text = from_agent
        if to_name:
            etree.SubElement(meta, f"{ENV}to").text = to_name
        if convo_id:
            etree.SubElement(meta, f"{ENV}convo_id").text = convo_id

        response_root.append(actual_payload)

        # noinspection PyTypeChecker
        return etree.tostring(response_root, encoding="unicode", pretty_print=True)
