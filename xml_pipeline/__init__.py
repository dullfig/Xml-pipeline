"""
xml_pipeline - Tamper-proof XML nervous system for AI agent swarms
"""

from .pipeline import Pipeline, extract_message_id
from .bus import MessageBus, Response, listener
from .messages import Message, Topic
from .errors import (
    PipelineError,
    ValidationError,
    RepairError,
    SchemaError,
    MessageError,
    SwarmTimeoutError,
    UnrepairableMessageError,
    ListenerNotFoundError,
    CircuitOpenError,
)
from .circuit import CircuitBreaker
from .schema_catalog import SchemaCatalog
from . import utils

__all__ = [
    # Core
    "Pipeline",
    "MessageBus",
    "Response",
    "listener",
    
    # Messages
    "Message",
    "Topic",
    
    # Errors
    "PipelineError",
    "ValidationError",
    "RepairError",
    "SchemaError",
    "MessageError",
    "SwarmTimeoutError",
    "UnrepairableMessageError",
    "ListenerNotFoundError",
    "CircuitOpenError",
    
    # Utilities
    "CircuitBreaker",
    "SchemaCatalog",
    "extract_message_id",
    "utils",
]

# Version is managed by setuptools_scm
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
