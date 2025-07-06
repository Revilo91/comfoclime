import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the ComfoClime climate device."""
    comfoclime_api = hass.data["comfoclime_api"]  # Passe dies ggf. an deine API-Initialisierung an
    async_add_entities([ComfoClimeClimate(comfoclime_api)], True)

class ComfoClimeClimate(ClimateEntity):
    """Representation of a ComfoClime as a climate entity."""

    def __init__(self, api):
        self._api = api
        self._name = "ComfoClime"
        self._hvac_mode = HVAC_MODE_OFF
        self._current_temperature = None
        self._target_temperature = None
        self._supported_features = SUPPORT_TARGET_TEMPERATURE

    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def supported_features(self):
        return self._supported_features

    @property
    def hvac_modes(self):
        return [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF]

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        # Passe dies an die tatsächliche API deiner ComfoClime an:
        await self._api.set_mode(hvac_mode)
        self._hvac_mode = hvac_mode
        await self.async_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            # Passe dies an die tatsächliche API deiner ComfoClime an:
            await self._api.set_temperature(temperature)
            self._target_temperature = temperature
            await self.async_update_ha_state()

    async def async_update(self):
        """Fetch state from the ComfoClime."""
        # Hole aktuelle Werte von deiner API:
        self._current_temperature = await self._api.get_current_temperature()
        self._target_temperature = await self._api.get_target_temperature()
        self._hvac_mode = await self._api.get_mode()
