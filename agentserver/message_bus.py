import asyncio
import logging
from typing import Dict, Optional, Callable
from lxml import etree

from .xml_listener import XMLListener
from .utils.message import repair_and_canonicalize, XmlTamperError

# Constants for Internal Physics
ENV_NS = "https://xml-pipeline.org/ns/envelope/1"
ENV = f"{{{ENV_NS}}}"
LOG_TAG = "{https://xml-pipeline.org/ns/logger/1}log"

logger = logging.getLogger("agentserver.bus")


class MessageBus:
    """
    The Pure Carrier: Routes XML trees between sovereign listeners.
    - Core: High-speed tree-to-tree routing.
    - Border: 'Air Lock' for ingesting raw bytes.
    - Physics: Hardcoded hooks for the Audit Witness.
    """

    def __init__(self, log_hook: Callable[[etree.Element], None]):
        # root_tag -> {agent_name -> XMLListener}
        self.listeners: Dict[str, Dict[str, XMLListener]] = {}
        # Global lookup for directed <to/> routing
        self.global_names: Dict[str, XMLListener] = {}
        # The 'Physics' hook provided by the Host (AgentServer)
        self._log_hook = log_hook

    async def register_listener(self, listener: XMLListener) -> None:
        """Register an organ. Enforces global identity uniqueness."""
        if listener.agent_name in self.global_names:
            raise ValueError(f"Identity collision: {listener.agent_name}")

        self.global_names[listener.agent_name] = listener
        for tag in listener.listens_to:
            tag_dict = self.listeners.setdefault(tag, {})
            tag_dict[listener.agent_name] = listener

        logger.info(f"Registered organ: {listener.agent_name}")


    async def deliver_bytes(
            self,
            raw_xml: bytes,
            client_id: Optional[str] = None
    ) -> Optional[str]:
        """
        The Air Lock: Ingests raw bytes from unauthenticated or foreign sources.
        Repairs and validates them before injecting the tree into the core.
        """
        try:
            # 1. Pressurize (Bytes -> Tree)
            envelope_tree: etree._Element = repair_and_canonicalize(raw_xml)
            # 2. Inject into core
            return await self.dispatch(envelope_tree, client_id)
        except XmlTamperError as e:
            logger.warning(f"Air Lock Reject: {e}")
            return None


    async def dispatch(
            self,
            envelope_tree: etree._Element,
            client_id: Optional[str] = None
    ) -> Optional[str]:
        """
        The Pure Heart: Routes a tree. Returns a validated response string.
        """
        # 1. WITNESS: Automatic logging of the truth
        self._log_hook(envelope_tree)

        # 2. Extract Metadata
        meta = envelope_tree.find(f"{ENV}meta")
        from_name = meta.findtext(f"{ENV}from")
        to_name = meta.findtext(f"{ENV}to")
        thread_id = meta.findtext(f"{ENV}thread")

        payload_elem = next((c for c in envelope_tree.iterchildren() if c.tag != f"{ENV}meta"), None)
        if payload_elem is None: return None
        payload_tag = payload_elem.tag

        # 3. AUTONOMIC REFLEX: The Logger Hook (Hardcoded Physics)
        if payload_tag == LOG_TAG:
            self._log_hook(envelope_tree)
            return f"<message xmlns='{ENV_NS}'><meta><from>system</from><to>{from_name}</to><thread_id>{thread_id}</thread_id></meta><logged status='success'/></message>"

        # 4. ROUTING
        listeners_for_tag = self.listeners.get(payload_tag, {})
        response_tree = None
        responding_agent_name = "unknown"

        if to_name:
            # Directed Mode
            target = listeners_for_tag.get(to_name) or self.global_names.get(to_name)
            if target:
                responding_agent_name = target.agent_name
                response_tree = await target.handle(envelope_tree, thread_id, from_name or client_id)
        else:
            # Broadcast Mode
            tasks = [l.handle(envelope_tree, thread_id, from_name or client_id) for l in listeners_for_tag.values()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, resp in enumerate(results):
                if isinstance(resp, etree._Element):
                    responding_agent_name = list(listeners_for_tag.values())[i].agent_name
                    response_tree = resp
                    break

        # 5. EGRESS CUSTOMS: Final validation before bytes hit the wire
        if response_tree is not None:
            return self._inspect_and_serialize(response_tree, responding_agent_name)

        return None


    def _inspect_and_serialize(self, tree: etree._Element, expected_from: str) -> Optional[str]:
        """Ensures identity integrity and performs final string serialization."""
        actual_from = tree.findtext(f"{ENV}meta/{ENV}from")
        if actual_from != expected_from:
            logger.critical(f"IDENTITY THEFT BLOCKED: {expected_from} spoofed {actual_from}")
            return None
        # noinspection PyTypeChecker
        return etree.tostring(tree, encoding="unicode", pretty_print=True)