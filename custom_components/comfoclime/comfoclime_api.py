# comfoclime_api.py
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

from .api_decorators import api_get, api_put, with_request_lock

_LOGGER = logging.getLogger(__name__)

# Rate limiting configuration (can be overridden via constructor)
DEFAULT_MIN_REQUEST_INTERVAL = 0.1  # Minimum seconds between any requests
DEFAULT_WRITE_COOLDOWN = 2.0  # Seconds to wait after a write operation before allowing reads
DEFAULT_REQUEST_DEBOUNCE = 0.3  # Debounce time for rapid successive requests

# Default timeout configuration (can be overridden via constructor)
DEFAULT_READ_TIMEOUT = 10  # Timeout for read operations (GET)
DEFAULT_WRITE_TIMEOUT = (
    30  # Timeout for write operations (PUT) - longer for dashboard updates
)
DEFAULT_CACHE_TTL = 30.0  # Cache time-to-live in seconds
DEFAULT_MAX_RETRIES = 3  # Number of retries for transient failures


class ComfoClimeAPI:
    # Mapping von kwargs zu payload-Struktur (class-level constant)
    FIELD_MAPPING = {
        # season fields
        "season_status": ("season", "status"),
        "season_value": ("season", "season"),
        "heating_threshold_temperature": ("season", "heatingThresholdTemperature"),
        "cooling_threshold_temperature": ("season", "coolingThresholdTemperature"),
        # temperature fields
        "temperature_status": ("temperature", "status"),
        "manual_temperature": ("temperature", "manualTemperature"),
        # top-level fields
        "temperature_profile": ("temperatureProfile", None),
        # heating profile fields
        "heating_comfort_temperature": (
            "heatingThermalProfileSeasonData",
            "comfortTemperature",
        ),
        "heating_knee_point_temperature": (
            "heatingThermalProfileSeasonData",
            "kneePointTemperature",
        ),
        "heating_reduction_delta_temperature": (
            "heatingThermalProfileSeasonData",
            "reductionDeltaTemperature",
        ),
        # cooling profile fields
        "cooling_comfort_temperature": (
            "coolingThermalProfileSeasonData",
            "comfortTemperature",
        ),
        "cooling_knee_point_temperature": (
            "coolingThermalProfileSeasonData",
            "kneePointTemperature",
        ),
        "cooling_temperature_limit": (
            "coolingThermalProfileSeasonData",
            "temperatureLimit",
        ),
    }

    def __init__(
        self,
        base_url,
        hass=None,
        read_timeout=DEFAULT_READ_TIMEOUT,
        write_timeout=DEFAULT_WRITE_TIMEOUT,
        cache_ttl=DEFAULT_CACHE_TTL,
        max_retries=DEFAULT_MAX_RETRIES,
        min_request_interval=DEFAULT_MIN_REQUEST_INTERVAL,
        write_cooldown=DEFAULT_WRITE_COOLDOWN,
        request_debounce=DEFAULT_REQUEST_DEBOUNCE,
    ):
        self.base_url = base_url.rstrip("/")
        self.hass = hass
        self.uuid = None
        self._request_lock = asyncio.Lock()
        self._session = None
        self._last_request_time = 0.0
        self._last_write_time = 0.0
        self._pending_requests: dict[str, asyncio.Task] = {}
        # Cache for telemetry and property reads: {cache_key: (value, timestamp)}
        self._telemetry_cache: dict[str, tuple] = {}
        self._property_cache: dict[str, tuple] = {}
        # Configurable timeouts, cache TTL, max retries, and rate limiting
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.min_request_interval = min_request_interval
        self.write_cooldown = write_cooldown
        self.request_debounce = request_debounce

    def _get_current_time(self) -> float:
        """Get current monotonic time for rate limiting."""
        return asyncio.get_event_loop().time()

    def _get_cache_key(self, device_uuid: str, data_id: str) -> str:
        """Generate a cache key from device UUID and data ID."""
        return f"{device_uuid}:{data_id}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if a cached value is still valid."""
        if self.cache_ttl == 0:
            return False  # Cache disabled
        return (self._get_current_time() - timestamp) < self.cache_ttl

    def _get_from_cache(self, cache_dict: dict, cache_key: str):
        """Get a value from cache if it's still valid."""
        if cache_key in cache_dict:
            value, timestamp = cache_dict[cache_key]
            if self._is_cache_valid(timestamp):
                _LOGGER.debug(f"Cache hit for {cache_key}")
                return value
            # Cache expired, remove it
            del cache_dict[cache_key]
        return None

    def _set_cache(self, cache_dict: dict, cache_key: str, value):
        """Store a value in cache with current timestamp."""
        cache_dict[cache_key] = (value, self._get_current_time())

    def _invalidate_cache_for_device(self, device_uuid: str):
        """Invalidate all cache entries for a specific device."""
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

    async def _wait_for_rate_limit(self, is_write: bool = False):
        """Wait if necessary to respect rate limits.

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
        if not is_write and time_since_last_write < self.write_cooldown:
            wait_time = max(wait_time, self.write_cooldown - time_since_last_write)

        if wait_time > 0:
            _LOGGER.debug(f"Rate limiting: waiting {wait_time:.2f}s before request")
            await asyncio.sleep(wait_time)

        # Update last request time
        self._last_request_time = self._get_current_time()

        # If this is a write, update write time
        if is_write:
            self._last_write_time = self._get_current_time()

    async def _debounced_request(
        self, key: str, coro_factory, debounce_time: float = None
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

    async def _get_session(self):
        """Get or create aiohttp session.

        Note: Timeouts are set per-request, not on the session level,
        to allow different timeouts for read vs write operations.
        """
        if self._session is None or self._session.closed:
            # No timeout on session - timeouts set per-request
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @staticmethod
    def bytes_to_signed_int(
        data: list, byte_count: int = None, signed: bool = True
    ) -> int:
        """Convert raw bytes to a signed integer value.

        Args:
            data: List of bytes (integers 0-255)
            byte_count: Number of bytes to read. If None calculate from data

        Returns:
            Signed integer value

        Raises:
            ValueError: If byte_count is not 1 or 2
        """
        if not isinstance(data, list):
            raise ValueError("'data' is not a list")

        if byte_count is None:
            byte_count = len(data)

        if byte_count not in (1, 2):
            raise ValueError(f"Unsupported byte count: {byte_count}")

        return int.from_bytes(data[:byte_count], byteorder="little", signed=signed)

    @staticmethod
    def signed_int_to_bytes(
        data: int, byte_count: int = 2, signed: bool = False
    ) -> list:
        """Convert a signed integer to a list of bytes.

        Args:
            data: Signed integer value
            byte_count: Number of bytes to convert to (1 or 2)

        Returns:
            List of bytes (integers 0-255)

        Raises:
            ValueError: If byte_count is not 1 or 2
        """
        if byte_count not in (1, 2):
            raise ValueError(f"Unsupported byte count: {byte_count}")

        return list(data.to_bytes(byte_count, byteorder="little", signed=signed))

    @staticmethod
    def fix_signed_temperature(api_value: float) -> float:
        """Fix temperature value by converting through signed 16-bit integer.

        This handles the case where temperature values need to be interpreted
        as signed 16-bit integers (scaled by 10).

        Args:
            api_value: Temperature value from API

        Returns:
            Corrected temperature value
        """
        raw_value = int(api_value * 10)
        # Convert to signed 16-bit using Python's built-in byte conversion
        unsigned_value = raw_value & 0xFFFF
        bytes_data = ComfoClimeAPI.signed_int_to_bytes(unsigned_value, 2)
        signed_value = ComfoClimeAPI.bytes_to_signed_int(bytes_data)
        return signed_value / 10.0

    @staticmethod
    def fix_signed_temperatures_in_dict(data: dict) -> dict:
        """Recursively fix signed temperature values in a dictionary.

        Applies fix_signed_temperature to all keys containing "Temperature"
        in both flat and nested dictionary structures.

        Args:
            data: Dictionary potentially containing temperature values

        Returns:
            Dictionary with fixed temperature values
        """
        for key in list(data.keys()):
            val = data[key]
            if isinstance(val, dict):
                # Recursively process nested dictionaries
                data[key] = ComfoClimeAPI.fix_signed_temperatures_in_dict(val)
            elif "Temperature" in key and val is not None and isinstance(val, (int, float)):
                data[key] = ComfoClimeAPI.fix_signed_temperature(val)
        return data

    async def _async_get_uuid_internal(self):
        """Internal method to get UUID.
        
        This method is called from within api_get decorators where the lock
        is already held, so it must not use the decorator to avoid deadlock.
        
        It performs a simple GET to /monitoring/ping to fetch the system UUID.
        """
        url = self.base_url + "/monitoring/ping"
        timeout = aiohttp.ClientTimeout(total=self.read_timeout)
        session = await self._get_session()
        
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            data = await response.json()
            self.uuid = data.get("uuid")
            return self.uuid

    @with_request_lock
    async def async_get_uuid(self):
        """Get UUID with lock protection.
        
        Public method to fetch the system UUID. Acquires the lock and
        respects rate limiting.
        """
        await self._wait_for_rate_limit(is_write=False)
        return await self._async_get_uuid_internal()

    @api_get("/system/{uuid}/dashboard", requires_uuid=True, fix_temperatures=True)
    async def async_get_dashboard_data(self, response_data):
        """Fetch dashboard data from the API.

        The @api_get decorator handles:
        - Request locking
        - Rate limiting
        - UUID retrieval
        - Session management
        - Temperature value fixing
        """
        return response_data

    @api_get("/system/{uuid}/devices", requires_uuid=True, response_key="devices", response_default=[])
    async def async_get_connected_devices(self, response_data):
        """Fetch connected devices from the API.

        The @api_get decorator handles:
        - Request locking
        - Rate limiting
        - UUID retrieval
        - Session management
        - Extracting 'devices' key from response (returns [] if not found)
        """
        return response_data

    @api_get("/device/{device_uuid}/definition")
    async def async_get_device_definition(self, response_data, device_uuid: str):
        """Get device definition data.

        Args:
            device_uuid: UUID of the device

        Returns:
            Dictionary containing device definition data

        The @api_get decorator handles:
        - Request locking
        - Rate limiting
        - Session management
        """
        return response_data

    @api_get("/device/{device_uuid}/telemetry/{telemetry_id}", on_error=None)
    async def _read_telemetry_raw(
        self, response_data, device_uuid: str, telemetry_id: str
    ):
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
            _LOGGER.debug(f"Ungültiges Telemetrie-Format für {telemetry_id}")
            return None
        return data
    
    async def async_read_telemetry_for_device(
        self,
        device_uuid: str,
        telemetry_id: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ):
        """Read telemetry for a device with caching.

        Args:
            device_uuid: UUID of the device
            telemetry_id: Telemetry ID to read
            faktor: Factor to multiply the value by
            signed: Whether the value is signed
            byte_count: Number of bytes to read

        Returns:
            The telemetry value (or None if failed)
        """
        # Try to get from cache first
        cache_key = self._get_cache_key(device_uuid, telemetry_id)
        cached_value = self._get_from_cache(self._telemetry_cache, cache_key)
        if cached_value is not None:
            return cached_value

        # Not in cache, fetch from API using decorator
        data = await self._read_telemetry_raw(device_uuid, telemetry_id)
        
        if data is None:
            return None

        value = self.bytes_to_signed_int(data, byte_count, signed)
        result = value * faktor

        # Store in cache
        self._set_cache(self._telemetry_cache, cache_key, result)

        return result

    async def async_read_property_for_device(
        self,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ):
        """Read property for a device with caching.

        Args:
            device_uuid: UUID of the device
            property_path: Property path to read
            faktor: Factor to multiply numeric values by
            signed: Whether the value is signed
            byte_count: Number of bytes to read

        Returns:
            The property value (or None if failed)
        """
        # Try to get from cache first
        cache_key = self._get_cache_key(device_uuid, property_path)
        cached_value = self._get_from_cache(self._property_cache, cache_key)
        if cached_value is not None:
            return cached_value

        # Not in cache, fetch from API using decorator
        data = await self._read_property_for_device_raw(device_uuid, property_path)

        # Wenn data leer/None ist, können wir nicht fortfahren
        if not data:
            return None

        if byte_count in (1, 2):
            value = self.bytes_to_signed_int(data, byte_count, signed)
            result = value * faktor
        elif byte_count and byte_count > 2:
            if len(data) != byte_count:
                raise ValueError(
                    f"Unerwartete Byte-Anzahl: erwartet {byte_count}, erhalten {len(data)}"
                )
            result = "".join(chr(byte) for byte in data if byte != 0)
        else:
            raise ValueError(f"Nicht unterstützte Byte-Anzahl: {byte_count}")

        # Store in cache
        self._set_cache(self._property_cache, cache_key, result)

        return result

    @api_get("/device/{device_uuid}/property/{property_path}", on_error=None)
    async def _read_property_for_device_raw(
        self, response_data, device_uuid: str, property_path: str
    ) -> None | list:
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
            _LOGGER.debug(f"Ungültiges Datenformat für Property {property_path}")
            return None
        return data

    @api_get("/system/{uuid}/thermalprofile", requires_uuid=True, fix_temperatures=True, on_error={})
    async def async_get_thermal_profile(self, response_data):
        """Fetch thermal profile data from the API.

        The @api_get decorator handles:
        - Request locking
        - Rate limiting
        - UUID retrieval
        - Session management
        - Temperature value fixing
        - Error handling (returns {} on error)
        """
        return response_data

    @api_put("/system/{uuid}/thermalprofile", requires_uuid=True)
    async def _update_thermal_profile(self, **kwargs) -> dict:
        """Update thermal profile settings via API.

        Modern method for thermal profile updates. Only fields that are provided
        will be included in the update payload.

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
        # Use class-level FIELD_MAPPING
        field_mapping = self.FIELD_MAPPING

        # Dynamically build payload
        payload: dict = {}

        for param_name, value in kwargs.items():
            if value is None or param_name not in field_mapping:
                continue

            section, key = field_mapping[param_name]

            if key is None:
                # Top-level field
                payload[section] = value
            else:
                # Nested field
                if section not in payload:
                    payload[section] = {}
                payload[section][key] = value

        return payload

    @api_put("/system/{uuid}/dashboard", requires_uuid=True, is_dashboard=True)
    async def _update_dashboard(
        self,
        set_point_temperature: float | None = None,
        fan_speed: int | None = None,
        season: int | None = None,
        hpStandby: bool | None = None,
        schedule: int | None = None,
        temperature_profile: int | None = None,
        season_profile: int | None = None,
        status: int | None = None,
        scenario: int | None = None,
        scenario_time_left: int | None = None,
        scenario_start_delay: int | None = None,
    ) -> dict:
        """Update dashboard settings via API.

        Modern method for dashboard updates. Only fields that are provided
        (not None) will be included in the update payload.

        The @api_put decorator handles:
        - UUID retrieval
        - Rate limiting
        - Timestamp addition (is_dashboard=True)
        - Retry with exponential backoff
        - Error handling

        Args:
            set_point_temperature: Target temperature (°C) - activates manual mode
            fan_speed: Fan speed (0-3)
            season: Season value (0=transition, 1=heating, 2=cooling)
            hpStandby: Heat pump standby state (True=standby/off, False=active)
            schedule: Schedule mode
            temperature_profile: Temperature profile/preset (0=comfort, 1=boost, 2=eco)
            season_profile: Season profile/preset (0=comfort, 1=boost, 2=eco)
            status: Temperature control mode (0=manual, 1=automatic)
            scenario: Scenario mode (4=Kochen, 5=Party, 7=Urlaub, 8=Boost)
            scenario_time_left: Duration for scenario in seconds (e.g., 1800 for 30min)
            scenario_start_delay: Start delay for scenario in seconds (optional)

        Returns:
            Payload dict for the decorator to process.
        """
        # Dynamically build payload; only include keys explicitly provided.
        payload: dict = {}
        if set_point_temperature is not None:
            payload["setPointTemperature"] = set_point_temperature
        if fan_speed is not None:
            payload["fanSpeed"] = fan_speed
        if season is not None:
            payload["season"] = season
        if schedule is not None:
            payload["schedule"] = schedule
        if temperature_profile is not None:
            payload["temperatureProfile"] = temperature_profile
        if season_profile is not None:
            payload["seasonProfile"] = season_profile
        if status is not None:
            payload["status"] = status
        if hpStandby is not None:
            payload["hpStandby"] = hpStandby
        if scenario is not None:
            payload["scenario"] = scenario
        if scenario_time_left is not None:
            payload["scenarioTimeLeft"] = scenario_time_left
        if scenario_start_delay is not None:
            payload["scenarioStartDelay"] = scenario_start_delay

        return payload

    async def async_update_dashboard(self, **kwargs):
        """Async wrapper for update_dashboard method."""
        async with self._request_lock:
            return await self._update_dashboard(**kwargs)

    async def async_update_thermal_profile(self, updates: dict | None = None, **kwargs):
        """Async wrapper for update_thermal_profile method.

        Supports two calling styles:
        1. Legacy dict-based: async_update_thermal_profile({"season": {"season": 1}})
        2. Modern kwargs-based: async_update_thermal_profile(season_value=1)
        """
        async with self._request_lock:
            # If updates dict is provided, convert it to kwargs
            if updates is not None:
                return await self._convert_dict_to_kwargs_and_update(updates)
            return await self._update_thermal_profile(**kwargs)

    async def _convert_dict_to_kwargs_and_update(self, updates: dict) -> bool:
        """Convert legacy dict-based updates to kwargs and call _update_thermal_profile."""
        # Mapping von nested dict-Struktur zu kwargs
        conversion_map = {
            ("season", "status"): "season_status",
            ("season", "season"): "season_value",
            ("season", "heatingThresholdTemperature"): "heating_threshold_temperature",
            ("season", "coolingThresholdTemperature"): "cooling_threshold_temperature",
            ("temperature", "status"): "temperature_status",
            ("temperature", "manualTemperature"): "manual_temperature",
            ("temperatureProfile",): "temperature_profile",
            (
                "heatingThermalProfileSeasonData",
                "comfortTemperature",
            ): "heating_comfort_temperature",
            (
                "heatingThermalProfileSeasonData",
                "kneePointTemperature",
            ): "heating_knee_point_temperature",
            (
                "heatingThermalProfileSeasonData",
                "reductionDeltaTemperature",
            ): "heating_reduction_delta_temperature",
            (
                "coolingThermalProfileSeasonData",
                "comfortTemperature",
            ): "cooling_comfort_temperature",
            (
                "coolingThermalProfileSeasonData",
                "kneePointTemperature",
            ): "cooling_knee_point_temperature",
            (
                "coolingThermalProfileSeasonData",
                "temperatureLimit",
            ): "cooling_temperature_limit",
        }

        kwargs = {}

        # Process nested dictionaries
        for section, value in updates.items():
            if isinstance(value, dict):
                for key, field_value in value.items():
                    mapping_key = (section, key)
                    if mapping_key in conversion_map:
                        kwargs[conversion_map[mapping_key]] = field_value
            else:
                # Top-level field
                mapping_key = (section,)
                if mapping_key in conversion_map:
                    kwargs[conversion_map[mapping_key]] = value

        return await self._update_thermal_profile(**kwargs)

    async def async_set_hvac_season(self, season: int, hpStandby: bool = False):
        """Set HVAC season and standby state in a single atomic operation.

        This method updates both the season (via thermal profile) and hpStandby
        (via dashboard) in a single lock to prevent race conditions.

        Args:
            season: Season value (0=transition, 1=heating, 2=cooling)
            hpStandby: Heat pump standby state (False=active, True=standby/off)
        """
        async with self._request_lock:
            # First update dashboard to set hpStandby
            await self._update_dashboard(hpStandby=hpStandby)
            # Then update thermal profile to set season
            if not hpStandby:  # Only set season if device is active
                await self._update_thermal_profile(season_value=season)

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
        return {"data": [z] + data}
    
    async def async_set_property_for_device(
        self,
        device_uuid: str,
        property_path: str,
        value: float,
        *,
        byte_count: int,
        signed: bool = True,
        faktor: float = 1.0,
    ):
        """Set property for a device.
        
        Args:
            device_uuid: UUID of the device
            property_path: Property path in format "x/y/z"
            value: Value to set
            byte_count: Number of bytes (1 or 2)
            signed: Whether the value is signed
            faktor: Factor to divide the value by before encoding
            
        Raises:
            ValueError: If byte_count is not 1 or 2
        """
        if byte_count not in (1, 2):
            raise ValueError("Nur 1 oder 2 Byte unterstützt")

        raw_value = int(round(value / faktor))
        data = self.signed_int_to_bytes(raw_value, byte_count, signed)

        x, y, z = map(int, property_path.split("/"))
        
        async with self._request_lock:
            result = await self._set_property_internal(device_uuid, x, y, z, data)
            # Invalidate cache for this device after successful write
            self._invalidate_cache_for_device(device_uuid)
            return result

    @api_put("/system/reset")
    async def _reset_system(self):
        """Internal method to build reset payload.
        
        The @api_put decorator handles:
        - Request locking
        - Rate limiting
        - Session management
        - Retry with exponential backoff
        """
        # No payload needed for reset
        return {}
    
    async def async_reset_system(self):
        """Trigger a restart of the ComfoClime device."""
        async with self._request_lock:
            return await self._reset_system()
