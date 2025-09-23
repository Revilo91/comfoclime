import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI
from .coordinator import ComfoClimeDashboardCoordinator, ComfoClimeThermalprofileCoordinator

_LOGGER = logging.getLogger(__name__)

# HVAC Mode mapping to season modes
HVAC_TO_SEASON = {
    HVACMode.OFF: None,  # System off
    HVACMode.HEAT: 1,    # Heating season
    HVACMode.COOL: 2,    # Cooling season
    HVACMode.AUTO: 0,    # Transitional season
}

SEASON_TO_HVAC = {v: k for k, v in HVAC_TO_SEASON.items() if v is not None}
SEASON_TO_HVAC[None] = HVACMode.OFF

# Preset mode mapping to temperature profiles
PRESET_TO_PROFILE = {
    "comfort": 0,
    "power": 1,
    "eco": 2,
}

PROFILE_TO_PRESET = {v: k for k, v in PRESET_TO_PROFILE.items()}


class ComfoClimeClimate(
    CoordinatorEntity[ComfoClimeDashboardCoordinator], ClimateEntity
):
    def __init__(
        self, 
        hass: HomeAssistant, 
        dashboard_coordinator: ComfoClimeDashboardCoordinator,
        thermal_coordinator: ComfoClimeThermalprofileCoordinator,
        api: ComfoClimeAPI, 
        device: dict, 
        entry: ConfigEntry
    ):
        super().__init__(dashboard_coordinator)
        self._hass = hass
        self._dashboard_coordinator = dashboard_coordinator
        self._thermal_coordinator = thermal_coordinator
        self._api = api
        self._device = device
        self._entry = entry

        # Entity properties
        self._attr_has_entity_name = True
        self._attr_translation_key = "climate"
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_config_entry_id = entry.entry_id

        # Climate properties
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_target_temperature_step = 0.5
        self._attr_min_temp = 18.0
        self._attr_max_temp = 28.0
        
        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.PRESET_MODE
        )
        
        # Supported modes
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.AUTO,
        ]
        
        self._attr_preset_modes = list(PRESET_TO_PROFILE.keys())

        # State variables
        self._current_temperature = None
        self._target_temperature = None
        self._hvac_mode = HVACMode.OFF
        self._preset_mode = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version"),
        )

    @property
    def current_temperature(self) -> float | None:
        return self._current_temperature

    @property
    def target_temperature(self) -> float | None:
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @property
    def preset_mode(self) -> str | None:
        return self._preset_mode

    def _handle_coordinator_update(self) -> None:
        """Update entity state from coordinator data."""
        try:
            # Get dashboard data for current temperature and basic status
            dashboard_data = self._dashboard_coordinator.data
            if dashboard_data:
                self._current_temperature = dashboard_data.get("indoorTemperature")
                
                # Get season mode from dashboard data for HVAC mode
                season_value = dashboard_data.get("season")
                self._hvac_mode = SEASON_TO_HVAC.get(season_value, HVACMode.OFF)
                
                # Get temperature profile for preset mode
                temp_profile = dashboard_data.get("temperatureProfile")
                self._preset_mode = PROFILE_TO_PRESET.get(temp_profile)

            # Get thermal profile data for target temperature
            thermal_data = self._thermal_coordinator.data
            if thermal_data:
                # Check if manual temperature control is active
                temp_data = thermal_data.get("temperature", {})
                temp_status = temp_data.get("status")
                
                if temp_status == 0:  # Manual temperature mode
                    self._target_temperature = temp_data.get("manualTemperature")
                else:  # Automatic mode - get comfort temperature based on season
                    season_data = thermal_data.get("season", {})
                    current_season = season_data.get("season")
                    
                    if current_season == 1:  # Heating
                        heating_data = thermal_data.get("heatingThermalProfileSeasonData", {})
                        self._target_temperature = heating_data.get("comfortTemperature")
                    elif current_season == 2:  # Cooling
                        cooling_data = thermal_data.get("coolingThermalProfileSeasonData", {})
                        self._target_temperature = cooling_data.get("comfortTemperature")
                    else:  # Transitional or unknown
                        # Use manual temperature if available, otherwise use a default
                        self._target_temperature = temp_data.get("manualTemperature", 21.0)

        except Exception as e:
            _LOGGER.warning(f"Error updating climate entity state: {e}")

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        try:
            # Use thermal profile API to set manual temperature
            updates = {
                "temperature": {
                    "status": 0,  # Enable manual mode
                    "manualTemperature": temperature
                }
            }
            
            await self._hass.async_add_executor_job(
                self._api.update_thermal_profile, updates
            )
            
            self._target_temperature = temperature
            self.async_write_ha_state()
            
            # Refresh coordinators
            await self._thermal_coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error(f"Error setting target temperature to {temperature}: {e}")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        try:
            season_value = HVAC_TO_SEASON.get(hvac_mode)
            
            if hvac_mode == HVACMode.OFF:
                # Turn off the system - this might need special handling
                # For now, we'll set to transitional mode
                season_value = 0
                
            if season_value is not None:
                updates = {
                    "season": {
                        "season": season_value
                    }
                }
                
                await self._hass.async_add_executor_job(
                    self._api.update_thermal_profile, updates
                )
                
            self._hvac_mode = hvac_mode
            self.async_write_ha_state()
            
            # Refresh coordinators
            await self._thermal_coordinator.async_request_refresh()
            await self._dashboard_coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error(f"Error setting HVAC mode to {hvac_mode}: {e}")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        try:
            profile_value = PRESET_TO_PROFILE.get(preset_mode)
            if profile_value is None:
                _LOGGER.error(f"Unknown preset mode: {preset_mode}")
                return

            await self._hass.async_add_executor_job(
                self._api.set_device_setting, profile_value
            )
            
            self._preset_mode = preset_mode
            self.async_write_ha_state()
            
            # Refresh coordinators
            await self._dashboard_coordinator.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error(f"Error setting preset mode to {preset_mode}: {e}")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up ComfoClime climate entity."""
    try:
        # Get integration data
        data = hass.data[DOMAIN][entry.entry_id]
        api: ComfoClimeAPI = data["api"]
        dashboard_coordinator: ComfoClimeDashboardCoordinator = data["coordinator"]
        thermal_coordinator: ComfoClimeThermalprofileCoordinator = data["tpcoordinator"]
        main_device = data["main_device"]

        if not main_device:
            _LOGGER.warning("No main device found for climate entity.")
            return

        # Ensure coordinators are ready
        try:
            await dashboard_coordinator.async_config_entry_first_refresh()
            await thermal_coordinator.async_config_entry_first_refresh()
        except Exception as e:
            _LOGGER.warning(f"Could not load coordinator data for climate entity: {e}")

        # Create climate entity
        climate_entity = ComfoClimeClimate(
            hass, dashboard_coordinator, thermal_coordinator, api, main_device, entry
        )
        
        async_add_entities([climate_entity], True)
        _LOGGER.info("ComfoClime climate entity added successfully")

    except Exception as e:
        _LOGGER.error(f"Error setting up ComfoClime climate entity: {e}")