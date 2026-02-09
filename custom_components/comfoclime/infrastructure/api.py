"""API infrastructure for ComfoClime integration.

This module consolidates API-related functionality:
- Rate limiting and caching (RateLimiterCache class)
- API decorators for unified endpoint patterns (api_get, api_put, api_post)
- Write operation priority management
- Request debouncing and cooldown periods
"""

import asyncio
import contextlib
import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from ..constants import API_DEFAULTS
from ..models import fix_signed_temperatures_in_dict

_LOGGER = logging.getLogger(__name__)

# Default configuration values (using APIDefaults for consistency)
DEFAULT_MIN_REQUEST_INTERVAL = API_DEFAULTS.MIN_REQUEST_INTERVAL
DEFAULT_WRITE_COOLDOWN = API_DEFAULTS.WRITE_COOLDOWN
DEFAULT_REQUEST_DEBOUNCE = API_DEFAULTS.REQUEST_DEBOUNCE
DEFAULT_CACHE_TTL = API_DEFAULTS.CACHE_TTL


class RateLimiterCache:
    """Manages rate limiting and caching for API requests.

    This class provides:
    - Rate limiting to prevent overwhelming the API
    - Write priority mechanism to ensure writes always succeed before reads
    - Write cooldown to ensure reads after writes are stable
    - Request debouncing to prevent rapid successive calls
    - TTL-based caching for telemetry and property reads

    Attributes:
        min_request_interval: Minimum seconds between any requests
        write_cooldown: Seconds to wait after write before allowing reads
        request_debounce: Debounce time for rapid successive requests
        cache_ttl: Cache time-to-live in seconds (0 = disabled)
    """

    def __init__(
        self,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
        write_cooldown: float = DEFAULT_WRITE_COOLDOWN,
        request_debounce: float = DEFAULT_REQUEST_DEBOUNCE,
        cache_ttl: float = DEFAULT_CACHE_TTL,
    ):
        """Initialize the RateLimiterCache.

        Args:
            min_request_interval: Minimum seconds between any requests
            write_cooldown: Seconds to wait after write before allowing reads
            request_debounce: Debounce time for rapid successive requests
            cache_ttl: Cache time-to-live in seconds (0 = disabled)
        """
        self.min_request_interval = min_request_interval
        self.write_cooldown = write_cooldown
        self.request_debounce = request_debounce
        self.cache_ttl = cache_ttl

        # Rate limiting state
        self._last_request_time: float = 0.0
        self._last_write_time: float = 0.0
        self._pending_requests: dict[str, asyncio.Task] = {}

        # Write priority mechanism
        # When a write is pending, reads should yield to allow the write to proceed
        self._pending_writes: int = 0

        # Cache storage: {cache_key: (value, timestamp)}
        self._telemetry_cache: dict[str, tuple] = {}
        self._property_cache: dict[str, tuple] = {}

    # -------------------------------------------------------------------------
    # Time utilities
    # -------------------------------------------------------------------------

    def _get_current_time(self) -> float:
        """Get current monotonic time for rate limiting."""
        return asyncio.get_event_loop().time()

    # -------------------------------------------------------------------------
    # Write priority methods
    # -------------------------------------------------------------------------

    def signal_write_pending(self) -> None:
        """Signal that a write operation is pending.

        This should be called before acquiring the lock for a write operation.
        Read operations will check this flag and yield priority to writes.
        """
        self._pending_writes += 1
        _LOGGER.debug("Write pending signaled (count: %d)", self._pending_writes)

    def signal_write_complete(self) -> None:
        """Signal that a write operation has completed.

        This should be called after a write operation is done.
        """
        self._pending_writes = max(0, self._pending_writes - 1)
        _LOGGER.debug("Write complete signaled (count: %d)", self._pending_writes)

    def has_pending_writes(self) -> bool:
        """Check if there are pending write operations.

        Returns:
            True if there are write operations waiting to be processed.
        """
        return self._pending_writes > 0

    async def yield_to_writes(self, max_wait: float = 0.5) -> None:
        """Yield to pending write operations.

        Read operations call this to allow pending writes to proceed first.
        This ensures writes always have priority over reads.

        Args:
            max_wait: Maximum time to wait for writes in seconds (default: 0.5)
        """
        if not self.has_pending_writes():
            return

        _LOGGER.debug("Read yielding to %d pending writes", self._pending_writes)
        # Give writes a short window to acquire the lock
        await asyncio.sleep(min(max_wait, 0.1))

    # -------------------------------------------------------------------------
    # Rate limiting methods
    # -------------------------------------------------------------------------

    async def wait_for_rate_limit(self, is_write: bool = False) -> None:
        """Wait if necessary to respect rate limits.

        For write operations: Only applies minimum request interval.
        For read operations: Also waits for write cooldown period.

        Write operations have priority - they skip write cooldown checks.

        Args:
            is_write: True if this is a write operation (will set cooldown after)
        """
        current_time = self._get_current_time()

        # Calculate minimum wait time
        time_since_last_request = current_time - self._last_request_time
        time_since_last_write = current_time - self._last_write_time

        wait_time = 0.0

        # Ensure minimum interval between requests
        if time_since_last_request < self.min_request_interval:
            wait_time = max(wait_time, self.min_request_interval - time_since_last_request)

        # If this is a read and we recently wrote, wait for cooldown
        # Write operations skip this check - they always have priority
        if not is_write and time_since_last_write < self.write_cooldown:
            wait_time = max(wait_time, self.write_cooldown - time_since_last_write)

        if wait_time > 0:
            _LOGGER.debug(
                "Rate limiting (%s): waiting %.2fs before request",
                "write" if is_write else "read",
                wait_time,
            )
            await asyncio.sleep(wait_time)

        # Update last request time
        self._last_request_time = self._get_current_time()

        # If this is a write, update write time
        if is_write:
            self._last_write_time = self._get_current_time()

    async def debounced_request(
        self,
        key: str,
        coro_factory,
        debounce_time: float | None = None,
    ):
        """Execute a request with debouncing to prevent rapid successive calls.

        If the same request (identified by key) is called again within debounce_time,
        the previous pending request is cancelled and a new one is scheduled.

        Args:
            key: Unique identifier for this request type
            coro_factory: Callable that returns the coroutine to execute
            debounce_time: Time to wait before executing (allows cancellation)

        Returns:
            Result of the request
        """
        if debounce_time is None:
            debounce_time = self.request_debounce

        # Cancel any pending request with the same key
        if key in self._pending_requests:
            pending_task = self._pending_requests[key]
            if not pending_task.done():
                pending_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await pending_task

        # Wait for debounce time
        await asyncio.sleep(debounce_time)

        # Execute the actual request
        return await coro_factory()

    # -------------------------------------------------------------------------
    # Cache utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def get_cache_key(device_uuid: str, data_id: str) -> str:
        """Generate a cache key from device UUID and data ID.

        Args:
            device_uuid: UUID of the device
            data_id: Telemetry ID or property path

        Returns:
            Cache key string
        """
        return f"{device_uuid}:{data_id}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if a cached value is still valid.

        Args:
            timestamp: Timestamp when the value was cached

        Returns:
            True if cache is still valid, False otherwise
        """
        if self.cache_ttl == 0:
            return False  # Cache disabled
        return (self._get_current_time() - timestamp) < self.cache_ttl

    # -------------------------------------------------------------------------
    # Telemetry cache methods
    # -------------------------------------------------------------------------

    def get_telemetry_from_cache(self, cache_key: str):
        """Get a telemetry value from cache if it's still valid.

        Args:
            cache_key: Cache key (use get_cache_key to generate)

        Returns:
            Cached value or None if not found/expired
        """
        if cache_key in self._telemetry_cache:
            value, timestamp = self._telemetry_cache[cache_key]
            if self._is_cache_valid(timestamp):
                _LOGGER.debug(f"Telemetry cache hit for {cache_key}")
                return value
            # Cache expired, remove it
            del self._telemetry_cache[cache_key]
        return None

    def set_telemetry_cache(self, cache_key: str, value) -> None:
        """Store a telemetry value in cache with current timestamp.

        Args:
            cache_key: Cache key (use get_cache_key to generate)
            value: Value to cache
        """
        self._telemetry_cache[cache_key] = (value, self._get_current_time())

    # -------------------------------------------------------------------------
    # Property cache methods
    # -------------------------------------------------------------------------

    def get_property_from_cache(self, cache_key: str):
        """Get a property value from cache if it's still valid.

        Args:
            cache_key: Cache key (use get_cache_key to generate)

        Returns:
            Cached value or None if not found/expired
        """
        if cache_key in self._property_cache:
            value, timestamp = self._property_cache[cache_key]
            if self._is_cache_valid(timestamp):
                _LOGGER.debug(f"Property cache hit for {cache_key}")
                return value
            # Cache expired, remove it
            del self._property_cache[cache_key]
        return None

    def set_property_cache(self, cache_key: str, value) -> None:
        """Store a property value in cache with current timestamp.

        Args:
            cache_key: Cache key (use get_cache_key to generate)
            value: Value to cache
        """
        self._property_cache[cache_key] = (value, self._get_current_time())

    # -------------------------------------------------------------------------
    # Cache invalidation
    # -------------------------------------------------------------------------

    def invalidate_cache_for_device(self, device_uuid: str) -> None:
        """Invalidate all cache entries for a specific device.

        Args:
            device_uuid: UUID of the device
        """
        # Remove telemetry cache entries for this device
        keys_to_remove = [k for k in self._telemetry_cache if k.startswith(f"{device_uuid}:")]
        for k in keys_to_remove:
            del self._telemetry_cache[k]

        # Remove property cache entries for this device
        keys_to_remove = [k for k in self._property_cache if k.startswith(f"{device_uuid}:")]
        for k in keys_to_remove:
            del self._property_cache[k]

        _LOGGER.debug(f"Invalidated all cache entries for device {device_uuid}")

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        self._telemetry_cache.clear()
        self._property_cache.clear()
        _LOGGER.debug("Cleared all caches")


# ============================================================================
# API Decorators
# ============================================================================
# The following section provides decorators for unified API method patterns,
# handling common patterns like locking, rate limiting, session management,
# error handling, and write operation priority.
#
# Write Priority Mechanism:
#     Write operations (PUT) always have priority over read operations (GET).
#     Before a write acquires the lock, it signals its intent. Read operations
#     check for pending writes and yield priority to allow writes to proceed first.
#
# Usage:
#     @api_get("/system/{uuid}/dashboard", requires_uuid=True, fix_temperatures=True)
#     async def async_get_dashboard_data(self, response_data):
#         return response_data
#
#     @api_get("/device/{device_uuid}/definition")
#     async def async_get_device_definition(self, response_data, device_uuid: str):
#         return response_data
# ============================================================================


def api_get(
    url_template: str,
    *,
    requires_uuid: bool = False,
    fix_temperatures: bool = False,
    response_key: str | None = None,
    response_default: Any = None,
    on_error: Any = None,
    skip_lock: bool = False,
):
    """Decorator for GET API endpoints.

    Handles:
    - Request locking (unless skip_lock=True)
    - Rate limiting
    - Session management
    - UUID retrieval (if requires_uuid=True)
    - Temperature value fixing (if fix_temperatures=True)
    - Response key extraction (if response_key is specified)
    - Error handling (if on_error is specified)
    - Yielding to pending write operations (write priority)

    Args:
        url_template: URL template with placeholders (e.g., "/system/{uuid}/dashboard")
                     Supports {uuid} for system UUID and any kwarg names for other params.
        requires_uuid: Whether the endpoint requires the system UUID to be fetched first.
        fix_temperatures: Whether to fix signed temperature values in the response.
        response_key: Optional key to extract from response (e.g., "devices" returns data["devices"]).
        response_default: Default value when response_key is not found (default: None, uses empty dict).
        on_error: Value to return on error instead of raising exception (e.g., {} for empty dict).
        skip_lock: Skip lock acquisition (for methods called from within locked context).

    Example:
        @api_get("/system/{uuid}/dashboard", requires_uuid=True, fix_temperatures=True)
        async def async_get_dashboard_data(self, response_data):
            return response_data

        @api_get("/monitoring/ping", skip_lock=True)
        async def _async_get_uuid_internal(self, response_data):
            # Called from within api_get decorated methods, lock already held
            return response_data
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Bind positional arguments to their parameter names for URL formatting
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            # Skip 'self' and 'response_data' (first two params)
            url_kwargs = dict(kwargs)
            for i, arg in enumerate(args):
                if i + 2 < len(params):  # +2 to skip 'self' and 'response_data'
                    param_name = params[i + 2]
                    url_kwargs[param_name] = arg

            async def _execute():
                """Execute the API call (with or without lock)."""
                await self._wait_for_rate_limit(is_write=False)

                # Get UUID if required
                if requires_uuid and not self.uuid:
                    await self._async_get_uuid_internal()

                # Build URL from template
                url = self.base_url + url_template.format(uuid=self.uuid, **url_kwargs)

                # Make request
                timeout = aiohttp.ClientTimeout(total=self.read_timeout)
                session = await self._get_session()
                async with session.get(url, timeout=timeout) as response:
                    response.raise_for_status()
                    data = await response.json()

                _LOGGER.debug("API GET %s returned data: %s", url, data)

                # Extract specific key if specified
                if response_key:
                    default = response_default if response_default is not None else {}
                    data = data.get(response_key, default)

                # Fix temperature values if needed
                if fix_temperatures:
                    data = fix_signed_temperatures_in_dict(data)

                # Call the original function with the response data and remaining args/kwargs
                return await func(self, data, *args, **kwargs)

            try:
                if skip_lock:
                    # Execute without acquiring lock (lock already held by caller)
                    return await _execute()

                # Yield to pending writes before trying to acquire lock
                # This ensures write operations always have priority
                await self._rate_limiter.yield_to_writes()

                # Execute with lock acquisition
                async with self._request_lock:
                    return await _execute()

            except (TimeoutError, aiohttp.ClientError) as e:
                if on_error is not None:
                    _LOGGER.warning(f"Error fetching {url_template}: {e}")
                    return on_error
                raise

        return wrapper

    return decorator


