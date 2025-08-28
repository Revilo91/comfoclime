"""Climate platform for ComfoClime integration."""
import asyncio
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# HVAC Mode Mapping basierend auf Season und Status
HVAC_MODE_MAPPING = {
    ("heating", True): HVACMode.HEAT,
    ("cooling", True): HVACMode.COOL,
    ("transition", True): HVACMode.FAN_ONLY,
    ("heating", False): HVACMode.OFF,
    ("cooling", False): HVACMode.OFF,
    ("transition", False): HVACMode.OFF,
}

# Temperature Profile Presets
PRESET_MAPPING = {
    0: "comfort",
    1: "power",
    2: "eco",
}

PRESET_REVERSE_MAPPING = {v: k for k, v in PRESET_MAPPING.items()}


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

    # Erstelle die Climate-Entität
    climate_entity = ComfoClimeClimate(
        dashboard_coordinator,
        thermalprofile_coordinator,
        api,
        config_entry.entry_id
    )

    async_add_entities([climate_entity])


class ComfoClimeClimate(CoordinatorEntity, ClimateEntity):
    """ComfoClime Climate entity."""

    def __init__(self, dashboard_coordinator, thermalprofile_coordinator, api, entry_id):
        """Initialize the climate entity."""
        super().__init__(dashboard_coordinator)
        self._api = api
        self._thermalprofile_coordinator = thermalprofile_coordinator
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_climate"
        self._attr_name = "ComfoClime Climate"
        self._attr_translation_key = "climate"

        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
        )

        # Temperature settings
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_precision = 0.5
        self._attr_target_temperature_step = 0.5

        # HVAC modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
        ]

        # Preset modes
        self._attr_preset_modes = list(PRESET_REVERSE_MAPPING.keys())

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "ComfoClime",
            "manufacturer": "Zehnder",
            "model": "ComfoClime",
        }

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        if self.coordinator.data:
            return self.coordinator.data.get("indoorTemperature")
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        thermal_data = self._thermalprofile_coordinator.data
        if not thermal_data:
            return None

        season = self._get_current_season()
        if season == "heating":
            return thermal_data.get("heatingThermalProfileSeasonData", {}).get("comfortTemperature")
        if season == "cooling":
            return thermal_data.get("coolingThermalProfileSeasonData", {}).get("comfortTemperature")
        return None

    @property
    def min_temp(self) -> float:
        """Return minimum temperature."""
        season = self._get_current_season()
        if season == "heating":
            return 15.0
        if season == "cooling":
            return 20.0
        return 15.0

    @property
    def max_temp(self) -> float:
        """Return maximum temperature."""
        season = self._get_current_season()
        if season == "heating":
            return 25.0
        if season == "cooling":
            return 28.0
        return 28.0

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        if not self.coordinator.data:
            return HVACMode.OFF

        season = self._get_current_season()
        fan_speed = self.coordinator.data.get("fanSpeed")

        # Prüfe ob System aktiv ist (Fan läuft)
        is_active = fan_speed and fan_speed != "0" and fan_speed != "standby"

        return HVAC_MODE_MAPPING.get((season, is_active), HVACMode.OFF)

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if not self.coordinator.data:
            return HVACAction.OFF

        fan_speed = self.coordinator.data.get("fanSpeed")
        if not fan_speed or fan_speed == "0" or fan_speed == "standby":
            return HVACAction.OFF

        season = self._get_current_season()
        current_temp = self.current_temperature
        target_temp = self.target_temperature

        if current_temp is None or target_temp is None:
            return HVACAction.FAN

        temp_diff = current_temp - target_temp

        if season == "heating" and temp_diff < -0.5:
            return HVACAction.HEATING
        if season == "cooling" and temp_diff > 0.5:
            return HVACAction.COOLING
        return HVACAction.FAN

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode."""
        if self.coordinator.data:
            temp_profile = self.coordinator.data.get("temperatureProfile")
            if isinstance(temp_profile, int):
                return PRESET_MAPPING.get(temp_profile)
        return None

    def _get_current_season(self) -> str:
        """Get current season from dashboard data."""
        if self.coordinator.data:
            season = self.coordinator.data.get("season")
            if season == "heating":
                return "heating"
            if season == "cooling":
                return "cooling"
            return "transition"
        return "transition"

    def _get_main_device_uuid(self) -> str | None:
        """Get the UUID of the main ComfoClime device."""
        # Try to get from the entry data
        try:
            entry_data = self.hass.data[DOMAIN][self._entry_id]
            main_device = entry_data.get("main_device")
            if main_device and main_device.get("uuid"):
                return main_device["uuid"]

            # Fallback: try to get from API
            if hasattr(self._api, "uuid") and self._api.uuid:
                return self._api.uuid

        except Exception as e:
            _LOGGER.warning(f"Could not get main device UUID: {e}")

        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        season = self._get_current_season()
        _LOGGER.info(f"Setting temperature to {temperature}°C in {season} season")

        try:
            # Basierend auf API-Dokumentation: Property 22/1/9 = heating comfort, 22/1/10 = cooling comfort
            device_uuid = self._get_main_device_uuid()
            if not device_uuid:
                _LOGGER.error("No main device UUID found")
                return

            if season == "heating":
                # Property 22/1/9: heating comfort temperature (UINT16, factor 0.1)
                temp_value = int(temperature * 10)  # Convert to 0.1°C units
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/9",
                    temp_value,
                    byte_count=2,
                    signed=False,
                    faktor=1.0
                )
            elif season == "cooling":
                # Property 22/1/10: cooling comfort temperature (UINT16, factor 0.1)
                temp_value = int(temperature * 10)  # Convert to 0.1°C units
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/10",
                    temp_value,
                    byte_count=2,
                    signed=False,
                    faktor=1.0
                )
            else:
                # In transition season, try to set heating temperature as fallback
                _LOGGER.warning("Setting temperature in transition season - using heating profile")
                temp_value = int(temperature * 10)
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/9",
                    temp_value,
                    byte_count=2,
                    signed=False,
                    faktor=1.0
                )

            # Coordinators aktualisieren
            await self._thermalprofile_coordinator.async_request_refresh()
            await self.coordinator.async_request_refresh()
            _LOGGER.info(f"Successfully set temperature to {temperature}°C")

        except Exception:
            _LOGGER.exception("Failed to set temperature")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        _LOGGER.info(f"Setting HVAC mode to {hvac_mode}")

        try:
            device_uuid = self._get_main_device_uuid()
            if not device_uuid:
                _LOGGER.error("No main device UUID found")
                return

            if hvac_mode == HVACMode.OFF:
                # System ausschalten - Fan auf standby setzen
                _LOGGER.info("Turning system OFF - setting fan to standby")
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 0
                )
            elif hvac_mode == HVACMode.HEAT:
                # Heizmodus aktivieren
                _LOGGER.info("Activating HEAT mode - setting season to heating")
                # Erst Fan aktivieren
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 1
                )
                # Season auf heating setzen (Property 22/1/3)
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/3",
                    1,  # 1 = heating
                    byte_count=1,
                    signed=False,
                    faktor=1.0
                )
                # Season mode auf manual setzen (Property 22/1/2)
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/2",
                    0,  # 0 = manual, 1 = automatic
                    byte_count=1,
                    signed=False,
                    faktor=1.0
                )
            elif hvac_mode == HVACMode.COOL:
                # Kühlmodus aktivieren
                _LOGGER.info("Activating COOL mode - setting season to cooling")
                # Erst Fan aktivieren
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 1
                )
                # Season auf cooling setzen (Property 22/1/3)
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/3",
                    2,  # 2 = cooling
                    byte_count=1,
                    signed=False,
                    faktor=1.0
                )
                # Season mode auf manual setzen (Property 22/1/2)
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/2",
                    0,  # 0 = manual, 1 = automatic
                    byte_count=1,
                    signed=False,
                    faktor=1.0
                )
            elif hvac_mode == HVACMode.FAN_ONLY:
                # Nur Lüftung aktivieren
                _LOGGER.info("Activating FAN_ONLY mode - setting season to transition")
                # Erst Fan aktivieren
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 1
                )
                # Season auf transition setzen (Property 22/1/3)
                await self._api.async_set_property_for_device(
                    self.hass,
                    device_uuid,
                    "22/1/3",
                    0,  # 0 = transition
                    byte_count=1,
                    signed=False,
                    faktor=1.0
                )

            # Kurze Pause für System-Update
            await asyncio.sleep(1)

            # Coordinators aktualisieren
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

            _LOGGER.info(f"Successfully set HVAC mode to {hvac_mode}")

        except Exception:
            _LOGGER.exception("Failed to set HVAC mode %s", hvac_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode not in PRESET_REVERSE_MAPPING:
            _LOGGER.error(f"Unknown preset mode: {preset_mode}")
            return

        temperature_profile = PRESET_REVERSE_MAPPING[preset_mode]
        _LOGGER.info(f"Setting preset mode to {preset_mode} (profile {temperature_profile})")

        try:
            await self.hass.async_add_executor_job(
                self._api.set_device_setting, temperature_profile, None
            )

            # Dashboard coordinator aktualisieren
            await self.coordinator.async_request_refresh()
            _LOGGER.info(f"Successfully set preset mode to {preset_mode}")

        except Exception:
            _LOGGER.exception("Failed to set preset mode %s", preset_mode)
