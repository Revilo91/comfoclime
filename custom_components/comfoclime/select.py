import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)

SELECT_ENTITIES = [
    {
        "key": "temperatureProfile",
        "name": "Temperature Profile",
        "options": {0: "Comfort", 1: "Power", 2: "Eco"},
    },
    {
        "key": "season.season",
        "name": "Season Mode",
        "options": {1: "Heating", 0: "Transition", 2: "Cooling"},
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
        ComfoClimeSelect(hass, api, conf, device=main_device, entry=entry)
        for conf in SELECT_ENTITIES
    ]
    async_add_entities(entities, True)


class ComfoClimeSelect(SelectEntity):
    def __init__(self, hass, api, conf, device=None, entry=None):
        self._hass = hass
        self._api = api
        self._key = conf["key"]
        self._name = conf["name"]
        self._key_path = self._key.split(".")
        self._options_map = conf["options"]
        self._options_reverse = {v: k for k, v in self._options_map.items()}
        self._current = None
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_select_{conf['key']}"
        self._attr_name = conf["name"]

    @property
    def options(self):
        return list(self._options_map.values())

    @property
    def current_option(self):
        return self._current

    @property
    def device_info(self) -> DeviceInfo:
        if not self._device:
            return None

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
            self._current = self._options_map.get(val)
        except Exception as e:
            _LOGGER.error(f"Fehler beim Laden von {self._name}: {e}")

    def select_option(self, option: str):
        value = self._options_reverse.get(option)
        if value is None:
            return

        try:
            if self._key == "temperatureProfile":
                self._api.set_temperature_profile(value)
            else:
                section = self._key_path[0]
                key = self._key_path[1]
                updates = {section: {key: value}}
                self._api.update_thermal_profile(updates)

            self._current = option

        except Exception as e:
            _LOGGER.error(f"Fehler beim Setzen von {self._name}: {e}")
