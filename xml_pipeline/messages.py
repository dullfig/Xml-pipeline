# xml_pipeline/messages.py
# Message types and topic definitions

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class Topic(str, Enum):
    """Predefined message topics for routing."""
    
    CAD_TASK = "cad-task"
    CAD_RESULT = "cad-result"
    MBD_QUERY = "mbd-query"
    MBD_RESPONSE = "mbd-response"
    LOG_ENTRY = "log-entry"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_root_tag(cls, root_tag: str) -> "Topic":
        """Convert XML root tag to Topic enum."""
        try:
            return cls(root_tag)
        except ValueError:
            return cls.UNKNOWN


@dataclass
class Message:
    """
    Structured representation of an XML message.
    
    Attributes:
        xml: Raw canonical XML bytes
        message_id: Unique message identifier
        topic: Message topic/type
        version: Message schema version
        timestamp: When message was created
        in_reply_to: ID of message this is replying to
        correlation_id: For tracking related messages
    """
    
    xml: bytes
    message_id: str
    topic: Topic
    version: Optional[str] = None
    timestamp: Optional[datetime] = None
    in_reply_to: Optional[str] = None
    correlation_id: Optional[str] = None
    
    @property
    def is_reply(self) -> bool:
        """Check if this message is a reply to another."""
        return self.in_reply_to is not None
    
    @property
    def root_tag(self) -> str:
        """Get the topic as string."""
        return self.topic.value
    
    def __repr__(self) -> str:
        return (
            f"Message(id={self.message_id[:8]}..., "
            f"topic={self.topic.value}, "
            f"version={self.version}, "
            f"reply_to={self.in_reply_to[:8] + '...' if self.in_reply_to else None})"
        )