def api_put(
    url_template: str,
    *,
    requires_uuid: bool = False,
    is_dashboard: bool = False,
    skip_lock: bool = False,
):
    """Decorator for PUT API endpoints.

    Handles:
    - Write priority signaling (writes always have priority over reads)
    - Request locking (unless skip_lock=True)
    - Rate limiting (write mode)
    - Session management
    - UUID retrieval (if requires_uuid=True)
    - Retry with exponential backoff
    - Timestamp addition (if is_dashboard=True)
    - Error handling

    Args:
        url_template: URL template with placeholders (e.g., "/system/{uuid}/dashboard")
                     Supports {uuid} for system UUID and any kwarg names for other params.
        requires_uuid: Whether the endpoint requires the system UUID to be fetched first.
        is_dashboard: Whether this is a dashboard update (adds timestamp and headers).
        skip_lock: Skip lock acquisition (for methods called from within locked context).

    The decorated function should build and return the payload dict.
    The URL is built from the template.

    Example:
        @api_put("/system/{uuid}/dashboard", requires_uuid=True, is_dashboard=True)
        async def _update_dashboard(self, **kwargs) -> dict:
            payload = {...}
            return payload

        @api_put("/device/{device_uuid}/method/{x}/{y}/3")
        async def _set_property(self, device_uuid: str, x: int, y: int, **kwargs) -> dict:
            payload = {...}
            return payload
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Bind positional arguments to their parameter names for URL formatting
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            # Skip 'self' (first param)
            url_kwargs = dict(kwargs)
            for i, arg in enumerate(args):
                if i + 1 < len(params):  # +1 to skip 'self'
                    param_name = params[i + 1]
                    url_kwargs[param_name] = arg

            async def _execute():
                """Execute the API call (with or without lock)."""
                await self._wait_for_rate_limit(is_write=True)

                # Get UUID if required
                if requires_uuid and not self.uuid:
                    await self._async_get_uuid_internal()

                # Build URL from template
                url = self.base_url + url_template.format(uuid=self.uuid, **url_kwargs)

                # Call the decorated function to get payload
                payload = await func(self, *args, **kwargs)

                if not payload:
                    _LOGGER.debug("No fields to update (empty payload) - skipping PUT.")
                    return {} if is_dashboard else True

                # Prepare headers and add timestamp for dashboard updates
                headers = None
                if is_dashboard:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo

                    if not self.hass:
                        raise ValueError("hass instance required for timestamp generation")
                    tz = ZoneInfo(self.hass.config.time_zone)
                    payload["timestamp"] = datetime.now(tz).isoformat()
                    headers = {"content-type": "application/json; charset=utf-8"}

                # Retry logic
                last_exception = None
                for attempt in range(self.max_retries + 1):
                    try:
                        timeout = aiohttp.ClientTimeout(total=self.write_timeout)
                        session = await self._get_session()
                        _LOGGER.debug(
                            "PUT attempt %d/%d, timeout=%ds, payload=%s",
                            attempt + 1,
                            self.max_retries + 1,
                            self.write_timeout,
                            payload,
                        )
                        async with session.put(url, json=payload, headers=headers, timeout=timeout) as response:
                            response.raise_for_status()
                            if is_dashboard:
                                try:
                                    resp_json = await response.json()
                                except (aiohttp.ContentTypeError, ValueError):
                                    resp_json = {"text": await response.text()}
                                _LOGGER.debug("Update OK response=%s", resp_json)
                                return resp_json
                            _LOGGER.debug("Update OK status=%d", response.status)
                            return response.status == 200

                    except asyncio.CancelledError:
                        # CancelledError should not be retried - it means the task was cancelled
                        # Re-raise immediately to propagate cancellation
                        raise
                    except (TimeoutError, aiohttp.ClientError) as e:
                        last_exception = e
                        if attempt < self.max_retries:
                            wait_time = 2 ** (attempt + 1)
                            _LOGGER.warning(
                                "Update failed (attempt %d/%d), retrying in %ds: %s: %s",
                                attempt + 1,
                                self.max_retries + 1,
                                wait_time,
                                type(e).__name__,
                                e,
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            _LOGGER.exception(
                                "Update failed after %d attempts: %s",
                                self.max_retries + 1,
                                type(e).__name__,
                            )

                if last_exception:
                    raise last_exception
                raise RuntimeError("Update failed with unknown error")

            if skip_lock:
                # Execute without acquiring lock (lock already held by caller)
                return await _execute()

            # Signal write intent before acquiring lock
            # This allows read operations to yield priority to this write
            self._rate_limiter.signal_write_pending()
            try:
                # Execute with lock acquisition
                async with self._request_lock:
                    return await _execute()
            finally:
                # Signal write complete
                self._rate_limiter.signal_write_complete()

        return wrapper

    return decorator
