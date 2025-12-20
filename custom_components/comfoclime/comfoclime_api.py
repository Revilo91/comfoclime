# comfoclime_api.py
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Rate limiting configuration
MIN_REQUEST_INTERVAL = (
    0.1  # Minimum seconds between any requests (reduced for better throughput)
)
WRITE_COOLDOWN = 2.0  # Seconds to wait after a write operation before allowing reads
REQUEST_DEBOUNCE = 0.3  # Debounce time for rapid successive requests
CACHE_TTL = 30.0  # Cache time-to-live in seconds

# Timeout configuration
DEFAULT_READ_TIMEOUT = 10  # Timeout for read operations (GET)
DEFAULT_WRITE_TIMEOUT = (
    30  # Timeout for write operations (PUT) - longer for dashboard updates
)
MAX_RETRIES = 3  # Number of retries for transient failures


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

    def __init__(self, base_url, hass=None):
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

    def _get_current_time(self) -> float:
        """Get current monotonic time for rate limiting."""
        return asyncio.get_event_loop().time()

    def _get_cache_key(self, device_uuid: str, data_id: str) -> str:
        """Generate a cache key from device UUID and data ID."""
        return f"{device_uuid}:{data_id}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if a cached value is still valid."""
        return (self._get_current_time() - timestamp) < CACHE_TTL

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
        if time_since_last_request < MIN_REQUEST_INTERVAL:
            wait_time = max(wait_time, MIN_REQUEST_INTERVAL - time_since_last_request)

        # If this is a read and we recently wrote, wait for cooldown
        if not is_write and time_since_last_write < WRITE_COOLDOWN:
            wait_time = max(wait_time, WRITE_COOLDOWN - time_since_last_write)

        if wait_time > 0:
            _LOGGER.debug(f"Rate limiting: waiting {wait_time:.2f}s before request")
            await asyncio.sleep(wait_time)

        # Update last request time
        self._last_request_time = self._get_current_time()

        # If this is a write, update write time
        if is_write:
            self._last_write_time = self._get_current_time()

    async def _debounced_request(
        self, key: str, coro_factory, debounce_time: float = REQUEST_DEBOUNCE
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

    async def _async_get_uuid_internal(self):
        """Internal method to get UUID without acquiring lock."""
        await self._wait_for_rate_limit(is_write=False)
        timeout = aiohttp.ClientTimeout(total=DEFAULT_READ_TIMEOUT)
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/monitoring/ping", timeout=timeout
        ) as response:
            response.raise_for_status()
            data = await response.json()
            self.uuid = data.get("uuid")
            return self.uuid

    async def async_get_uuid(self):
        """Get UUID with lock protection."""
        async with self._request_lock:
            return await self._async_get_uuid_internal()

    async def async_get_dashboard_data(self):
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=False)
            if not self.uuid:
                await self._async_get_uuid_internal()
            timeout = aiohttp.ClientTimeout(total=DEFAULT_READ_TIMEOUT)
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/system/{self.uuid}/dashboard", timeout=timeout
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def async_get_connected_devices(self):
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=False)
            if not self.uuid:
                await self._async_get_uuid_internal()
            timeout = aiohttp.ClientTimeout(total=DEFAULT_READ_TIMEOUT)
            session = await self._get_session()
            url = f"{self.base_url}/system/{self.uuid}/devices"
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("devices", [])

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

        # Not in cache, fetch from API
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=False)
            try:
                timeout = aiohttp.ClientTimeout(total=DEFAULT_READ_TIMEOUT)
                session = await self._get_session()
                url = f"{self.base_url}/device/{device_uuid}/telemetry/{telemetry_id}"
                async with session.get(url, timeout=timeout) as response:
                    response.raise_for_status()
                    payload = await response.json()

                data = payload.get("data")
                if not isinstance(data, list) or len(data) == 0:
                    _LOGGER.debug(f"Ungültiges Telemetrie-Format für {telemetry_id}")
                    return None

            except asyncio.TimeoutError:
                _LOGGER.debug(f"Timeout beim Abrufen der Telemetrie {telemetry_id}")
                return None
            except Exception as e:
                _LOGGER.debug(f"Fehler beim Abrufen der Telemetrie {telemetry_id}: {e}")
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

        # Not in cache, fetch from API
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=False)
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

    async def _read_property_for_device_raw(
        self, device_uuid: str, property_path: str
    ) -> None | list:
        url = f"{self.base_url}/device/{device_uuid}/property/{property_path}"
        try:
            timeout = aiohttp.ClientTimeout(total=DEFAULT_READ_TIMEOUT)
            session = await self._get_session()
            async with session.get(url, timeout=timeout) as response:
                try:
                    response.raise_for_status()
                except Exception as http_error:
                    _LOGGER.debug(
                        f"HTTP error beim Abrufen der Property {property_path} "
                        f"(Status {response.status}): {http_error}"
                    )
                    return None
                payload = await response.json()
        except asyncio.TimeoutError:
            _LOGGER.debug(f"Timeout beim Abrufen der Property {property_path}")
            return None
        except Exception as e:
            _LOGGER.debug(f"Fehler beim Abrufen der Property {property_path}: {e}")
            return None

        data = payload.get("data")
        if not isinstance(data, list) or not data:
            _LOGGER.debug(f"Ungültiges Datenformat für Property {property_path}")
            return None
        return data

    async def async_get_thermal_profile(self):
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=False)
            if not self.uuid:
                await self._async_get_uuid_internal()
            url = f"{self.base_url}/system/{self.uuid}/thermalprofile"
            try:
                timeout = aiohttp.ClientTimeout(total=DEFAULT_READ_TIMEOUT)
                session = await self._get_session()
                async with session.get(url, timeout=timeout) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                _LOGGER.warning(f"Fehler beim Abrufen von thermal_profile: {e}")
                return {}  # leer zurückgeben statt crashen

    async def _update_thermal_profile(self, **kwargs) -> bool:
        """Update thermal profile settings via API.

        Modern method for thermal profile updates. Only fields that are provided
        will be included in the update payload.

        Supported kwargs:
            - season_status, season_value, heating_threshold_temperature, cooling_threshold_temperature
            - temperature_status, manual_temperature
            - temperature_profile
            - heating_comfort_temperature, heating_knee_point_temperature, heating_reduction_delta_temperature
            - cooling_comfort_temperature, cooling_knee_point_temperature, cooling_temperature_limit

        Returns:
            True if update was successful, False otherwise
        """
        if not self.uuid:
            await self._async_get_uuid_internal()

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

        if not payload:
            _LOGGER.debug(
                "No thermal profile fields to update (empty payload) - skipping PUT"
            )
            return True

        await self._wait_for_rate_limit(is_write=True)

        url = f"{self.base_url}/system/{self.uuid}/thermalprofile"

        # Retry logic for transient failures
        last_exception = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # Use longer timeout for write operations
                timeout = aiohttp.ClientTimeout(total=DEFAULT_WRITE_TIMEOUT)
                session = await self._get_session()
                _LOGGER.debug(
                    f"Thermal profile update attempt {attempt + 1}/{MAX_RETRIES + 1}, "
                    f"timeout={DEFAULT_WRITE_TIMEOUT}s, payload: {payload}"
                )
                async with session.put(url, json=payload, timeout=timeout) as response:
                    response.raise_for_status()
                    _LOGGER.debug(
                        f"Thermal Profile Update erfolgreich, Status: {response.status}"
                    )
                    return response.status == 200
            except (  # noqa: PERF203
                asyncio.TimeoutError,
                asyncio.CancelledError,
                aiohttp.ClientError,
            ) as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    # Exponential backoff: 2s, 4s, 8s
                    wait_time = 2 ** (attempt + 1)
                    _LOGGER.warning(
                        f"Thermal profile update failed (attempt {attempt + 1}/{MAX_RETRIES + 1}), "
                        f"retrying in {wait_time}s: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    _LOGGER.exception(
                        f"Thermal profile update failed after {MAX_RETRIES + 1} attempts: "
                        f"{type(e).__name__}"
                    )

        # If we get here, all retries failed
        # last_exception should always be set by the loop, but we check defensively
        if last_exception:
            raise last_exception
        raise RuntimeError("Thermal profile update failed with unknown error")

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

        # Android app export from @msfuture
        payload = {
            "@type": None,
            "name": None,
            "displayName": None,
            "description": None,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": status,
            "setPointTemperature": set_point_temperature,
            "temperatureProfile": temperature_profile,
            "seasonProfile": season_profile,
            "fanSpeed": fan_speed,
            "scenario": None,
            "scenarioTimeLeft": None,
            "season": season,
            "schedule": None,
            "scenario": None,
            "scenarioTimeLeft": None,
            "scenarioStartDelay": None
        }

        The API distinguishes between two modes:
        - Automatic mode (status=1): Uses preset profiles (seasonProfile, temperatureProfile)
        - Manual mode (status=0): Uses manual temperature (setPointTemperature)

        Scenario modes:
        - 4: Kochen (Cooking) - 30 minutes high ventilation
        - 5: Party - 30 minutes high ventilation
        - 7: Urlaub (Holiday) - 24 hours reduced mode
        - 8: Boost - 30 minutes maximum power

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
            Response JSON from the API

        Raises:
            aiohttp.ClientError: If the API request fails
        """
        if not self.uuid:
            await self._async_get_uuid_internal()

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

        if not payload:
            _LOGGER.debug(
                "No dashboard fields to update (empty payload) - skipping PUT"
            )
            return {}

        await self._wait_for_rate_limit(is_write=True)

        # Add timestamp to payload
        if not self.hass:
            raise ValueError("hass instance required for timestamp generation")
        tz = ZoneInfo(self.hass.config.time_zone)
        payload["timestamp"] = datetime.now(tz).isoformat()

        headers = {"content-type": "application/json; charset=utf-8"}
        url = f"{self.base_url}/system/{self.uuid}/dashboard"

        # Retry logic for transient failures
        last_exception = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # Use longer timeout for write operations
                timeout = aiohttp.ClientTimeout(total=DEFAULT_WRITE_TIMEOUT)
                session = await self._get_session()
                _LOGGER.debug(
                    f"Dashboard update attempt {attempt + 1}/{MAX_RETRIES + 1}, "
                    f"timeout={DEFAULT_WRITE_TIMEOUT}s, payload={payload}"
                )
                async with session.put(
                    url, json=payload, headers=headers, timeout=timeout
                ) as response:
                    response.raise_for_status()
                    try:
                        resp_json = await response.json()
                    except Exception:
                        resp_json = {"text": await response.text()}
                    _LOGGER.debug(
                        f"Dashboard update OK payload={payload} response={resp_json}"
                    )
                    return resp_json
            except (  # noqa: PERF203
                asyncio.TimeoutError,
                asyncio.CancelledError,
                aiohttp.ClientError,
            ) as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    # Exponential backoff: 2s, 4s, 8s
                    wait_time = 2 ** (attempt + 1)
                    _LOGGER.warning(
                        f"Dashboard update failed (attempt {attempt + 1}/{MAX_RETRIES + 1}), "
                        f"retrying in {wait_time}s: {type(e).__name__}: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    _LOGGER.exception(
                        f"Dashboard update failed after {MAX_RETRIES + 1} attempts: "
                        f"{type(e).__name__}"
                    )

        # If we get here, all retries failed
        # last_exception should always be set by the loop, but we check defensively
        if last_exception:
            raise last_exception
        raise RuntimeError("Dashboard update failed with unknown error")

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
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=True)
            if byte_count not in (1, 2):
                raise ValueError("Nur 1 oder 2 Byte unterstützt")

            raw_value = int(round(value / faktor))
            data = self.signed_int_to_bytes(raw_value, byte_count, signed)

            x, y, z = map(int, property_path.split("/"))
            url = f"{self.base_url}/device/{device_uuid}/method/{x}/{y}/3"
            payload = {"data": [z] + data}

            # Retry logic for transient failures
            last_exception = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    # Use longer timeout for write operations
                    timeout = aiohttp.ClientTimeout(total=DEFAULT_WRITE_TIMEOUT)
                    session = await self._get_session()
                    _LOGGER.debug(
                        f"Property write attempt {attempt + 1}/{MAX_RETRIES + 1}, "
                        f"timeout={DEFAULT_WRITE_TIMEOUT}s, path={property_path}, payload={payload}"
                    )
                    async with session.put(
                        url, json=payload, timeout=timeout
                    ) as response:
                        response.raise_for_status()
                    # Invalidate cache for this device after successful write
                    self._invalidate_cache_for_device(device_uuid)
                    return  # Success, exit retry loop
                except (  # noqa: PERF203
                    asyncio.TimeoutError,
                    asyncio.CancelledError,
                    aiohttp.ClientError,
                ) as e:
                    last_exception = e
                    if attempt < MAX_RETRIES:
                        # Exponential backoff: 2s, 4s, 8s
                        wait_time = 2 ** (attempt + 1)
                        _LOGGER.warning(
                            f"Property write failed (attempt {attempt + 1}/{MAX_RETRIES + 1}), "
                            f"retrying in {wait_time}s: {type(e).__name__}: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        _LOGGER.exception(
                            f"Property write failed after {MAX_RETRIES + 1} attempts: "
                            f"{type(e).__name__}"
                        )

            # If we get here, all retries failed
            # last_exception should always be set by the loop, but we check defensively
            if last_exception:
                raise last_exception
            raise RuntimeError(
                f"Property write failed for {property_path} with unknown error"
            )

    async def async_reset_system(self):
        """Trigger a restart of the ComfoClime device."""
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=True)
            url = f"{self.base_url}/system/reset"

            # Use longer timeout for write operations
            timeout = aiohttp.ClientTimeout(total=DEFAULT_WRITE_TIMEOUT)
            session = await self._get_session()
            async with session.put(url, timeout=timeout) as response:
                response.raise_for_status()
                return response.status == 200
