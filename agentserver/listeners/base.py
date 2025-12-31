"""
Core base class for all listeners in the xml-pipeline organism.

All capabilities — personalities, tools, gateways — inherit from this class.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

from lxml import etree

logger = logging.getLogger(__name__)


class XMLListener:
    """
    Base class for all capabilities (personalities, tools, gateways).

    Subclasses must:
    - Define `listens_to` as a class attribute (list of root tags they handle)
    - Implement `async handle()` method

    The `convo_id` received in handle() MUST be preserved in any response payload
    (via make_response() helper or manually).
    """

    listens_to: List[str] = []  # Must be overridden in subclass — required

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Args:
            name: Optional explicit name (defaults to class name)
            config: Owner-provided configuration from privileged registration
        """
        self.name = name or self.__class__.__name__
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    async def handle(
        self, msg: etree.Element, convo_id: str
    ) -> Optional[etree.Element]:
        """
        Process an incoming message whose root tag matches this listener.

        Args:
            msg: The payload element (already repaired and C14N'd)
            convo_id: Thread/conversation UUID — must be preserved in any response

        Returns:
            Response payload element (with convo_id preserved), or None if no response
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.handle() must be implemented"
        )

    def make_response(
        self,
        tag: str,
        text: Optional[str] = None,
        *,
        convo_id: str,
        **attribs,
    ) -> etree.Element:
        """
        Convenience helper to create a response element with preserved convo_id.

        Strongly recommended for all listeners to ensure thread continuity.
        """
        elem = etree.Element(tag, convo_id=convo_id, **attribs)
        if text is not None:
            elem.text = text
        return elem

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.name}' listens_to={self.listens_to}>"