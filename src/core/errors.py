"""Error handling and retry utilities."""
import time
import functools
import logging
from typing import Callable, Type, Tuple, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    RETRYABLE = "retryable"  # Network timeout, temporary failure
    BUSINESS = "business"    # Model load failure, invalid input
    FATAL = "fatal"          # Data corruption, configuration error


class DicomAgentError(Exception):
    """Base exception for DICOM Agent."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.BUSINESS):
        super().__init__(message)
        self.severity = severity
        self.message = message


class RetryableError(DicomAgentError):
    """Error that can be retried."""

    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.RETRYABLE)


class BusinessError(DicomAgentError):
    """Business logic error."""

    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.BUSINESS)


class FatalError(DicomAgentError):
    """Fatal error that should not be retried."""

    def __init__(self, message: str):
        super().__init__(message, ErrorSeverity.FATAL)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: Tuple[Type[Exception], ...] = (RetryableError, TimeoutError, ConnectionError),
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """Decorator to retry function with exponential backoff.

    Args:
        config: Retry configuration
        on_retry: Callback on each retry (exception, attempt_number)

    Example:
        @retry_with_backoff(RetryConfig(max_attempts=3))
        def fetch_dicom(url):
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts:
                        logger.error(f"Max retries ({config.max_attempts}) reached for {func.__name__}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay,
                    )

                    logger.warning(
                        f"Retry {attempt}/{config.max_attempts} for {func.__name__}: {e}. "
                        f"Waiting {delay:.2f}s"
                    )

                    if on_retry:
                        on_retry(e, attempt)

                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise BusinessError("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)

            # Success - reset circuit breaker
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")

            return result

        except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"
                    logger.error(f"Circuit breaker OPEN after {self.failure_count} failures")

                raise BusinessError(str(e))

    def reset(self):
        """Manually reset circuit breaker."""
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None


def format_error_message(error: Exception, context: Optional[dict] = None) -> str:
    """Format error message with context and suggestions.

    Args:
        error: The exception
        context: Additional context (operation, input, etc.)

    Returns:
        User-friendly error message with suggestions
    """
    msg = str(error)
    suggestions = []

    # Add suggestions based on error type
    if isinstance(error, (TimeoutError, ConnectionError)):
        suggestions.append("Check network connection")
        suggestions.append("Try again later")
    elif isinstance(error, FileNotFoundError):
        suggestions.append("Verify file path is correct")
    elif isinstance(error, ValueError):
        suggestions.append("Check input parameters")

    suggestion_text = ""
    if suggestions:
        suggestion_text = " Suggestions: " + "; ".join(suggestions)

    context_text = ""
    if context:
        ctx_str = ", ".join(f"{k}={v}" for k, v in context.items())
        context_text = f" [Context: {ctx_str}]"

    return f"{msg}{context_text}{suggestion_text}"