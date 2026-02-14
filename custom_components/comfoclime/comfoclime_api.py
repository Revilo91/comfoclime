"""ComfoClime API Client.

This module provides the async API client for communicating with
ComfoClime devices over the local network. The API uses HTTP/JSON
for all communication and includes features like rate limiting,
request caching, retry logic, and connection management.

The API client supports:
    - Dashboard data (temperature, fan speed, season, etc.)
    - Thermal profile management (heating/cooling parameters)
    - Connected device telemetry and properties
    - System monitoring and control
    - Automatic retry with exponential backoff
    - Request caching to reduce load on device
    - Rate limiting to prevent API overload

Example:
    >>> api = ComfoClimeAPI("http://192.168.1.100")
    >>> async with api:
    ...     data = await api.async_get_dashboard_data()
    ...     print(f"Indoor temp: {data['indoorTemperature']}°C")
    ...     await api.async_update_dashboard(fan_speed=2)

Note:
    The API is local and unauthenticated. Ensure your network is secure.
    All temperature values are automatically fixed for signed integer handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .constants import API_DEFAULTS
from .infrastructure import RateLimiterCache, api_get, api_put
from .models import (
    ConnectedDevicesResponse,
    DashboardData,
    DashboardUpdate,
    DashboardUpdateResponse,
    DeviceDefinitionData,
    MonitoringPing,
    PropertyReadResult,
    PropertyReading,
    PropertyWriteRequest,
    PropertyWriteResponse,
    TelemetryReading,
    ThermalProfileData,
    ThermalProfileUpdate,
    ThermalProfileUpdateResponse,
)

_LOGGER = logging.getLogger(__name__)


class ComfoClimeAPI:
    """Async client for ComfoClime device API.

    Provides methods for reading and writing device data with automatic
    rate limiting, caching, retry logic, and session management.

    The API client is responsible only for HTTP communication with the device.
    All data transformation and validation logic is handled by Pydantic models
    in the models.py module.

    Attributes:
        base_url: Base URL of the ComfoClime device
        hass: Home Assistant instance (optional)
        uuid: Device UUID (fetched automatically)
        read_timeout: Timeout for read operations in seconds
        write_timeout: Timeout for write operations in seconds
        max_retries: Maximum number of retries for failed requests
    """

    def __init__(
        self,
        base_url: str,
        hass: HomeAssistant | None = None,
        read_timeout: int = API_DEFAULTS.READ_TIMEOUT,
        write_timeout: int = API_DEFAULTS.WRITE_TIMEOUT,
        cache_ttl: int = int(API_DEFAULTS.CACHE_TTL),
        max_retries: int = API_DEFAULTS.MAX_RETRIES,
        min_request_interval: float = API_DEFAULTS.MIN_REQUEST_INTERVAL,
        write_cooldown: float = API_DEFAULTS.WRITE_COOLDOWN,
        request_debounce: float = API_DEFAULTS.REQUEST_DEBOUNCE,
    ) -> None:
        """Initialize ComfoClime API client.

        Args:
            base_url: Base URL of the ComfoClime device (e.g., "http://192.168.1.100")
            hass: Optional Home Assistant instance for integration
            read_timeout: Timeout for read operations (GET) in seconds
            write_timeout: Timeout for write operations (PUT) in seconds
            cache_ttl: Cache time-to-live in seconds for telemetry/property reads
            max_retries: Maximum number of retries for transient failures
            min_request_interval: Minimum interval between requests in seconds
            write_cooldown: Cooldown period after write operations in seconds
            request_debounce: Debounce time for rapid requests in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.hass = hass
        self.uuid = None
        self._request_lock = asyncio.Lock()
        self._session = None

        # Initialize rate limiter and cache manager
        self._rate_limiter = RateLimiterCache(
            min_request_interval=min_request_interval,
            write_cooldown=write_cooldown,
            request_debounce=request_debounce,
            cache_ttl=cache_ttl,
        )

        # Configurable timeouts and max retries
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.max_retries = max_retries

    # -------------------------------------------------------------------------
    # Rate limiting delegation (used by decorators)
    # -------------------------------------------------------------------------

    async def _wait_for_rate_limit(self, is_write: bool = False) -> None:
        """Wait if necessary to respect rate limits.

        This method enforces minimum request intervals and write cooldowns
        to prevent overloading the device's API.

        Args:
            is_write: True for write operations, False for read operations.
                Write operations have longer cooldown periods.
        """
        await self._rate_limiter.wait_for_rate_limit(is_write=is_write)

    # -------------------------------------------------------------------------
    # Session management
    # -------------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session.

        Returns an existing session if available, or creates a new one.
        The session is reused across all API calls for connection pooling.

        Returns:
            Active aiohttp ClientSession instance.

        Note:
            Timeouts are set per-request, not on the session level,
            to allow different timeouts for read vs write operations.
        """
        if self._session is None or self._session.closed:
            # No timeout on session - timeouts set per-request
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session.

        This should be called when the API client is no longer needed
        to properly clean up network resources.

        Example:
            >>> api = ComfoClimeAPI("http://192.168.1.100")
            >>> try:
            ...     await api.async_get_dashboard_data()
            ... finally:
            ...     await api.close()
        """
        if self._session and not self._session.closed:
            await self._session.close()

    @api_get("/monitoring/ping", skip_lock=True)
    async def _async_get_uuid_internal(self, response_data):
        """Internal method to get device UUID from monitoring endpoint.

        Uses skip_lock=True because it's called from within other api_get
        decorated methods where the lock is already held.

        Args:
            response_data: JSON response from /monitoring/ping endpoint

        Returns:
            Device UUID string or None if not found.

        Note:
            The @api_get decorator handles rate limiting, session management,
            and HTTP request execution.
        """
        self.uuid = response_data.get("uuid")
        return self.uuid

    async def async_get_uuid(self) -> str | None:
        """Get device UUID with lock protection.

        Public method to fetch the system UUID from the device.
        The UUID is cached after the first call.

        Returns:
            Device UUID string or None if not available.

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> uuid = await api.async_get_uuid()
            >>> print(f"Device UUID: {uuid}")
        """
        async with self._request_lock:
            return await self._async_get_uuid_internal()

    @api_get("/monitoring/ping")
    async def async_get_monitoring_ping(self, response_data):
        """Get monitoring/ping data including device uptime.

        Returns comprehensive monitoring information including UUID,
        uptime, and timestamp.

        Args:
            response_data: JSON response from /monitoring/ping endpoint

        Returns:
            MonitoringPing model containing:
                - uuid (str): Device UUID
                - uptime (int): Device uptime in seconds
                - up_time_seconds (int): Device uptime in seconds (alias)
                - timestamp: Current timestamp

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> data = await api.async_get_monitoring_ping()
            >>> hours = data.uptime / 3600
            >>> print(f"Device has been running for {hours:.1f} hours")

        Note:
            The @api_get decorator handles request locking, rate limiting,
            and session management automatically.
        """
        # Parse the raw dict into a validated MonitoringPing model
        # The model handles uptime/up_time_seconds normalization
        return MonitoringPing(**response_data)

    @api_get("/system/{uuid}/dashboard", requires_uuid=True, fix_temperatures=True)
    async def async_get_dashboard_data(self, response_data):
        """Fetch current dashboard data from the device.

        Returns real-time status including temperatures, fan speed,
        operating mode, and system state. All temperature values are
        automatically fixed for signed integer handling.

        Args:
            response_data: JSON response from /system/{uuid}/dashboard endpoint

        Returns:
            DashboardData: Pydantic model containing:
                - indoor_temperature (float): Current indoor temperature in °C
                - outdoor_temperature (float): Current outdoor temperature in °C
                - set_point_temperature (float): Target temperature in °C
                - fan_speed (int): Current fan speed level (0-3)
                - season (int): Season mode (0=transition, 1=heating, 2=cooling)
                - hp_standby (bool): Heat pump standby state
                - temperature_profile (int): Active temperature profile (0-2)
                - status (int): Control mode (0=manual, 1=automatic)

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> data = await api.async_get_dashboard_data()
            >>> if data['season'] == 1:
            ...     print(f"Heating mode: {data['indoorTemperature']}°C")

        Note:
            The @api_get decorator handles request locking, rate limiting,
            UUID retrieval, session management, and temperature value fixing.
        """
        return DashboardData(**response_data)

    @api_get(
        "/system/{uuid}/devices",
        requires_uuid=True,
    )
    async def async_get_connected_devices(self, response_data):
        """Fetch list of connected devices from the system.

        Returns information about all devices connected to the ComfoClime
        system, including heat pumps, sensors, and other peripherals.

        Args:
            response_data: Extracted 'devices' array from response

        Returns:
            ConnectedDevicesResponse model with validated DeviceConfig entries.

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> devices = await api.async_get_connected_devices()
            >>> for device in devices.devices:
            ...     print(f"{device.display_name}: {device.model_type_id}")

        Note:
            Invalid device entries are skipped.
        """
        return ConnectedDevicesResponse.from_api(response_data)

    @api_get(
        "/device/{device_uuid}/definition",
        fix_temperatures=True,
    )
    async def async_get_device_definition(self, response_data, device_uuid: str):
        """Get device definition data.

        Args:
            device_uuid: UUID of the device

        Returns:
            DeviceDefinitionData model containing device definition data

        The @api_get decorator handles:
        - Request locking
        - Rate limiting
        - Session management
        """
        return DeviceDefinitionData(**response_data)

    @api_get("/device/{device_uuid}/telemetry/{telemetry_id}")
    async def _read_telemetry_raw(self, response_data, device_uuid: str, telemetry_id: str):
        """Read raw telemetry data from device.

        The @api_get decorator handles:
        - Request locking
        - Rate limiting
        - Session management
        - Error handling (returns None on error)

        Args:
            device_uuid: UUID of the device
            telemetry_id: Telemetry ID to read

        Returns:
            List of bytes or None on error
        """
        data = response_data.get("data")
        if not isinstance(data, list) or len(data) == 0:
            _LOGGER.debug("Invalid telemetry format for %s", telemetry_id)
            return None
        return data

    async def async_read_telemetry_for_device(
        self,
        device_uuid: str,
        telemetry_id: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> TelemetryReading | None:
        """Read telemetry data for a device with automatic caching.

        Fetches telemetry data from a specific device sensor. Results are
        cached for CACHE_TTL seconds to reduce API load. Supports scaling
        and signed/unsigned interpretation.

        Args:
            device_uuid: UUID of the device
            telemetry_id: Telemetry sensor ID to read
            faktor: Scaling factor to multiply the raw value by (default: 1.0)
            signed: If True, interpret as signed integer (default: True)
            byte_count: Number of bytes to read (1 or 2, auto-detected if None)

        Returns:
            TelemetryReading model with validated data and scaled_value property,
            or None if read failed.

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> # Read temperature sensor (2 bytes, signed, factor 0.1)
            >>> reading = await api.async_read_telemetry_for_device(
            ...     device_uuid="abc123",
            ...     telemetry_id="100",
            ...     faktor=0.1,
            ...     signed=True,
            ...     byte_count=2
            ... )
            >>> if reading:
            ...     print(f"Temperature: {reading.scaled_value}°C")
        """
        # Try to get from cache first
        cache_key = RateLimiterCache.get_cache_key(device_uuid, telemetry_id)
        cached_value = self._rate_limiter.get_telemetry_from_cache(cache_key)
        cached_reading = TelemetryReading.from_cached_value(
            device_uuid=device_uuid,
            telemetry_id=str(telemetry_id),
            cached_value=cached_value,
            faktor=faktor,
            signed=signed,
            byte_count=byte_count,
        )
        if cached_reading is not None:
            return cached_reading

        # Not in cache, fetch from API using decorator
        data = await self._read_telemetry_raw(device_uuid, telemetry_id)

        reading = TelemetryReading.from_raw_bytes(
            device_uuid=device_uuid,
            telemetry_id=str(telemetry_id),
            data=data or [],
            faktor=faktor,
            signed=signed,
            byte_count=byte_count,
        )

        if reading is None:
            return None

        # Store scaled value in cache
        self._rate_limiter.set_telemetry_cache(cache_key, reading.scaled_value)

        return reading

    async def async_read_property_for_device(
        self,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> PropertyReading | None:
        """Read property data for a device with automatic caching.

        Fetches property data from a device. Results are cached for CACHE_TTL
        seconds to reduce API load. Supports numeric properties (1-2 bytes)
        and string properties (3+ bytes).

        Args:
            device_uuid: UUID of the device
            property_path: Property path in format "X/Y/Z" (e.g., "29/1/10")
            faktor: Scaling factor for numeric values (default: 1.0)
            signed: If True, interpret numeric values as signed (default: True)
            byte_count: Number of bytes (1-2 for numeric, 3+ for string)

        Returns:
            PropertyReading model with validated data and scaled_value property,
            or None if failed.

        Raises:
            ValueError: If byte_count is invalid or data size mismatch.
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> # Read numeric property
            >>> reading = await api.async_read_property_for_device(
            ...     device_uuid="abc123",
            ...     property_path="29/1/10",
            ...     byte_count=2,
            ...     faktor=0.1
            ... )
            >>> if reading:
            ...     print(f"Value: {reading.scaled_value}")
        """
        # Try to get from cache first
        cache_key = RateLimiterCache.get_cache_key(device_uuid, property_path)
        cached_value = self._rate_limiter.get_property_from_cache(cache_key)
        cached_reading = PropertyReading.from_cached_value(
            device_uuid=device_uuid,
            path=property_path,
            cached_value=cached_value,
            faktor=faktor,
            signed=signed,
            byte_count=byte_count,
        )
        if cached_reading is not None:
            return cached_reading

        # Not in cache, fetch from API using decorator
        data = await self._read_property_for_device_raw(device_uuid, property_path)

        parsed = PropertyReadResult.from_raw_bytes(
            device_uuid=device_uuid,
            path=property_path,
            data=data or [],
            faktor=faktor,
            signed=signed,
            byte_count=byte_count,
        )

        if parsed.cache_value is not None:
            self._rate_limiter.set_property_cache(cache_key, parsed.cache_value)

        return parsed.reading

    @api_get("/device/{device_uuid}/property/{property_path}")
    async def _read_property_for_device_raw(self, response_data, device_uuid: str, property_path: str) -> None | list:
        """Read raw property data from device.

        The @api_get decorator handles:
        - Request locking
        - Rate limiting
        - Session management
        - Error handling (returns None on error)

        Args:
            device_uuid: UUID of the device
            property_path: Property path (e.g., "29/1/10")

        Returns:
            List of bytes or None on error
        """
        data = response_data.get("data")
        if not isinstance(data, list) or not data:
            _LOGGER.debug("Invalid data format for property %s", property_path)
            return None
        return data

    @api_get(
        "/system/{uuid}/thermalprofile",
        requires_uuid=True,
        fix_temperatures=True,
        on_error={},
    )
    async def async_get_thermal_profile(self, response_data):
        """Fetch thermal profile configuration from the device.

        Returns heating and cooling parameters including temperature profiles,
        season settings, and control modes. All temperature values are
        automatically fixed for signed integer handling.

        Args:
            response_data: JSON response from /system/{uuid}/thermalprofile endpoint

        Returns:
            ThermalProfileData model containing validated thermal profile data.

        Raises:
            aiohttp.ClientError: If connection to device fails (returns {}).
            asyncio.TimeoutError: If request times out (returns {}).

        Example:
            >>> profile = await api.async_get_thermal_profile()
            >>> if profile['season']['season'] == 1:
            ...     comfort = profile['heatingThermalProfileSeasonData']['comfortTemperature']
            ...     print(f"Heating comfort temperature: {comfort}°C")

        Note:
            The @api_get decorator returns {} on any error to prevent
            integration failures.
        """
        return ThermalProfileData(**response_data)

    @api_put("/system/{uuid}/thermalprofile", requires_uuid=True)
    async def _update_thermal_profile(self, **kwargs) -> dict:
        """Update thermal profile settings via API.

        Modern method for thermal profile updates. Only fields that are provided
        will be included in the update payload. Uses ThermalProfileUpdate model
        for payload generation.

        The @api_put decorator handles:
        - UUID retrieval
        - Rate limiting
        - Retry with exponential backoff
        - Error handling

        Supported kwargs:
            - season_status, season_value, heating_threshold_temperature, cooling_threshold_temperature
            - temperature_status, manual_temperature
            - temperature_profile
            - heating_comfort_temperature, heating_knee_point_temperature, heating_reduction_delta_temperature
            - cooling_comfort_temperature, cooling_knee_point_temperature, cooling_temperature_limit

        Returns:
            Payload dict for the decorator to process.
        """
        # Use ThermalProfileUpdate model to build payload
        update = ThermalProfileUpdate(**kwargs)
        return update.to_api_payload()

    @api_put("/system/{uuid}/dashboard", requires_uuid=True, is_dashboard=True)
    async def _async_update_dashboard_internal(self, update: DashboardUpdate) -> dict:
        """Internal decorated method for dashboard updates.

        This method is decorated with @api_put which handles:
        - UUID retrieval
        - Rate limiting
        - Timestamp addition (is_dashboard=True)
        - Retry with exponential backoff
        - Error handling

        Args:
            update: DashboardUpdate model containing the fields to update.

        Returns:
            Payload dict for the decorator to process
        """
        return update.to_api_payload(include_timestamp=False)

    async def async_update_dashboard(self, update: DashboardUpdate) -> DashboardUpdateResponse:
        """Update dashboard settings via API.

        Modern method for dashboard updates. Only fields that are provided
        (not None) will be included in the update payload. Uses DashboardUpdate
        model for payload generation.

        The internal decorator handles:
        - UUID retrieval
        - Rate limiting
        - Timestamp addition
        - Retry with exponential backoff
        - Error handling

        Args:
            update: DashboardUpdate model containing the fields to update.
                   Only non-None fields will be included in the payload.

        Returns:
            DashboardUpdateResponse model with status and response data.

        Example:
            update = DashboardUpdate(set_point_temperature=22.0, status=0)
            response = await api.async_update_dashboard(update)
            print(response.status)
        """
        response_dict = await self._async_update_dashboard_internal(update)
        # Wrap decorator's dict response to DashboardUpdateResponse
        if isinstance(response_dict, dict):
            response_dict.setdefault("status", 200)
            return DashboardUpdateResponse(**response_dict)
        return DashboardUpdateResponse(status=200)

    @api_put("/system/{uuid}/thermalprofile", requires_uuid=True)
    async def _async_update_thermal_profile(self, update: ThermalProfileUpdate | None = None, **kwargs) -> dict:
        """Internal decorated method for thermal profile updates.

        This method is decorated with @api_put which handles:
        - UUID retrieval
        - Rate limiting
        - Retry with exponential backoff
        - Error handling

        Only called from async_update_thermal_profile wrapper to avoid duplication.
        Uses ThermalProfileUpdate model for payload generation.

        Supported kwargs:
            - season_status, season_value, heating_threshold_temperature, cooling_threshold_temperature
            - temperature_status, manual_temperature
            - temperature_profile
            - heating_comfort_temperature, heating_knee_point_temperature, heating_reduction_delta_temperature
            - cooling_comfort_temperature, cooling_knee_point_temperature, cooling_temperature_limit

        Returns:
            Payload dict for the decorator to process.
        """
        # Use ThermalProfileUpdate model to build payload
        if update is None:
            update = ThermalProfileUpdate(**kwargs)
        return update.to_api_payload()

    async def async_update_thermal_profile(
        self,
        updates: dict[str, Any] | None = None,
        update: ThermalProfileUpdate | None = None,
        **kwargs,
    ) -> ThermalProfileUpdateResponse:
        """Update thermal profile settings on the device.

        Provides backward compatibility with legacy dict-based calls while
        supporting modern kwargs-based calls. Only specified fields are updated.

        Supports two calling styles:
            1. Legacy dict-based: await api.async_update_thermal_profile({"season": {"season": 1}})
            2. Modern kwargs-based: await api.async_update_thermal_profile(season_value=1)

        Args:
            updates: Optional dict with nested thermal profile structure (legacy style)
            update: Optional ThermalProfileUpdate model (preferred)
            **kwargs: Modern kwargs style parameters:
                - season_status (int): Season control mode
                - season_value (int): Season (0=transition, 1=heating, 2=cooling)
                - heating_threshold_temperature (float): Temperature threshold for heating
                - cooling_threshold_temperature (float): Temperature threshold for cooling
                - temperature_status (int): Temperature control mode (0=manual, 1=automatic)
                - manual_temperature (float): Manual temperature setpoint
                - temperature_profile (int): Profile (0=comfort, 1=power, 2=eco)
                - heating_comfort_temperature (float): Heating comfort temperature
                - heating_knee_point_temperature (float): Heating knee point
                - heating_reduction_delta_temperature (float): Heating reduction delta
                - cooling_comfort_temperature (float): Cooling comfort temperature
                - cooling_knee_point_temperature (float): Cooling knee point
                - cooling_temperature_limit (float): Cooling temperature limit

        Returns:
            ThermalProfileUpdateResponse model with status and response data.

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> # Modern style - set season to heating
            >>> response = await api.async_update_thermal_profile(season_value=1)
            >>> # Modern style - set heating comfort temperature
            >>> response = await api.async_update_thermal_profile(heating_comfort_temperature=22.0)
            >>> # Legacy style
            >>> response = await api.async_update_thermal_profile({"season": {"season": 1}})
        """
        # If updates dict is provided, convert it to kwargs
        if updates is not None:
            response_dict = await self._convert_dict_to_kwargs_and_update(updates)
        elif update is not None:
            response_dict = await self._async_update_thermal_profile(update=update)
        else:
            response_dict = await self._async_update_thermal_profile(**kwargs)

        # Wrap the decorator's dict response to ThermalProfileUpdateResponse
        if isinstance(response_dict, dict):
            response_dict.setdefault("status", 200)
            return ThermalProfileUpdateResponse(**response_dict)
        return ThermalProfileUpdateResponse(status=200)

    async def _convert_dict_to_kwargs_and_update(self, updates: dict[str, Any]) -> dict:
        """Convert legacy dict-based thermal profile updates to kwargs format.

        Internal method that translates nested dict structure to modern
        kwargs format for calling _async_update_thermal_profile.
        Uses ThermalProfileUpdate.from_dict() for the conversion.

        Args:
            updates: Nested dict structure with thermal profile updates

        Returns:
            Response dict from _async_update_thermal_profile.
        """
        # Use ThermalProfileUpdate model to convert dict to kwargs
        update = ThermalProfileUpdate.from_dict(updates)
        return await self._async_update_thermal_profile(**update.model_dump(exclude_none=True))

    async def async_set_hvac_season(self, season: int, hpStandby: bool = False) -> None:
        """Set HVAC season and heat pump standby state atomically.

        Updates both the season (via thermal profile) and hpStandby state
        (via dashboard) in a single atomic operation. The decorators handle
        all locking internally.

        Args:
            season: Season value (0=transition, 1=heating, 2=cooling)
            hpStandby: Heat pump standby state (False=active, True=standby/off)

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> # Activate heating mode
            >>> await api.async_set_hvac_season(season=1, hpStandby=False)
            >>> # Put system in standby
            >>> await api.async_set_hvac_season(season=0, hpStandby=True)
        """
        # Wrap in timeout to ensure the entire operation completes within reasonable time
        async with asyncio.timeout(self.write_timeout * 2):
            # First update dashboard to set hpStandby
            update = DashboardUpdate(hp_standby=hpStandby)
            await self.async_update_dashboard(update)
            # Then update thermal profile to set season
            if not hpStandby:  # Only set season if device is active
                await self._async_update_thermal_profile(season_value=season)

    @api_put("/device/{device_uuid}/method/{x}/{y}/3")
    async def _set_property_internal(
        self,
        device_uuid: str,
        x: int,
        y: int,
        z: int,
        data: list,
    ):
        """Internal method to build property write payload.

        The @api_put decorator handles:
        - Request locking
        - Rate limiting (write mode)
        - Session management
        - Retry with exponential backoff
        - Error handling

        Args:
            device_uuid: UUID of the device
            x, y: URL path parameters from property_path
            z: First data byte (property ID)
            data: Additional data bytes (value)

        Returns:
            Payload dict for the decorator to process
        """
        return {"data": [z, *data]}

    async def async_set_property_for_device(
        self,
        device_uuid: str | None = None,
        property_path: str | None = None,
        value: float | None = None,
        *,
        byte_count: int | None = None,
        signed: bool = True,
        faktor: float = 1.0,
        request: PropertyWriteRequest | None = None,
    ) -> PropertyWriteResponse:
        """Set property value for a device.

        Writes a property value to a device. The decorator handles all
        locking, rate limiting, and retry logic. After successful write,
        the cache for this device is invalidated.

        Args:
            device_uuid: UUID of the device
            property_path: Property path in format "X/Y/Z" (e.g., "29/1/10")
            value: Value to set (will be scaled by faktor)
            byte_count: Number of bytes (1 or 2)
            signed: If True, encode as signed integer (default: True)
            faktor: Scaling factor to divide value by before encoding (default: 1.0)
            request: Optional PropertyWriteRequest model (preferred)

        Returns:
            PropertyWriteResponse model with status and response data.

        Raises:
            ValueError: If byte_count is not 1 or 2.
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> # Set property to 22.5°C (factor 0.1, so raw value = 225)
            >>> response = await api.async_set_property_for_device(
            ...     device_uuid="abc123",
            ...     property_path="29/1/10",
            ...     value=22.5,
            ...     byte_count=2,
            ...     signed=True,
            ...     faktor=0.1
            ... )
            >>> print(response.status)
        """
        if request is None:
            if device_uuid is None or property_path is None or value is None or byte_count is None:
                raise ValueError("device_uuid, property_path, value, and byte_count are required")
            request = PropertyWriteRequest(
                device_uuid=device_uuid,
                path=property_path,
                value=value,
                byte_count=byte_count,
                signed=signed,
                faktor=faktor,
            )

        x, y, z, data = request.to_wire_data()

        response_dict = await self._set_property_internal(request.device_uuid, x, y, z, data)
        # Invalidate cache for this device after successful write
        self._rate_limiter.invalidate_cache_for_device(request.device_uuid)

        # Wrap the decorator's dict response to PropertyWriteResponse
        if isinstance(response_dict, dict):
            response_dict.setdefault("status", 200)
            return PropertyWriteResponse(**response_dict)
        return PropertyWriteResponse(status=200)

    @api_put("/system/reset")
    async def async_reset_system(self):
        """Trigger a system restart of the ComfoClime device.

        Sends a reset command to reboot the device. The device will
        be unavailable for a short time during the restart process.

        Returns:
            Response from device API.

        Raises:
            aiohttp.ClientError: If connection to device fails.
            asyncio.TimeoutError: If request times out.

        Example:
            >>> await api.async_reset_system()
            >>> # Wait for device to restart
            >>> await asyncio.sleep(10)

        Note:
            The @api_put decorator handles request locking, rate limiting,
            session management, and retry with exponential backoff.
        """
        # No payload needed for reset
        return {}
