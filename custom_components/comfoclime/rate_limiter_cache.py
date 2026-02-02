# rate_limiter_cache.py
"""Rate limiting and caching utilities for ComfoClime API.

This module provides the RateLimiterCache class that handles:
- Rate limiting between API requests
- Write cooldown periods
- Request debouncing
- Telemetry and property caching with TTL
- Write operation priority over read operations
"""

import asyncio
import logging

from .constants import API_DEFAULTS

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
            wait_time = max(
                wait_time, self.min_request_interval - time_since_last_request
            )

        # If this is a read and we recently wrote, wait for cooldown
        # Write operations skip this check - they always have priority
        if not is_write and time_since_last_write < self.write_cooldown:
            wait_time = max(wait_time, self.write_cooldown - time_since_last_write)

        if wait_time > 0:
            _LOGGER.debug(
                "Rate limiting (%s): waiting %.2fs before request",
                "write" if is_write else "read",
                wait_time
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
                try:
                    await pending_task
                except asyncio.CancelledError:
                    pass

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
        keys_to_remove = [
            k for k in self._telemetry_cache.keys() if k.startswith(f"{device_uuid}:")
        ]
        for k in keys_to_remove:
            del self._telemetry_cache[k]

        # Remove property cache entries for this device
        keys_to_remove = [
            k for k in self._property_cache.keys() if k.startswith(f"{device_uuid}:")
        ]
        for k in keys_to_remove:
            del self._property_cache[k]

        _LOGGER.debug(f"Invalidated all cache entries for device {device_uuid}")

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        self._telemetry_cache.clear()
        self._property_cache.clear()
        _LOGGER.debug("Cleared all caches")
