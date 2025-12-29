"""
Core base class for all listeners in the organism.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from lxml import etree

logger = logging.getLogger(__name__)


class XMLListener:
    """
    Base class for all capabilities (personalities, tools, gateways).

    Subclasses must:
    - Define `listens_to` (list of root tags they handle)
    - Implement `async handle()`

    The `convo_id` received in handle() MUST be preserved in any response payload.
    """

    listens_to: List[str] = []  # Must be overridden in subclass

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self.name = name or self.__class__.__name__
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    async def handle(
        self, msg: etree.Element, convo_id: str
    ) -> Optional[etree.Element]:
        """
        Handle a message whose root tag matches this listener.

        Args:
            msg: The payload element (repaired and C14N'd)
            convo_id: Thread/conversation UUID — must be preserved in response

        Returns:
            Response payload element with the same convo_id, or None
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
        Helper to create a response element with a preserved convo_id attribute.
        Recommended for all listeners.
        """
        elem = etree.Element(tag, convo_id=convo_id, **attribs)
        if text is not None:
            elem.text = text
        return elem

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} listens_to={self.listens_to}>"