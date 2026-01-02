# api_decorators.py
"""Decorators for unified API method patterns.

These decorators provide a clean, consistent way to define API endpoints
by handling common patterns like locking, rate limiting, session management,
and error handling.

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
import logging
from typing import Any, Callable

import aiohttp

_LOGGER = logging.getLogger(__name__)


def api_get(
    url_template: str,
    *,
    requires_uuid: bool = False,
    fix_temperatures: bool = False,
    response_key: str | None = None,
    response_default: Any = None,
):
    """Decorator for GET API endpoints.

    Handles:
    - Request locking
    - Rate limiting
    - Session management
    - UUID retrieval (if requires_uuid=True)
    - Temperature value fixing (if fix_temperatures=True)
    - Response key extraction (if response_key is specified)

    Args:
        url_template: URL template with placeholders (e.g., "/system/{uuid}/dashboard")
                     Supports {uuid} for system UUID and any kwarg names for other params.
        requires_uuid: Whether the endpoint requires the system UUID to be fetched first.
        fix_temperatures: Whether to fix signed temperature values in the response.
        response_key: Optional key to extract from response (e.g., "devices" returns data["devices"]).
        response_default: Default value when response_key is not found (default: None, uses empty dict).

    Example:
        @api_get("/system/{uuid}/dashboard", requires_uuid=True, fix_temperatures=True)
        async def async_get_dashboard_data(self, response_data):
            return response_data
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Import here to avoid circular imports
            from .comfoclime_api import DEFAULT_READ_TIMEOUT
            import inspect

            # Bind positional arguments to their parameter names for URL formatting
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            # Skip 'self' and 'response_data' (first two params)
            url_kwargs = dict(kwargs)
            for i, arg in enumerate(args):
                if i + 2 < len(params):  # +2 to skip 'self' and 'response_data'
                    param_name = params[i + 2]
                    url_kwargs[param_name] = arg

            async with self._request_lock:
                await self._wait_for_rate_limit(is_write=False)

                # Get UUID if required
                if requires_uuid and not self.uuid:
                    await self._async_get_uuid_internal()

                # Build URL from template
                url = self.base_url + url_template.format(uuid=self.uuid, **url_kwargs)

                # Make request
                timeout = aiohttp.ClientTimeout(total=DEFAULT_READ_TIMEOUT)
                session = await self._get_session()
                async with session.get(url, timeout=timeout) as response:
                    response.raise_for_status()
                    data = await response.json()

                # Extract specific key if specified
                if response_key:
                    default = response_default if response_default is not None else {}
                    data = data.get(response_key, default)

                # Fix temperature values if needed
                if fix_temperatures:
                    data = self.fix_signed_temperatures_in_dict(data)

                # Call the original function with the response data
                return await func(self, data, *args, **kwargs)

        return wrapper

    return decorator


def api_get_cached(
    url_template: str,
    *,
    cache_type: str = "telemetry",
):
    """Decorator for GET API endpoints with caching.

    Handles:
    - Cache lookup and storage
    - Request locking
    - Rate limiting
    - Session management

    Args:
        url_template: URL template with placeholders
        cache_type: Cache type to use ("telemetry" or "property")

    The decorated function should accept response_data and return the processed value.
    The function's kwargs should include 'device_uuid' and either 'telemetry_id' or 'property_path'
    for cache key generation.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(
            self,
            device_uuid: str,
            *args,
            **kwargs,
        ):
            # Determine cache key based on cache type
            if cache_type == "telemetry":
                data_id = kwargs.get("telemetry_id", args[0] if args else "")
            else:  # property
                data_id = kwargs.get("property_path", args[0] if args else "")

            cache_key = self._get_cache_key(device_uuid, str(data_id))
            cache_dict = (
                self._telemetry_cache if cache_type == "telemetry" else self._property_cache
            )

            # Check cache first
            cached_value = self._get_from_cache(cache_dict, cache_key)
            if cached_value is not None:
                return cached_value

            # Not in cache, call the decorated function to get data
            result = await func(self, device_uuid, *args, **kwargs)

            # Store in cache if result is not None
            if result is not None:
                self._set_cache(cache_dict, cache_key, result)

            return result

        return wrapper

    return decorator


def api_put_with_retry(
    *,
    is_dashboard: bool = False,
):
    """Decorator for PUT API endpoints with retry logic.

    Handles:
    - Request locking
    - Rate limiting (write mode)
    - Session management
    - Retry with exponential backoff
    - Error handling

    Args:
        is_dashboard: Whether this is a dashboard update (adds timestamp and headers).

    The decorated function should build and return (url, payload) tuple.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Import here to avoid circular imports
            from .comfoclime_api import DEFAULT_WRITE_TIMEOUT, MAX_RETRIES

            # Call the decorated function to get URL and payload
            url, payload = await func(self, *args, **kwargs)

            if not payload:
                _LOGGER.debug("No fields to update (empty payload) - skipping PUT.")
                return {} if is_dashboard else True

            await self._wait_for_rate_limit(is_write=True)

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
            for attempt in range(MAX_RETRIES + 1):
                try:
                    timeout = aiohttp.ClientTimeout(total=DEFAULT_WRITE_TIMEOUT)
                    session = await self._get_session()
                    _LOGGER.debug(
                        f"PUT attempt {attempt + 1}/{MAX_RETRIES + 1}, "
                        f"timeout={DEFAULT_WRITE_TIMEOUT}s, payload={payload}"
                    )
                    async with session.put(
                        url, json=payload, headers=headers, timeout=timeout
                    ) as response:
                        response.raise_for_status()
                        if is_dashboard:
                            try:
                                resp_json = await response.json()
                            except Exception:
                                resp_json = {"text": await response.text()}
                            _LOGGER.debug(f"Update OK response={resp_json}")
                            return resp_json
                        else:
                            _LOGGER.debug(f"Update OK status={response.status}")
                            return response.status == 200

                except (  # noqa: PERF203
                    asyncio.TimeoutError,
                    asyncio.CancelledError,
                    aiohttp.ClientError,
                ) as e:
                    last_exception = e
                    if attempt < MAX_RETRIES:
                        wait_time = 2 ** (attempt + 1)
                        _LOGGER.warning(
                            f"Update failed (attempt {attempt + 1}/{MAX_RETRIES + 1}), "
                            f"retrying in {wait_time}s: {type(e).__name__}: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        _LOGGER.exception(
                            f"Update failed after {MAX_RETRIES + 1} attempts: "
                            f"{type(e).__name__}"
                        )

            if last_exception:
                raise last_exception
            raise RuntimeError("Update failed with unknown error")

        return wrapper

    return decorator


def with_request_lock(func: Callable) -> Callable:
    """Simple decorator to wrap a method with request lock.

    Use this for methods that need locking but don't fit the api_get/api_put patterns.
    """

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with self._request_lock:
            return await func(self, *args, **kwargs)

    return wrapper
