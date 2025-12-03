# xml_pipeline/circuit.py
# Circuit breaker pattern for resilient message handling

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, requests flow through
    - OPEN: Too many failures, reject all requests
    - HALF_OPEN: Testing if service recovered
    """
    
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    success_threshold: int = 2  # successes needed to close from half-open
    
    def __post_init__(self):
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: Optional[float] = None
        self._state: str = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        if self._state == "OPEN":
            # Check if recovery timeout has passed
            if self._last_failure_time and time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                self._success_count = 0
                return False
            return True
        return False
    
    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == "HALF_OPEN":
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = "CLOSED"
                self._failure_count = 0
        elif self._state == "CLOSED":
            self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "OPEN"
        elif self._state == "HALF_OPEN":
            self._state = "OPEN"
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
    
    @property
    def state(self) -> str:
        """Current state of the circuit breaker."""
        # Update state if needed
        self.is_open()
        return self._state
