import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)

NUMBER_ENTITIES = [
    {
        "key": "heatingThermalProfileSeasonData.comfortTemperature",
        "name": "Heating Comfort Temperature",
        "translation_key": "heating_comfort_temperature",
        "min": 15,
        "max": 25,
        "step": 0.5,
    },
    {
        "key": "heatingThermalProfileSeasonData.kneePointTemperature",
        "name": "Heating Knee Point",
        "translation_key": "heating_knee_point",
        "min": 5,
        "max": 15,
        "step": 0.5,
    },
    {
        "key": "heatingThermalProfileSeasonData.reductionDeltaTemperature",
        "name": "Heating Reduction Delta",
        "translation_key": "heating_reduction_delta",
        "min": 0,
        "max": 5,
        "step": 0.5,
    },
    {
        "key": "coolingThermalProfileSeasonData.comfortTemperature",
        "name": "Cooling Comfort Temperature",
        "translation_key": "cooling_comfort_temperature",
        "min": 20,
        "max": 28,
        "step": 0.5,
    },
    {
        "key": "coolingThermalProfileSeasonData.kneePointTemperature",
        "name": "Cooling Knee Point",
        "translation_key": "cooling_knee_point",
        "min": 15,
        "max": 25,
        "step": 0.5,
    },
    {
        "key": "coolingThermalProfileSeasonData.temperatureLimit",
        "name": "Cooling Temperature Limit",
        "translation_key": "cooling_temperature_limit",
        "min": 20,
        "max": 28,
        "step": 0.5,
    },
    {
        "key": "temperature.manualTemperature",
        "name": "Manual Comfort Temperature",
        "translation_key": "manual_comfort_temperature",
        "min": 18,
        "max": 28,
        "step": 0.5,
    },
    {
        "key": "season.heatingThresholdTemperature",
        "name": "Heating Threshold",
        "translation_key": "heating_threshold",
        "min": 5,
        "max": 15,
        "step": 0.5,
    },
    {
        "key": "season.coolingThresholdTemperature",
        "name": "Cooling Threshold",
        "translation_key": "cooling_threshold",
        "min": 16,
        "max": 25,
        "step": 0.5,
    },
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    host = entry.data["host"]
    api = ComfoClimeAPI(f"http://{host}")
    await api.async_get_uuid(hass)
    devices = await api.async_get_connected_devices(hass)
    main_device = next((d for d in devices if d.get("modelTypeId") == 20), None)

    entities = [
        ComfoClimeTemperatureNumber(hass, api, conf, device=main_device, entry=entry)
        for conf in NUMBER_ENTITIES
    ]
    async_add_entities(entities, True)


class ComfoClimeTemperatureNumber(NumberEntity):
    def __init__(self, hass, api, conf, device=None, entry=None):
        self._hass = hass
        self._api = api
        self._conf = conf
        self._key_path = conf["key"].split(".")
        self._name = conf["name"]
        self._value = None
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{conf['key']}"
        # self._attr_name = conf["name"]
        self._attr_translation_key = conf["translation_key"]
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        return self._value

    @property
    def native_unit_of_measurement(self):
        return "°C"

    @property
    def native_min_value(self):
        return self._conf["min"]

    @property
    def native_max_value(self):
        return self._conf["max"]

    @property
    def native_step(self):
        return self._conf["step"]

    @property
    def device_info(self) -> DeviceInfo:
        if not self._device:
            return None

        dev_id = self._device.get("uuid")
        if not dev_id or dev_id == "NULL":
            return None  # <-- Verhindert fehlerhafte Registrierung

        return DeviceInfo(
            identifiers={(DOMAIN, self._device["uuid"])},
            name=self._device.get("displayName", "ComfoClime"),
            manufacturer="Zehnder",
            model=self._device.get("@modelType"),
            sw_version=self._device.get("version", None),
        )

    async def async_update(self):
        try:
            data = await self._api.async_get_thermal_profile(self._hass)
            val = data
            for k in self._key_path:
                val = val.get(k)
            self._value = val
        except Exception as e:
            _LOGGER.warning(f"[{self.name}] Fehler beim Update: {e}")
            self._value = None  # besser als Absturz

    def set_native_value(self, value: float):
        section = self._key_path[0]
        key = self._key_path[1]

        update = {section: {key: value}}

        try:
            self._api.update_thermal_profile(update)
            self._value = value
        except Exception as e:
            _LOGGER.error(f"Fehler beim Setzen von {self._name}: {e}")
