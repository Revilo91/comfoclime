import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from .const import DOMAIN
from .coordinator import ComfoClimeDashboardCoordinator, ComfoClimeThermalprofileCoordinator
from .entities.number_definitions import (
    NUMBER_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ComfoClime climate platform."""
    data = hass.data[DOMAIN][entry.entry_id]
    dashboard_coordinator = data["coordinator"]
    thermalprofile_coordinator = data["tpcoordinator"]
    api = data["api"]
    main_device = data["main_device"]

    async_add_entities([
        ComfoClimeClimate(
            hass,
            dashboard_coordinator,
            thermalprofile_coordinator,
            api,
            main_device,
            entry
        )
    ])


class ComfoClimeClimate(ClimateEntity):
    """Representation of a ComfoClime as a climate entity."""

    def __init__(self, hass, dashboard_coordinator: ComfoClimeDashboardCoordinator, thermalprofile_coordinator: ComfoClimeThermalprofileCoordinator, api, device, entry):
        self._hass = hass
        self.dashboard_coordinator = dashboard_coordinator
        self.thermalprofile_coordinator = thermalprofile_coordinator
        self._api = api
        self._device = device
        self._entry = entry

        self._attr_has_entity_name = True
        self._attr_translation_key = "climate"
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device["uuid"])},
            "name": device["displayName"],
            "manufacturer": "Zehnder",
            "model": device["@modelType"],
        }

        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.FAN_ONLY]
        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
        )

        # Temperature
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        manual_temperature_conf = next(
            (element for element in NUMBER_ENTITIES if element["key"] == "temperature.manualTemperature"),
            None)
        self._attr_min_temp = manual_temperature_conf["min"] if manual_temperature_conf else 18
        self._attr_max_temp = manual_temperature_conf["max"] if manual_temperature_conf else 28
        self._attr_target_temperature_step = manual_temperature_conf["step"] if manual_temperature_conf else 0.5

        # Fan
        self._attr_fan_modes = ["Off", "Low", "Medium", "High"]

        # Initial state
        self._attr_hvac_mode = None
        self._attr_fan_mode = None
        self._attr_current_temperature = None
        self._attr_target_temperature = None


    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.dashboard_coordinator.last_update_success and self.thermalprofile_coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.dashboard_coordinator.async_add_listener(
                self._handle_coordinator_update
            )
        )
        self.async_on_remove(
            self.thermalprofile_coordinator.async_add_listener(
                self._handle_coordinator_update
            )
        )
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.dashboard_coordinator.data or not self.thermalprofile_coordinator.data:
            return

        dashboard = self.dashboard_coordinator.data
        thermalprofile = self.thermalprofile_coordinator.data

        # Update current temperature
        self._attr_current_temperature = dashboard.get("indoorTemperature")

        # Update target temperature
        if "setPointTemperature" in dashboard:
            self._attr_target_temperature = dashboard.get("setPointTemperature")
        elif "temperature" in thermalprofile and "manualTemperature" in thermalprofile["temperature"]:
            self._attr_target_temperature = thermalprofile["temperature"]["manualTemperature"]

        # Update fan mode
        fan_speed = dashboard.get("fanSpeed")
        if fan_speed is not None and 0 <= fan_speed < len(self._attr_fan_modes):
            self._attr_fan_mode = self._attr_fan_modes[fan_speed]

        # Update HVAC mode
        if dashboard.get("hpStandby") is True:
            self._attr_hvac_mode = HVACMode.OFF
        else:
            season = dashboard.get("season")
            if season == 0:
                self._attr_hvac_mode = HVACMode.FAN_ONLY
            elif season == 1:
                self._attr_hvac_mode = HVACMode.HEAT
            elif season == 2:
                self._attr_hvac_mode = HVACMode.COOL
            else:
                self._attr_hvac_mode = HVACMode.OFF

        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self._api.async_update_device_dashboard(self._hass, {"hpStandby": True})
        else:
            await self._api.async_update_device_dashboard(self._hass, {"hpStandby": False})

            if hvac_mode == HVACMode.FAN_ONLY:
                await self._api.async_update_thermal_profile(self._hass, {"season": {"season": 0}})
            elif hvac_mode == HVACMode.HEAT:
                await self._api.async_update_thermal_profile(self._hass, {"season": {"season": 1}})
            elif hvac_mode == HVACMode.COOL:
                await self._api.async_update_thermal_profile(self._hass, {"season": {"season": 2}})

        await self.dashboard_coordinator.async_request_refresh()
        await self.thermalprofile_coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if fan_mode not in self._attr_fan_modes:
            _LOGGER.error(f"Unsupported fan mode: {fan_mode}")
            return

        await self._api.async_update_device_dashboard(self._hass, {"fanSpeed": self._attr_fan_modes.index(fan_mode)})
        await self.dashboard_coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        await self._api.async_update_thermal_profile(self._hass, {"temperature": {"manualTemperature": temperature}})
        await self.thermalprofile_coordinator.async_request_refresh()
