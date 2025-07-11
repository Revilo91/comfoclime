import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ComfoClimeDashboardCoordinator
from .entities.number_definitions import (
    CONNECTED_DEVICE_NUMBER_PROPERTIES,
    NUMBER_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)


class ComfoClimeClimate(CoordinatorEntity[ComfoClimeDashboardCoordinator], ClimateEntity):
    """Representation of a ComfoClime as a climate entity."""

    def __init__(self, hass, coordinator, api, device, entry):
        super().__init__(coordinator)
        self._hass = hass
        self._api = api
        self._device = device
        self._entry = entry
        self._current_speed = 0

        self._attr_has_entity_name = True
        self._attr_translation_key = "climate"
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_config_entry_id = entry.entry_id

        self.translation_key = "climate_comfoclime"
        self._hvac_mode = HVACMode.FAN_ONLY
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.FAN_ONLY]
        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
        )

        # Temperature
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._manual_temperature_conf = next(
            (element for element in NUMBER_ENTITIES if element["key"] == "temperature.manualTemperature"),
            None)
        self._attr_min_temp = self._manual_temperature_conf["min"] if self._manual_temperature_conf else 18
        self._attr_max_temp = self._manual_temperature_conf["max"] if self._manual_temperature_conf else 28
        self._attr_target_temperature_step = self._manual_temperature_conf["step"] if self._manual_temperature_conf else 0.5

        # Fan
        self._attr_fan_modes = ["Off", "Low", "Medium", "High"]
        self._attr_fan_mode = "Medium"
        self._attr_current_temperature = None

    @property
    def name(self):
        return self._name

    def set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        # Passe dies an die tatsächliche API deiner ComfoClime an:
        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.error(f"Unsupported HVAC mode: {hvac_mode}")
            return
        self._hvac_mode = hvac_mode

        if self._hvac_mode == HVACMode.OFF:
            self._api.set_device_setting(hpStandby=True)
        else:
            self._api.set_device_setting(hpStandby=False)

        if self._hvac_mode == HVACMode.FAN_ONLY:
            self._api.update_thermal_profile({"season": {"season": 0}})
        elif self._hvac_mode == HVACMode.HEAT:
            self._api.update_thermal_profile({"season": {"season": 1}})
        elif self._hvac_mode == HVACMode.COOL:
            self._api.update_thermal_profile({"season": {"season": 2}})

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if fan_mode not in self._attr_fan_modes:
            _LOGGER.error(f"Unsupported fan mode: {fan_mode}")
            return
        self._attr_fan_mode = fan_mode
        self._api.set_device_setting(fanSpeed=self._attr_fan_modes.index(fan_mode))

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.error("Temperature not provided")
            return
        if not (self._attr_min_temp <= temperature <= self._attr_max_temp):
            _LOGGER.error(f"Temperature {temperature} out of range")
            return
        self._api.update_thermal_profile({"temperature": {"manualTemperature": temperature, "status": 0}})
        self._attr_target_temperature = temperature
