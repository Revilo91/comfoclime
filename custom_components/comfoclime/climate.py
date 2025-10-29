"""Climate platform for ComfoClime integration."""
import logging
from typing import Any

from homeassistant.components.climate import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .coordinator import ComfoClimeDashboardCoordinator


_LOGGER = logging.getLogger(__name__)

# Temperature Profile Presets
PRESET_MAPPING = {
    0: PRESET_COMFORT,
    1: PRESET_BOOST,
    2: PRESET_ECO,
}

PRESET_REVERSE_MAPPING = {v: k for k, v in PRESET_MAPPING.items()}

# Fan Mode Mapping (based on fan.py implementation)
# fanSpeed from dashboard: 0, 1, 2, 3
FAN_MODE_MAPPING = {
    0: FAN_OFF,     # Speed 0
    1: FAN_LOW,     # Speed 1
    2: FAN_MEDIUM,  # Speed 2
    3: FAN_HIGH,    # Speed 3
}

FAN_MODE_REVERSE_MAPPING = {v: k for k, v in FAN_MODE_MAPPING.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ComfoClime climate entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    api = data["api"]
    dashboard_coordinator = data["coordinator"]
    thermalprofile_coordinator = data["tpcoordinator"]
    main_device = data.get("main_device")

    if not main_device:
        _LOGGER.warning("No main device found - cannot create climate entity")
        return

    climate_entity = ComfoClimeClimate(
        dashboard_coordinator,
        thermalprofile_coordinator,
        api,
        main_device,
        config_entry
    )

    async_add_entities([climate_entity])


class ComfoClimeClimate(CoordinatorEntity[ComfoClimeDashboardCoordinator], ClimateEntity):
    """ComfoClime Climate entity."""

    def __init__(self, dashboard_coordinator, thermalprofile_coordinator, api, device, entry):
        """Initialize the climate entity."""
        super().__init__(dashboard_coordinator)
        self._api = api
        self._thermalprofile_coordinator = thermalprofile_coordinator
        self._device = device
        self._entry = entry

        # Entity attributes
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_name = None  # Use device name
        self._attr_has_entity_name = True
        self._attr_translation_key = "climate"

        # Temperature settings
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_precision = 0.5
        self._attr_target_temperature_step = 0.5

        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.FAN_MODE
        )

        # HVAC modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
        ]

        # Preset modes
        self._attr_preset_modes = list(PRESET_REVERSE_MAPPING.keys())

        # Fan modes
        self._attr_fan_modes = list(FAN_MODE_REVERSE_MAPPING.keys())

        # Add thermal profile coordinator listener
        self._thermalprofile_coordinator.async_add_listener(self._handle_coordinator_update)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self._thermalprofile_coordinator.last_update_success
        )

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device["uuid"])},
            "name": self._device.get("displayName", "ComfoClime"),
            "manufacturer": "Zehnder",
            "model": self._device.get("@modelType", "ComfoClime"),
            "sw_version": self._device.get("version"),
        }

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature from dashboard data."""
        if self.coordinator.data:
            return self.coordinator.data.get("indoorTemperature")
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature from thermal profile data.

        According to API documentation:
        - In manual mode (temperature.status=0): Returns setPointTemperature from dashboard
        - In automatic mode (temperature.status=1): Returns comfortTemperature for current season
        """
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return None

        temp_data = thermal_data.get("temperature", {})

        # When automatic mode is OFF (status=0), use setPointTemperature from dashboard
        if self._get_temperature_status() == 0:
            # In manual mode, the dashboard contains setPointTemperature
            if self.coordinator.data:
                set_point = self.coordinator.data.get("setPointTemperature")
                if set_point is not None:
                    return set_point
            # Fallback to manualTemperature from thermal profile
            return temp_data.get("manualTemperature")

        # When automatic mode is ON (status=1), use comfort temperature based on season
        season = self._get_current_season()

        if season == 1:  # heating
            heating_data = thermal_data.get("heatingThermalProfileSeasonData", {})
            return heating_data.get("comfortTemperature")
        elif season == 2:  # cooling
            cooling_data = thermal_data.get("coolingThermalProfileSeasonData", {})
            return cooling_data.get("comfortTemperature")

        # Fallback: manual temperature (for transitional season)
        return temp_data.get("manualTemperature")

    @property
    def min_temp(self) -> float:
        """Return minimum temperature as per Copilot instructions."""
        return 10.0

    @property
    def max_temp(self) -> float:
        """Return maximum temperature as per Copilot instructions."""
        return 30.0

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode from dashboard data.

        Maps the season field from dashboard to HVAC mode:
        - season 0 (transitional) → FAN_ONLY
        - season 1 (heating) → HEAT
        - season 2 (cooling) → COOL
        - hpStandby true → OFF (device powered off)
        """
        if not self.coordinator.data:
            return HVACMode.OFF

        # Check if device is in standby (powered off)
        hp_standby = self.coordinator.data.get("hpStandby")
        if hp_standby is True:
            return HVACMode.OFF

        # Map season from dashboard to HVAC mode
        season = self.coordinator.data.get("season")

        if season == 0:  # transitional
            return HVACMode.FAN_ONLY
        elif season == 1:  # heating
            return HVACMode.HEAT
        elif season == 2:  # cooling
            return HVACMode.COOL

        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action based on dashboard heatPumpStatus.

        According to ComfoClime API documentation, heatPumpStatus values:
        - 0: heat pump is off
        - 1: starting up
        - 3: heating
        - 5: cooling
        - Other values: transitional states (defrost, etc.)

        Reference: https://github.com/msfuture/comfoclime_api/blob/main/ComfoClimeAPI.md#heat-pump-status-codes
        """
        if not self.coordinator.data:
            return HVACAction.OFF

        heat_pump_status = self.coordinator.data.get("heatPumpStatus")

        if heat_pump_status is None:
            return HVACAction.OFF

        # Map heat pump status codes to HVAC actions
        if heat_pump_status == 0:
            # Heat pump is off
            return HVACAction.OFF
        elif heat_pump_status == 1:
            # Starting up - show as idle (preparing to heat/cool)
            return HVACAction.IDLE
        elif heat_pump_status == 3:
            # Actively heating
            return HVACAction.HEATING
        elif heat_pump_status == 5:
            # Actively cooling
            return HVACAction.COOLING
        else:
            # Other status codes (17, 19, 21, 67, 75, 83, etc.)
            # These are transitional states like defrost, anti-freeze, etc.
            # Show as idle since heat pump is running but not actively heating/cooling
            return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode from coordinator data."""
        # Prüfe Dashboard Coordinator (für aktuellen Zustand)
        if self.coordinator.data:
            temp_profile = self.coordinator.data.get("temperatureProfile")
            if isinstance(temp_profile, int):
                return PRESET_MAPPING.get(temp_profile)
            if isinstance(temp_profile, str) and temp_profile.isdigit():
                return PRESET_MAPPING.get(int(temp_profile))

        # Fallback: Prüfe Thermal Profile Coordinator (für Select Entity Änderungen)
        if self._thermalprofile_coordinator.data:
            temp_profile = self._thermalprofile_coordinator.data.get("temperatureProfile")
            if isinstance(temp_profile, int):
                return PRESET_MAPPING.get(temp_profile)
            if isinstance(temp_profile, str) and temp_profile.isdigit():
                return PRESET_MAPPING.get(int(temp_profile))

        return None

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode from dashboard data.

        Maps fanSpeed from dashboard (0-3) to fan mode strings:
        - 0: off
        - 1: low
        - 2: medium
        - 3: high
        """
        if self.coordinator.data:
            fan_speed = self.coordinator.data.get("fanSpeed")
            if isinstance(fan_speed, int):
                return FAN_MODE_MAPPING.get(fan_speed)
            if isinstance(fan_speed, str) and fan_speed.isdigit():
                return FAN_MODE_MAPPING.get(int(fan_speed))
        return None

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return self._attr_fan_modes

    def _get_temperature_status(self) -> int:
        """Get the temperature.status value from thermal profile.

        Returns:
            1 if automatic comfort temperature is enabled (default)
            0 if manual temperature mode is active
        """
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return 1  # default to automatic

        temp_data = thermal_data.get("temperature", {})
        return temp_data.get("status", 1)

    def _get_current_season(self) -> int:
        """Get the current season value from thermal profile.

        Returns:
            0 for transitional, 1 for heating, 2 for cooling
        """
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return 0

        season_data = thermal_data.get("season", {})
        return season_data.get("season", 0)

    def _get_season_status(self) -> int:
        """Get the season.status value from thermal profile.

        Returns:
            0 for manual season mode
            1 for automatic season mode (default)
        """
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return 1  # default to automatic

        season_data = thermal_data.get("season", {})
        return season_data.get("status", 1)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature by updating thermal profile.

        Respects the temperature.status switch:
        - When temperature.status=1 (automatic ON): Updates comfortTemperature for current season
        - When temperature.status=0 (automatic OFF): Updates setPointTemperature via dashboard API

        According to API documentation, setPointTemperature should be set via the dashboard
        endpoint when in manual mode, not via thermalprofile.
        """
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.warning("No temperature provided in kwargs")
            return

        try:
            # Get thermal profile data to check temperature.status
            thermal_data = self._thermalprofile_coordinator.data
            if not thermal_data:
                _LOGGER.error("No thermal profile data available")
                return

            temp_status = self._get_temperature_status()

            # When automatic comfort temperature switch is OFF (status=0)
            # Use dashboard API with setPointTemperature
            if temp_status == 0:
                _LOGGER.debug(f"Automatic comfort temperature is OFF - setting setPointTemperature to {temperature} via dashboard API")
                # Use set_device_setting which uses the dashboard API
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, None
                )
                # Now we need to set setPointTemperature - let's update set_device_setting to support it
                # For now, use a direct dashboard update
                await self.async_set_setpoint_temperature(temperature)
            else:
                # When automatic comfort temperature switch is ON (status=1)
                # Update the appropriate comfort temperature based on current season/HVAC mode
                hvac_mode = self.hvac_mode
                season = self._get_current_season()

                if hvac_mode == HVACMode.HEAT or season == 1:
                    # Update heating comfort temperature
                    _LOGGER.debug(f"Automatic comfort temperature is ON - setting heating comfortTemperature to {temperature}")
                    updates = {
                        "heatingThermalProfileSeasonData": {
                            "comfortTemperature": temperature
                        }
                    }
                    await self.hass.async_add_executor_job(
                        self._api.update_thermal_profile, updates
                    )
                elif hvac_mode == HVACMode.COOL or season == 2:
                    # Update cooling comfort temperature
                    _LOGGER.debug(f"Automatic comfort temperature is ON - setting cooling comfortTemperature to {temperature}")
                    updates = {
                        "coolingThermalProfileSeasonData": {
                            "comfortTemperature": temperature
                        }
                    }
                    await self.hass.async_add_executor_job(
                        self._api.update_thermal_profile, updates
                    )
                else:
                    # For transitional season or FAN_ONLY/OFF modes, use setPointTemperature
                    _LOGGER.debug(f"Transitional season or OFF/FAN_ONLY mode - setting setPointTemperature to {temperature}")
                    await self.async_set_setpoint_temperature(temperature)

            # Request refresh of coordinators
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception(f"Failed to set temperature to {temperature}")

    async def async_set_setpoint_temperature(self, temperature: float) -> None:
        """Set setPointTemperature via dashboard API.

        According to API documentation, setPointTemperature is set via the dashboard
        PUT endpoint in manual mode. Only fields documented in the API spec are included.
        """
        import requests

        if not self._api.uuid:
            await self.hass.async_add_executor_job(self._api.get_uuid)

        def _set_dashboard_temperature():
            # Only include fields documented in the ComfoClime API spec
            # Fields like scenario, scenarioTimeLeft, @type, name, displayName, description
            # are NOT part of the official API and should not be included
            payload = {
                "setPointTemperature": temperature,
                "fanSpeed": None,
                "season": None,
                "schedule": None,
            }
            headers = {"content-type": "application/json; charset=utf-8"}
            url = f"{self._api.base_url}/system/{self._api.uuid}/dashboard"
            try:
                response = requests.put(url, json=payload, timeout=5, headers=headers)
                response.raise_for_status()
            except Exception as e:
                _LOGGER.error(f"Fehler beim Setzen von setPointTemperature: {e}")
                raise

        await self.hass.async_add_executor_job(_set_dashboard_temperature)

    async def _set_hp_standby(self, hp_standby: bool) -> None:
        """Set hpStandby via dashboard API.

        According to issue requirements, this controls the heat pump standby state:
        - hpStandby: false when HVAC mode is OFF (turns off ComfoClime via heat pump)
        - hpStandby: true for all other HVAC modes (ensures device is active)
        """
        import requests

        if not self._api.uuid:
            await self.hass.async_add_executor_job(self._api.get_uuid)

        def _set_dashboard_hp_standby():
            # Only include fields documented in the ComfoClime API spec
            payload = {
                "setPointTemperature": None,
                "fanSpeed": None,
                "season": None,
                "schedule": None,
                "hpStandby": hp_standby,
            }
            headers = {"content-type": "application/json; charset=utf-8"}
            url = f"{self._api.base_url}/system/{self._api.uuid}/dashboard"
            try:
                response = requests.put(url, json=payload, timeout=5, headers=headers)
                response.raise_for_status()
                _LOGGER.debug(f"Set hpStandby to {hp_standby}")
            except Exception as e:
                _LOGGER.error(f"Error setting hpStandby: {e}")
                raise

        await self.hass.async_add_executor_job(_set_dashboard_hp_standby)

    async def _set_dashboard_hvac_settings(self, season: int | None, hp_standby: bool) -> None:
        """Set season and hpStandby via dashboard API.

        Args:
            season: Season value (0=transitional, 1=heating, 2=cooling, None=no change)
            hp_standby: Heat pump standby state (False=off, True=active)
        """
        import requests

        if not self._api.uuid:
            await self.hass.async_add_executor_job(self._api.get_uuid)

        def _set_dashboard_hvac():
            # Only include fields documented in the ComfoClime API spec
            payload = {
                "setPointTemperature": None,
                "fanSpeed": None,
                "season": season,
                "schedule": None,
                "hpStandby": hp_standby,
            }
            headers = {"content-type": "application/json; charset=utf-8"}
            url = f"{self._api.base_url}/system/{self._api.uuid}/dashboard"
            try:
                response = requests.put(url, json=payload, timeout=5, headers=headers)
                response.raise_for_status()
                _LOGGER.debug(f"Set season to {season} and hpStandby to {hp_standby}")
            except Exception as e:
                _LOGGER.error(f"Error setting HVAC settings: {e}")
                raise

        await self.hass.async_add_executor_job(_set_dashboard_hvac)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode by updating season and hpStandby via dashboard API."""
        try:
            # Map HVAC modes to season values and hpStandby
            if hvac_mode == HVACMode.OFF:
                # Set hpStandby to false to turn off ComfoClime via heat pump
                season_value = None
                hp_standby_value = False
            elif hvac_mode == HVACMode.FAN_ONLY:
                # Set season to transitional (0)
                # Set hpStandby to false for fan only mode
                season_value = 0
                hp_standby_value = False
            elif hvac_mode == HVACMode.HEAT:
                # Set season to heating (1)
                # Set hpStandby to true to ensure device is active
                season_value = 1
                hp_standby_value = True
            elif hvac_mode == HVACMode.COOL:
                # Set season to cooling (2)
                # Set hpStandby to true to ensure device is active
                season_value = 2
                hp_standby_value = True
            else:
                _LOGGER.error(f"Unsupported HVAC mode: {hvac_mode}")
                return

            # Update season and hpStandby via dashboard API
            await self._set_dashboard_hvac_settings(season_value, hp_standby_value)

            # Request refresh of coordinators
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception(f"Failed to set HVAC mode {hvac_mode}")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode by updating temperature profile."""
        if preset_mode not in PRESET_REVERSE_MAPPING:
            _LOGGER.error(f"Unknown preset mode: {preset_mode}")
            return

        try:
            # Map preset mode to temperature profile value
            temperature_profile = PRESET_REVERSE_MAPPING[preset_mode]

            # Use working API method to set device setting
            await self.hass.async_add_executor_job(
                self._api.set_device_setting, temperature_profile
            )

            # Request refresh of coordinators
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception(f"Failed to set preset mode {preset_mode}")

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode by updating fan speed in dashboard.

        Maps fan mode strings to fanSpeed values:
        - auto: 0
        - low: 1
        - medium: 2
        - high: 3
        """
        if fan_mode not in FAN_MODE_REVERSE_MAPPING:
            _LOGGER.error(f"Unknown fan mode: {fan_mode}")
            return

        try:
            # Map fan mode to fan speed value
            fan_speed = FAN_MODE_REVERSE_MAPPING[fan_mode]

            # Use API method to set fan speed via dashboard
            # set_device_setting(temperature_profile, fan_speed)
            # First parameter (temperature_profile) is None to only update fan speed
            await self.hass.async_add_executor_job(
                self._api.set_device_setting, None, fan_speed
            )

            # Request refresh of coordinator
            await self.coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception(f"Failed to set fan mode {fan_mode}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return all interface data as extra state attributes.

        Exposes all available data from the ComfoClime API interfaces:
        - Dashboard data from /system/{UUID}/dashboard
        - Thermal profile data from /system/{UUID}/thermalprofile
        """
        attrs = {}

        # Add complete dashboard data from Dashboard API interface
        if self.coordinator.data:
            attrs["dashboard"] = self.coordinator.data

        # Add complete thermal profile data from Thermal Profile API interface
        if self._thermalprofile_coordinator.data:
            attrs["thermal_profile"] = self._thermalprofile_coordinator.data

        # Add calculated/derived values for convenience
        thermal_data = self._thermalprofile_coordinator.data
        if thermal_data:
            season_data = thermal_data.get("season", {})
            temp_data = thermal_data.get("temperature", {})
            attrs["calculated"] = {
                "season_season": season_data.get("season"),
                "season_status": season_data.get("status"),
                "temperature_status": temp_data.get("status"),
                "temperature_profile": thermal_data.get("temperatureProfile"),
                "hvac_mode": str(self.hvac_mode),
                "preset_mode": self.preset_mode,
                "temperature_mode": "automatic" if self._get_temperature_status() == 1 else "manual",
            }

        return attrs
