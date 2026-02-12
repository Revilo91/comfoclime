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
    "DEFAULT_CACHE_TTL",
    # API constants
    "DEFAULT_MIN_REQUEST_INTERVAL",
    "DEFAULT_REQUEST_DEBOUNCE",
    "DEFAULT_WRITE_COOLDOWN",
    # Tracking
    "AccessTracker",
    "ComfoClimeAPIError",
    "ComfoClimeConnectionError",
    # Errors
    "ComfoClimeError",
    "ComfoClimeTimeoutError",
    "ComfoClimeValidationError",
    "RateLimiterCache",
    # API decorators and utilities
    "api_get",
    "api_put",
    "validate_byte_value",
    "validate_duration",
    # Validation
    "validate_host",
    "validate_property_path",
]
