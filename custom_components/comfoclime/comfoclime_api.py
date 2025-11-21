# comfoclime_api.py
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
from aiohttp import ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)


def _decode_raw_value(raw, factor=1.0, signed=True, byte_count=2):
    """Decode a raw dashboard value with optional signed two's complement conversion.

    This helper centralizes decoding logic for dashboard numeric fields that may
    represent signed INT16 values. The dashboard API sometimes returns values
    that are already scaled incorrectly or as unsigned integers when they should
    be signed.

    Args:
        raw: Raw value (int, float, or None) from dashboard API
        factor: Scaling factor to apply after decoding (default: 1.0)
        signed: Whether to apply two's complement for negative values (default: True)
        byte_count: Number of bytes (1 or 2) for two's complement threshold (default: 2)

    Returns:
        Decoded and scaled value (float) or None if raw is None/unconvertible

    Example:
        # Negative temperature incorrectly returned as unsigned value
        _decode_raw_value(65519, factor=0.1, signed=True, byte_count=2)  # Returns -1.7
    """
    if raw is None:
        return None

    try:
        # If raw is a float with large absolute value, assume it was incorrectly scaled
        # and reverse-scale it back to integer
        if isinstance(raw, float) and abs(raw) > 1000:
            raw = round(raw / factor)

        # Convert to integer
        raw_int = int(raw)

        # Apply two's complement conversion for signed values
        if signed:
            if byte_count == 1 and raw_int >= 0x80:
                raw_int -= 0x100
            elif byte_count == 2 and raw_int >= 0x8000:
                raw_int -= 0x10000

        return raw_int * factor
    except (ValueError, TypeError):
        return None


# Exception classes as per ComfoClimeAPI.md documentation
class ComfoClimeError(Exception):
    """Base exception for ComfoClime API errors."""


class ComfoClimeConnectionError(ComfoClimeError):
    """Exception for connection errors."""


class ComfoClimeTimeoutError(ComfoClimeError):
    """Exception for timeout errors."""


class ComfoClimeAuthenticationError(ComfoClimeError):
    """Exception for authentication errors."""


