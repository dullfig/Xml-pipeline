# xml_pipeline/errors.py
# Custom exceptions for the XML pipeline

class PipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass


class SwarmTimeoutError(PipelineError):
    """Raised when a request times out waiting for response."""
    pass


class UnrepairableMessageError(PipelineError):
    """Raised when XML cannot be repaired even with aggressive healing."""
    pass


class ListenerNotFoundError(PipelineError):
    """Raised when no listener is available for a message."""
    pass


class CircuitOpenError(PipelineError):
    """Raised when circuit breaker is open (too many failures)."""
    pass


class ValidationError(PipelineError):
    """Raised when XML fails schema validation."""
    pass


class RepairError(PipelineError):
    """Raised when XML repair fails."""
    pass


class SchemaError(PipelineError):
    """Raised when schema loading or validation fails."""
    pass


class MessageError(PipelineError):
    """Raised when message processing fails."""
    pass
