"""Climate platform for ComfoClime integration."""
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

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        season = self._get_current_season()

        try:
            if season == "heating":
                updates = {
                    "heatingThermalProfileSeasonData": {
                        "comfortTemperature": temperature
                    }
                }
            if season == "cooling":
                updates = {
                    "coolingThermalProfileSeasonData": {
                        "comfortTemperature": temperature
                    }
                }
            if season == "transition":
                _LOGGER.warning("Cannot set temperature in transition season")
                return

            await self.hass.async_add_executor_job(
                self._api.update_thermal_profile, updates
            )

            # Thermal profile coordinator aktualisieren
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception("Failed to set temperature")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        try:
            if hvac_mode == HVACMode.OFF:
                # System ausschalten - auf Standby setzen
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 0
                )
            elif hvac_mode == HVACMode.HEAT:
                # Heizmodus aktivieren
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 1
                )
                # Season auf heating setzen wenn möglich
                thermal_data = self._thermalprofile_coordinator.data or {}
                season_data = thermal_data.get("season", {})
                if season_data.get("season") != 1:  # 1 = heating
                    updates = {
                        "season": {
                            "season": 1,
                            "status": 1  # manual
                        }
                    }
                    await self.hass.async_add_executor_job(
                        self._api.update_thermal_profile, updates
                    )
            elif hvac_mode == HVACMode.COOL:
                # Kühlmodus aktivieren
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 1
                )
                # Season auf cooling setzen wenn möglich
                thermal_data = self._thermalprofile_coordinator.data or {}
                season_data = thermal_data.get("season", {})
                if season_data.get("season") != 2:  # 2 = cooling
                    updates = {
                        "season": {
                            "season": 2,
                            "status": 1  # manual
                        }
                    }
                    await self.hass.async_add_executor_job(
                        self._api.update_thermal_profile, updates
                    )
            elif hvac_mode == HVACMode.FAN_ONLY:
                # Nur Lüftung aktivieren
                await self.hass.async_add_executor_job(
                    self._api.set_device_setting, None, 1
                )
                # Season auf transition setzen
                updates = {
                    "season": {
                        "season": 0,  # 0 = transition
                        "status": 1   # manual
                    }
                }
                await self.hass.async_add_executor_job(
                    self._api.update_thermal_profile, updates
                )

            # Coordinators aktualisieren
            await self.coordinator.async_request_refresh()
            await self._thermalprofile_coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception("Failed to set HVAC mode %s", hvac_mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if preset_mode not in PRESET_REVERSE_MAPPING:
            _LOGGER.error(f"Unknown preset mode: {preset_mode}")
            return

        temperature_profile = PRESET_REVERSE_MAPPING[preset_mode]

        try:
            await self.hass.async_add_executor_job(
                self._api.set_device_setting, temperature_profile, None
            )

            # Dashboard coordinator aktualisieren
            await self.coordinator.async_request_refresh()

        except Exception:
            _LOGGER.exception("Failed to set preset mode %s", preset_mode)
