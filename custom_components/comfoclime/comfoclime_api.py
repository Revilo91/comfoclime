# comfoclime_api.py
import asyncio
import datetime
import logging

import requests

_LOGGER = logging.getLogger(__name__)


def _decode_raw_value(raw, factor=0.1):
    """Decode raw sensor values with auto-scaling and signed conversion.

    Small values (< 1000) → return as-is (already scaled)
    Large values (≥ 1000) → decode as signed int and apply factor
    """
    if raw is None:
        return None

    try:
        # Already scaled values pass through
        if abs(raw) < 1000:
            return float(raw)

        # Reverse-scale floats back to raw integer
        if isinstance(raw, float):
            raw = round(raw / factor)

        raw_int = int(raw)

        # Apply two's complement for signed conversion
        if raw_int <= 0xFF and raw_int >= 0x80:  # 1-byte signed
            raw_int -= 0x100
        elif raw_int >= 0x8000:  # 2-byte signed
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
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
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

    async def async_get_dashboard_data(self, hass):
        async with self._request_lock:
            return await hass.async_add_executor_job(self.get_dashboard_data)

    def get_dashboard_data(self):
        if not self.uuid:
            self.get_uuid()
        response = requests.get(
            f"{self.base_url}/system/{self.uuid}/dashboard", timeout=5
        )
        response.raise_for_status()
        data = response.json()

        # Auto-decode only temperature fields (ending with 'Temperature')
        return {
            key: _decode_raw_value(val, factor=0.1)
            if isinstance(val, (int, float)) and key.endswith("Temperature")
            else val
            for key, val in data.items()
        }

    async def async_get_connected_devices(self, hass):
        async with self._request_lock:
            return await hass.async_add_executor_job(self.get_connected_devices)

    def get_connected_devices(self):
        if not self.uuid:
            self.get_uuid()
        url = f"{self.base_url}/system/{self.uuid}/devices"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get("devices", [])

    async def async_read_telemetry_for_device(
        self, hass, device_uuid, telemetry_id, faktor=1.0, byte_count=None
    ):
        async with self._request_lock:
            return await hass.async_add_executor_job(
                self.read_telemetry_for_device,
                device_uuid,
                telemetry_id,
                faktor,
                byte_count,
            )

    def read_telemetry_for_device(
        self, device_uuid, telemetry_id, faktor=1.0, byte_count=None
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
            if value >= 0x80:
                value -= 0x100
        elif byte_count == 2:
            lsb, msb = data[:2]
            value = lsb + (msb << 8)
            if value >= 0x8000:
                value -= 0x10000
        else:
            raise ValueError(f"Nicht unterstützte Byte-Anzahl: {byte_count}")

        return value * faktor

    async def async_read_property_for_device(
        self,
        hass,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        byte_count: int | None = None,
    ):
        async with self._request_lock:
            return await hass.async_add_executor_job(
                self.read_property_for_device,
                device_uuid,
                property_path,
                faktor,
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

        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError("Unerwartetes Property-Format")
        return data

    def read_property_for_device(
        self,
        device_uuid: str,
        property_path: str,
        faktor: float = 1.0,
        byte_count: int | None = None,
    ) -> None | str | float:
        data = self.read_property_for_device_raw(device_uuid, property_path)

        # Wenn data leer/None ist, können wir nicht fortfahren
        if not data:
            return None

        # Wenn byte_count nicht angegeben wurde, verwende die Länge der Daten
        if byte_count is None:
            byte_count = len(data)

        if byte_count == 1:
            value = data[0]
            if value >= 0x80:
                value -= 0x100
        elif byte_count == 2:
            lsb, msb = data[:2]
            value = lsb + (msb << 8)
            if value >= 0x8000:
                value -= 0x10000
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

    async def async_get_thermal_profile(self, hass):
        async with self._request_lock:
            return await hass.async_add_executor_job(self.get_thermal_profile)

    def get_thermal_profile(self):
        if not self.uuid:
            self.get_uuid()
        url = f"{self.base_url}/system/{self.uuid}/thermalprofile"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            _LOGGER.warning(f"Fehler beim Abrufen von thermal_profile: {e}")
            return {}  # leer zurückgeben statt crashen

    def update_thermal_profile(self, updates: dict):
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
            self.get_uuid()

        url = f"{self.base_url}/system/{self.uuid}/thermalprofile"
        response = requests.put(url, json=full_payload, timeout=5)
        response.raise_for_status()
        return response.status_code == 200

    def update_dashboard(
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
            requests.RequestException: If the API request fails
        """
        if not self.uuid:
            self.get_uuid()

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

    async def async_update_dashboard(self, hass, **kwargs):
        """Async wrapper for update_dashboard method."""
        async with self._request_lock:
            return await hass.async_add_executor_job(
                lambda: self.update_dashboard(**kwargs)
            )

    async def async_update_thermal_profile(self, hass, updates: dict):
        """Async wrapper for update_thermal_profile method."""
        async with self._request_lock:
            return await hass.async_add_executor_job(
                lambda: self.update_thermal_profile(updates)
            )

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

            def _update():
                # First update dashboard to set hpStandby
                self.update_dashboard(hp_standby=hp_standby)
                # Then update thermal profile to set season
                if not hp_standby:  # Only set season if device is active
                    self.update_thermal_profile({"season": {"season": season}})

            return await hass.async_add_executor_job(_update)

    async def async_set_property_for_device(
        self,
        hass,
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
        faktor: float = 1.0,
    ):
        if byte_count not in (1, 2):
            raise ValueError("Nur 1 oder 2 Byte unterstützt")

        # Wert zurückrechnen, falls ein Faktor verwendet wird
        raw_value = int(round(value / faktor))

        # Bytes erzeugen (immer signed)
        if byte_count == 1:
            if raw_value < 0:
                raw_value += 0x100
            data = [raw_value & 0xFF]
        elif byte_count == 2:
            if raw_value < 0:
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

    async def async_reset_system(self, hass):
        async with self._request_lock:
            return await hass.async_add_executor_job(self.reset_system)

    def reset_system(self):
        """Trigger a restart of the ComfoClime device."""
        url = f"{self.base_url}/system/reset"
        response = requests.put(url, timeout=5)
        response.raise_for_status()
        return response.status_code == 200