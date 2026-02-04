# api_decorators.py
"""Decorators for unified API method patterns.

These decorators provide a clean, consistent way to define API endpoints
by handling common patterns like locking, rate limiting, session management,
error handling, and write operation priority.

Write Priority Mechanism:
    Write operations (PUT) always have priority over read operations (GET).
    Before a write acquires the lock, it signals its intent. Read operations
    check for pending writes and yield priority to allow writes to proceed first.

Usage:
    @api_get("/system/{uuid}/dashboard", requires_uuid=True, fix_temperatures=True)
    async def async_get_dashboard_data(self, response_data):
        return response_data

    @api_get("/device/{device_uuid}/definition")
    async def async_get_device_definition(self, response_data, device_uuid: str):
        return response_data
"""

import asyncio
import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

# Import temperature fixing function from models module
from .models import fix_signed_temperatures_in_dict

_LOGGER = logging.getLogger(__name__)


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

                    except (TimeoutError, asyncio.CancelledError, aiohttp.ClientError) as e:
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
