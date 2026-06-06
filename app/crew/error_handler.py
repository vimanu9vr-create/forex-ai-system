import time
import logging
from typing import Callable, Any, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    RETRYABLE = "retryable"
    FATAL = "fatal"
    DEGRADABLE = "degradable"


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, timeout_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

    def is_open(self) -> bool:
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if (
                self.last_failure_time
                and datetime.now() - self.last_failure_time
                > timedelta(seconds=self.timeout_seconds)
            ):
                self.state = CircuitBreakerState.HALF_OPEN
                self.failure_count = 0
                logger.info("Circuit breaker transitioning to half-open")
                return False
            return True
        return False


def classify_error(error: Exception) -> ErrorType:
    """Classify error as retryable, fatal, or degradable"""
    error_str = str(error).lower()

    # Retryable errors (connection, timeout, rate limit)
    retryable_keywords = [
        "timeout",
        "connection",
        "refused",
        "temporarily",
        "busy",
        "rate limit",
        "429",
        "503",
        "504",
    ]

    # Fatal errors (auth, not found, validation)
    fatal_keywords = [
        "authentication",
        "unauthorized",
        "forbidden",
        "404",
        "not found",
        "invalid",
        "validation",
    ]

    for keyword in retryable_keywords:
        if keyword in error_str:
            return ErrorType.RETRYABLE

    for keyword in fatal_keywords:
        if keyword in error_str:
            return ErrorType.FATAL

    return ErrorType.DEGRADABLE


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_wait: float = 1.0,
    backoff_multiplier: float = 2.0,
    *args,
    **kwargs,
) -> Dict[str, Any]:
    """
    Execute function with exponential backoff retry logic.

    Returns:
        {
            "success": bool,
            "result": Any,
            "error": Optional[Exception],
            "attempts": int,
            "error_type": ErrorType
        }
    """
    wait_time = initial_wait
    last_error = None
    error_type = None

    for attempt in range(max_retries + 1):
        try:
            result = func(*args, **kwargs)
            logger.info(f"Successfully executed {func.__name__} on attempt {attempt + 1}")
            return {
                "success": True,
                "result": result,
                "error": None,
                "attempts": attempt + 1,
                "error_type": None,
            }

        except Exception as e:
            last_error = e
            error_type = classify_error(e)

            if error_type == ErrorType.FATAL:
                logger.error(f"Fatal error in {func.__name__}: {e}")
                return {
                    "success": False,
                    "result": None,
                    "error": e,
                    "attempts": attempt + 1,
                    "error_type": error_type,
                }

            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}. "
                    f"Retrying in {wait_time}s... Error: {e}"
                )
                time.sleep(wait_time)
                wait_time *= backoff_multiplier
            else:
                logger.error(
                    f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                )

    return {
        "success": False,
        "result": None,
        "error": last_error,
        "attempts": max_retries + 1,
        "error_type": error_type,
    }


def with_fallback(primary_func: Callable, fallback_func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Execute primary function with fallback on failure.

    Returns:
        {
            "success": bool,
            "result": Any,
            "source": "primary" | "fallback" | "failed",
            "error": Optional[Exception]
        }
    """
    try:
        result = primary_func(*args, **kwargs)
        logger.info(f"Primary function {primary_func.__name__} succeeded")
        return {
            "success": True,
            "result": result,
            "source": "primary",
            "error": None,
        }

    except Exception as e:
        logger.warning(f"Primary function {primary_func.__name__} failed: {e}. Using fallback.")
        try:
            result = fallback_func(*args, **kwargs)
            logger.info(f"Fallback function {fallback_func.__name__} succeeded")
            return {
                "success": True,
                "result": result,
                "source": "fallback",
                "error": e,
            }

        except Exception as fallback_error:
            logger.error(f"Both primary and fallback failed: {fallback_error}")
            return {
                "success": False,
                "result": None,
                "source": "failed",
                "error": fallback_error,
            }


class ErrorMetrics:
    """Track error statistics for monitoring"""

    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_types: Dict[str, ErrorType] = {}
        self.last_errors: Dict[str, Exception] = {}

    def record_error(self, operation: str, error: Exception):
        if operation not in self.error_counts:
            self.error_counts[operation] = 0
        self.error_counts[operation] += 1
        self.error_types[operation] = classify_error(error)
        self.last_errors[operation] = error

    def get_stats(self, operation: str) -> Dict[str, Any]:
        return {
            "operation": operation,
            "error_count": self.error_counts.get(operation, 0),
            "error_type": self.error_types.get(operation, "none"),
            "last_error": str(self.last_errors.get(operation, "none")),
        }

    def get_all_stats(self) -> Dict[str, Any]:
        return {op: self.get_stats(op) for op in self.error_counts.keys()}


# Global error metrics instance
error_metrics = ErrorMetrics()