class ComfoClimeAPI:
    def __init__(self, base_url: str, session: ClientSession | None = None):
        """Initialize the API client.

        Args:
            base_url: The base URL of the ComfoClime device (e.g. http://192.168.1.10)
            session: Optional aiohttp ClientSession. If not provided, one will be created.
        """
        self.base_url = base_url.rstrip("/")
        self.uuid = None
        self._session = session
        self._close_session = False
        self._request_lock = asyncio.Lock()

    async def _get_session(self) -> ClientSession:
        """Get or create the client session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=ClientTimeout(total=10)
            )
            self._close_session = True
        return self._session

    async def close(self):
        """Close the session if we created it."""
        if self._close_session and self._session and not self._session.closed:
            await self._session.close()

    async def async_get_uuid(self, hass=None):
        """Get the UUID of the device."""
        # hass argument is kept for compatibility but not used
        async with self._request_lock:
            return await self._get_uuid()

    async def _get_uuid(self):
        """Internal method to get UUID."""
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}/monitoring/ping") as response:
                response.raise_for_status()
                data = await response.json()
                self.uuid = data.get("uuid")
                return self.uuid
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise ComfoClimeConnectionError(f"Error getting UUID: {err}") from err

    async def async_get_dashboard_data(self, hass=None):
        """Get dashboard data."""
        async with self._request_lock:
            if not self.uuid:
                await self._get_uuid()

            session = await self._get_session()
            try:
                async with session.get(
                    f"{self.base_url}/system/{self.uuid}/dashboard"
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # Decode temperature fields that may be returned as unsigned INT16
                    # when they should be signed (e.g., negative temperatures)
                    temp_fields = [
                        # "indoorTemperature",
                        "outdoorTemperature",
                        # "exhaustTemperature",
                        # "supplyTemperature",
                        # "runningMeanOutdoorTemperature",
                        # "setPointTemperature",  # Manual mode target temperature
                    ]

                    for field in temp_fields:
                        if field in data:
                            data[field] = _decode_raw_value(
                                data[field], factor=0.1, signed=True, byte_count=2
                            )

                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise ComfoClimeConnectionError(f"Error getting dashboard data: {err}") from err

    async def async_get_connected_devices(self, hass=None):
        """Get list of connected devices."""
        async with self._request_lock:
            if not self.uuid:
                await self._get_uuid()

            session = await self._get_session()
            url = f"{self.base_url}/system/{self.uuid}/devices"
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get("devices", [])
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise ComfoClimeConnectionError(f"Error getting connected devices: {err}") from err

    async def async_read_telemetry_for_device(
        self, hass, device_uuid, telemetry_id, faktor=1.0, signed=True, byte_count=None
    ):
        """Read telemetry data for a specific device."""
        async with self._request_lock:
            session = await self._get_session()
            url = f"{self.base_url}/device/{device_uuid}/telemetry/{telemetry_id}"

            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    payload = await response.json()

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
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise ComfoClimeConnectionError(f"Error reading telemetry: {err}") from err

    async def async_read_property_for_device(
        self,
        hass,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ):
        """Read property for a specific device."""
        async with self._request_lock:
            return await self._read_property_for_device(
                device_uuid, property_path, faktor, signed, byte_count
            )

    async def _read_property_for_device_raw(
        self, device_uuid: str, property_path: str
    ) -> None | list:
        session = await self._get_session()
        url = f"{self.base_url}/device/{device_uuid}/property/{property_path}"
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                payload = await response.json()
                data = payload.get("data")
                if not isinstance(data, list) or not data:
                    raise ValueError("Unerwartetes Property-Format")
                return data
        except Exception:
            _LOGGER.exception(f"Fehler beim Abrufen der Property {property_path}")
            return None

    async def _read_property_for_device(
        self,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        signed: bool = True,
        byte_count: int | None = None,
    ) -> None | str | float:
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
            # String property - decode all received bytes, not just byte_count
            # Actual string can be shorter than expected byte_count
            if all(0 <= byte < 256 for byte in data):
                return "".join(chr(byte) for byte in data if byte != 0)
            else:
                _LOGGER.warning(f"Invalid string data for property {property_path}: {data}")
                return None
        else:
            raise ValueError(f"Nicht unterstützte Byte-Anzahl: {byte_count}")

        return value * faktor

    async def async_get_thermal_profile(self, hass=None):
        """Get thermal profile."""
        async with self._request_lock:
            if not self.uuid:
                await self._get_uuid()

            session = await self._get_session()
            url = f"{self.base_url}/system/{self.uuid}/thermalprofile"
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                _LOGGER.warning(f"Fehler beim Abrufen von thermal_profile: {e}")
                return {}  # leer zurückgeben statt crashen

    async def _update_thermal_profile(self, updates: dict):
        """Internal method to update thermal profile."""
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
            await self._get_uuid()

        session = await self._get_session()
        url = f"{self.base_url}/system/{self.uuid}/thermalprofile"
        try:
            async with session.put(url, json=full_payload) as response:
                response.raise_for_status()
                return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise ComfoClimeConnectionError(f"Error updating thermal profile: {err}") from err

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
        """Internal method to update dashboard."""
        if not self.uuid:
            await self._get_uuid()

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
        # We don't have access to hass config here easily without passing it down
        # But we can use datetime.now() with local timezone if available or UTC
        payload["timestamp"] = datetime.now().astimezone().isoformat()

        headers = {"content-type": "application/json; charset=utf-8"}
        url = f"{self.base_url}/system/{self.uuid}/dashboard"

        session = await self._get_session()
        try:
            async with session.put(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                try:
                    resp_json = await response.json()
                except Exception:
                    text = await response.text()
                    resp_json = {"text": text}
                _LOGGER.debug(f"Dashboard update OK payload={payload} response={resp_json}")
                return resp_json
        except Exception:
            _LOGGER.exception(f"Error updating dashboard (payload={payload})")
            raise

    async def async_update_dashboard(self, hass, **kwargs):
        """Async wrapper for update_dashboard method."""
        async with self._request_lock:
            return await self._update_dashboard(**kwargs)

    async def async_update_thermal_profile(self, hass, updates: dict):
        """Async wrapper for update_thermal_profile method."""
        async with self._request_lock:
            return await self._update_thermal_profile(updates)

    async def async_set_hvac_season(self, hass, season: int, hp_standby: bool = False):
        """Set HVAC season and standby state in a single atomic operation.

        This method updates both the season (via thermal profile) and hpStandby
        (via dashboard) in a single lock to prevent race conditions.

        Args:
            hass: Home Assistant instance
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
        hass,
        device_uuid: str,
        property_path: str,
        value: float,
        *,
        byte_count: int,
        signed: bool = True,
        faktor: float = 1.0,
    ):
        """Set property for a specific device."""
        async with self._request_lock:
            return await self._set_property_for_device(
                device_uuid,
                property_path,
                value,
                byte_count=byte_count,
                signed=signed,
                faktor=faktor,
            )

    async def _set_property_for_device(
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

        session = await self._get_session()
        try:
            async with session.put(url, json=payload) as response:
                response.raise_for_status()
        except Exception:
            _LOGGER.exception(
                f"Fehler beim Schreiben von Property {property_path} mit Payload {payload}"
            )
            raise

    async def async_reset_system(self, hass):
        """Trigger a restart of the ComfoClime device."""
        async with self._request_lock:
            if not self.uuid:
                await self._get_uuid()

            session = await self._get_session()
            url = f"{self.base_url}/system/reset"
            try:
                async with session.put(url) as response:
                    response.raise_for_status()
                    return response.status == 200
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise ComfoClimeConnectionError(f"Error resetting system: {err}") from err
