"""Infrastructure layer for ComfoClime integration.

This package contains core infrastructure components:
- API utilities (decorators, rate limiting, caching)
- Validation logic
- Error definitions
- Access tracking
"""

# Re-export commonly used components for backward compatibility
from .api import (
    DEFAULT_CACHE_TTL,
    DEFAULT_MIN_REQUEST_INTERVAL,
    DEFAULT_REQUEST_DEBOUNCE,
    DEFAULT_WRITE_COOLDOWN,
    RateLimiterCache,
    api_get,
    api_put,
)
from .errors import (
    ComfoClimeAPIError,
    ComfoClimeConnectionError,
    ComfoClimeError,
    ComfoClimeTimeoutError,
    ComfoClimeValidationError,
)
from .tracking import AccessTracker
from .validation import (
    validate_byte_value,
    validate_duration,
    validate_host,
    validate_property_path,
)

__all__ = [
    # API decorators and utilities
    "api_get",
    "api_put",
    "RateLimiterCache",
    # API constants
    "DEFAULT_MIN_REQUEST_INTERVAL",
    "DEFAULT_WRITE_COOLDOWN",
    "DEFAULT_REQUEST_DEBOUNCE",
    "DEFAULT_CACHE_TTL",
    # Errors
    "ComfoClimeError",
    "ComfoClimeConnectionError",
    "ComfoClimeAPIError",
    "ComfoClimeTimeoutError",
    "ComfoClimeValidationError",
    # Tracking
    "AccessTracker",
    # Validation
    "validate_host",
    "validate_property_path",
    "validate_byte_value",
    "validate_duration",
]
