# comfoclime_api.py
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

_LOGGER = logging.getLogger(__name__)


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

    async def async_get_uuid(self, hass):
        async with self._request_lock:
            return await hass.async_add_executor_job(self.get_uuid)

    def get_uuid(self):
        response = requests.get(f"{self.base_url}/monitoring/ping", timeout=5)
        response.raise_for_status()
        data = response.json()
        self.uuid = data.get("uuid")
        return self.uuid

    async def async_get_uuid(self):
        """Get UUID with lock protection."""
        async with self._request_lock:
            return await self._async_get_uuid_internal()

    def get_dashboard_data(self):
        if not self.uuid:
            self.get_uuid()
        response = requests.get(
            f"{self.base_url}/system/{self.uuid}/dashboard", timeout=5
        )
        response.raise_for_status()
        return response.json()

    async def async_get_connected_devices(self):
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=False)
            if not self.uuid:
                await self._async_get_uuid_internal()
            session = await self._get_session()
            url = f"{self.base_url}/system/{self.uuid}/devices"
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("devices", [])

    async def async_read_telemetry_for_device(
        self, hass, device_uuid, telemetry_id, faktor=1.0, signed=True, byte_count=None
    ):
        async with self._request_lock:
            return await hass.async_add_executor_job(
                self.read_telemetry_for_device,
                device_uuid,
                telemetry_id,
                faktor,
                signed,
                byte_count,
            )

    def read_telemetry_for_device(
        self, device_uuid, telemetry_id, faktor=1.0, signed=True, byte_count=None
    ):
        url = f"{self.base_url}/device/{device_uuid}/telemetry/{telemetry_id}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        payload = response.json()

        data = payload.get("data")
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("Unerwartetes Telemetrie-Format")

        if byte_count is None:
            byte_count = len(data)

        if byte_count == 1:
            value = data[0]
            if signed and value >= 0x80:
                value -= 0x100
        elif byte_count == 2:
            lsb, msb = data[:2]
            value = lsb + (msb << 8)
            if signed and value >= 0x8000:
                value -= 0x10000
        else:
            raise ValueError(f"Nicht unterstützte Byte-Anzahl: {byte_count}")

        return value * faktor

    async def async_read_property_for_device(
        self,
        device_uuid: str,
        telemetry_id: str,
        faktor: float = 1.0,
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
            return await hass.async_add_executor_job(
                self.read_property_for_device,
                device_uuid,
                property_path,
                faktor,
                signed,
                byte_count,
            )

    def read_property_for_device_raw(
        self, device_uuid: str, property_path: str
    ) -> None | list:
        url = f"{self.base_url}/device/{device_uuid}/property/{property_path}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            _LOGGER.error(f"Fehler beim Abrufen der Property {property_path}: {e}")
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

        # Wenn byte_count nicht angegeben wurde, verwende die Länge der Daten
        if byte_count is None:
            byte_count = len(data)

        if byte_count == 1:
            value = data[0]
            if signed and value >= 0x80:
                value -= 0x100
        elif byte_count == 2:
            lsb, msb = data[:2]
            value = lsb + (msb << 8)
            if signed and value >= 0x8000:
                value -= 0x10000
        elif byte_count > 2:
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
            session = await self._get_session()
            async with session.get(url) as response:
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
                session = await self._get_session()
                async with session.get(url) as response:
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
        try:
            session = await self._get_session()
            _LOGGER.debug(f"Sende Thermal Profile Update: {payload}")
            async with session.put(url, json=payload) as response:
                response.raise_for_status()
                _LOGGER.debug(
                    f"Thermal Profile Update erfolgreich, Status: {response.status}"
                )
                return response.status == 200
        except Exception:
            _LOGGER.exception(f"Error updating thermal profile (payload={payload})")
            raise

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
        if hp_standby is not None:
            payload["hpStandby"] = hp_standby

        if not payload:
            _LOGGER.debug(
                "No dashboard fields to update (empty payload) - skipping PUT"
            )
            return {}

        await self._wait_for_rate_limit(is_write=True)

        # Add timestamp to payload
        payload["timestamp"] = datetime.datetime.now().isoformat()

        headers = {"content-type": "application/json; charset=utf-8"}
        url = f"{self.base_url}/system/{self.uuid}/dashboard"
        try:
            response = requests.put(url, json=payload, timeout=5, headers=headers)
            response.raise_for_status()
            try:
                resp_json = response.json()
            except Exception:
                resp_json = {"text": response.text}
            _LOGGER.debug(f"Dashboard update OK payload={payload} response={resp_json}")
            return resp_json
        except Exception as e:
            _LOGGER.error(f"Error updating dashboard (payload={payload}): {e}")
            raise
        return resp_json

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
        # Build conversion_map from class-level FIELD_MAPPING
        conversion_map = {}
        for k, v in self.FIELD_MAPPING.items():
            if v[1] is None:
                conversion_map[(v[0],)] = k
            else:
                conversion_map[(v[0], v[1])] = k

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
        faktor: float = 1.0,
    ):
        async with self._request_lock:
            return await hass.async_add_executor_job(
                lambda: self.set_property_for_device(
                    device_uuid,
                    property_path,
                    value,
                    byte_count=byte_count,
                    signed=signed,
                    faktor=faktor,
                )
            )

    def set_property_for_device(
        self,
        device_uuid: str,
        property_path: str,
        value: float,
        *,
        byte_count: int,
        signed: bool = True,
        faktor: float = 1.0,
    ):
        if byte_count not in (1, 2):
            raise ValueError("Nur 1 oder 2 Byte unterstützt")

        # Wert zurückrechnen, falls ein Faktor verwendet wird
        raw_value = int(round(value / faktor))

        # Bytes erzeugen
        if byte_count == 1:
            if signed and raw_value < 0:
                raw_value += 0x100
            data = [raw_value & 0xFF]
        elif byte_count == 2:
            if signed and raw_value < 0:
                raw_value += 0x10000
            data = [raw_value & 0xFF, (raw_value >> 8) & 0xFF]

            x, y, z = map(int, property_path.split("/"))
            url = f"{self.base_url}/device/{device_uuid}/method/{x}/{y}/3"
            payload = {"data": [z] + data}

        try:
            response = requests.put(url, json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            _LOGGER.error(
                f"Fehler beim Schreiben von Property {property_path} mit Payload {payload}: {e}"
            )
            raise

    async def async_reset_system(self):
        """Trigger a restart of the ComfoClime device."""
        async with self._request_lock:
            await self._wait_for_rate_limit(is_write=True)
            url = f"{self.base_url}/system/reset"
            session = await self._get_session()
            async with session.put(url) as response:
                response.raise_for_status()
                return response.status == 200
