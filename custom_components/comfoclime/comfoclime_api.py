# comfoclime_api.py
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ComfoClimeAPI:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.uuid = None
        self._request_lock = asyncio.Lock()
        self._session = None

    async def _get_session(self):
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=5)
            self._session = aiohttp.ClientSession(timeout=timeout)
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

    async def async_get_uuid(self):
        async with self._request_lock:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/monitoring/ping") as response:
                response.raise_for_status()
                data = await response.json()
                self.uuid = data.get("uuid")
                return self.uuid

    async def async_get_dashboard_data(self):
        async with self._request_lock:
            if not self.uuid:
                await self.async_get_uuid()
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/system/{self.uuid}/dashboard"
            ) as response:
                response.raise_for_status()
                return await response.json()

    async def async_get_connected_devices(self):
        async with self._request_lock:
            if not self.uuid:
                await self.async_get_uuid()
            session = await self._get_session()
            url = f"{self.base_url}/system/{self.uuid}/devices"
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("devices", [])

    async def async_read_telemetry_for_device(
        self, device_uuid: str, telemetry_id: str, faktor: float = 1.0, signed: bool = True, byte_count: int | None = None
    ):
        async with self._request_lock:
            session = await self._get_session()
            url = f"{self.base_url}/device/{device_uuid}/telemetry/{telemetry_id}"
            async with session.get(url) as response:
                response.raise_for_status()
                payload = await response.json()

            data = payload.get("data")
            if not isinstance(data, list) or len(data) == 0:
                raise ValueError("Unerwartetes Telemetrie-Format")

        value = self.bytes_to_signed_int(data, byte_count, signed)
        return value * faktor

    async def async_read_property_for_device(
        self,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ):
        async with self._request_lock:
            data = await self._read_property_for_device_raw(device_uuid, property_path)

            # Wenn data leer/None ist, können wir nicht fortfahren
            if not data:
                return None

        if byte_count in (1, 2):
            value = self.bytes_to_signed_int(data, byte_count, signed)
        elif byte_count > 2:
            if len(data) != byte_count:
                raise ValueError(
                    f"Unerwartete Byte-Anzahl: erwartet {byte_count}, erhalten {len(data)}"
                )
            if all(0 <= byte < 256 for byte in data):
                return "".join(chr(byte) for byte in data if byte != 0)
        else:
            raise ValueError(f"Nicht unterstützte Byte-Anzahl: {byte_count}")

        return value * faktor

    async def _read_property_for_device_raw(
        self, device_uuid: str, property_path: str
    ) -> None | list:
        url = f"{self.base_url}/device/{device_uuid}/property/{property_path}"
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                response.raise_for_status()
                payload = await response.json()
        except Exception as e:
            _LOGGER.error(f"Fehler beim Abrufen der Property {property_path}: {e}")
            return None

        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError("Unerwartetes Property-Format")
        return data

    async def async_get_thermal_profile(self):
        async with self._request_lock:
            if not self.uuid:
                await self.async_get_uuid()
            url = f"{self.base_url}/system/{self.uuid}/thermalprofile"
            try:
                session = await self._get_session()
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                _LOGGER.warning(f"Fehler beim Abrufen von thermal_profile: {e}")
                return {}  # leer zurückgeben statt crashen

    async def _update_thermal_profile(self, updates: dict):
        """
        updates: dict mit Teilwerten, z. B. {"heatingThermalProfileSeasonData": {"comfortTemperature": 20.0}}

        Diese Methode füllt alle anderen Felder mit None (null), wie von der API gefordert.
        """
        full_payload = {
            "season": {
                "status": None,
                "season": None,
                "heatingThresholdTemperature": None,
                "coolingThresholdTemperature": None,
            },
            "temperature": {
                "status": None,
                "manualTemperature": None,
            },
            "temperatureProfile": None,
            "heatingThermalProfileSeasonData": {
                "comfortTemperature": None,
                "kneePointTemperature": None,
                "reductionDeltaTemperature": None,
            },
            "coolingThermalProfileSeasonData": {
                "comfortTemperature": None,
                "kneePointTemperature": None,
                "temperatureLimit": None,
            },
        }

        # Deep-Update: überschreibe gezielt Felder im Payload
        for section, values in updates.items():
            if section in full_payload and isinstance(values, dict):
                full_payload[section].update(values)
            else:
                full_payload[section] = values  # z. B. "temperatureProfile": 1

        if not self.uuid:
            await self.async_get_uuid()

        url = f"{self.base_url}/system/{self.uuid}/thermalprofile"
        session = await self._get_session()
        async with session.put(url, json=full_payload) as response:
            response.raise_for_status()
            return response.status == 200

    async def _update_dashboard(
        self,
        set_point_temperature: float | None = None,
        fan_speed: int | None = None,
        season: int | None = None,
        hp_standby: bool | None = None,
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

        Args:
            set_point_temperature: Target temperature (°C) - activates manual mode
            fan_speed: Fan speed (0-3)
            season: Season value (0=transition, 1=heating, 2=cooling)
            hp_standby: Heat pump standby state (True=standby/off, False=active)
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
            await self.async_get_uuid()

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

        # Add timestamp to payload
        tz = ZoneInfo(self.hass.config.time_zone)
        payload["timestamp"] = datetime.now(tz).isoformat()

        headers = {"content-type": "application/json; charset=utf-8"}
        url = f"{self.base_url}/system/{self.uuid}/dashboard"
        try:
            session = await self._get_session()
            async with session.put(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                try:
                    resp_json = await response.json()
                except Exception:
                    resp_json = {"text": await response.text()}
                _LOGGER.debug(f"Dashboard update OK payload={payload} response={resp_json}")
                return resp_json
        except Exception as e:
            _LOGGER.exception(f"Error updating dashboard (payload={payload})")
            raise
        return resp_json

    async def async_update_dashboard(self, **kwargs):
        """Async wrapper for update_dashboard method."""
        async with self._request_lock:
            return await self._update_dashboard(**kwargs)

    async def async_update_thermal_profile(self, updates: dict):
        """Async wrapper for update_thermal_profile method."""
        async with self._request_lock:
            return await self._update_thermal_profile(updates)

    async def async_set_hvac_season(self, season: int, hp_standby: bool = False):
        """Set HVAC season and standby state in a single atomic operation.

        This method updates both the season (via thermal profile) and hpStandby
        (via dashboard) in a single lock to prevent race conditions.

        Args:
            season: Season value (0=transition, 1=heating, 2=cooling)
            hp_standby: Heat pump standby state (False=active, True=standby/off)
        """
        async with self._request_lock:
            # First update dashboard to set hpStandby
            await self._update_dashboard(hp_standby=hp_standby)
            # Then update thermal profile to set season
            if not hp_standby:  # Only set season if device is active
                await self._update_thermal_profile({"season": {"season": season}})

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
            if byte_count not in (1, 2):
                raise ValueError("Nur 1 oder 2 Byte unterstützt")

            raw_value = int(round(value / faktor))
            data = self.signed_int_to_bytes(raw_value, byte_count, signed)

            x, y, z = map(int, property_path.split("/"))
            url = f"{self.base_url}/device/{device_uuid}/method/{x}/{y}/3"
            payload = {"data": [z] + data}

            try:
                session = await self._get_session()
                async with session.put(url, json=payload) as response:
                    response.raise_for_status()
            except Exception as e:
                _LOGGER.exception(
                    f"Fehler beim Schreiben von Property {property_path} mit Payload {payload}"
                )
                raise

    async def async_reset_system(self):
        """Trigger a restart of the ComfoClime device."""
        async with self._request_lock:
            url = f"{self.base_url}/system/reset"
            session = await self._get_session()
            async with session.put(url) as response:
                response.raise_for_status()
                return response.status == 200
