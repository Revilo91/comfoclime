import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)

SWITCHES = [
    {
        "key": "season.status",
        "name": "Automatic Season Detection",
        "translation_key": "automatic_season_detection",
    },
    {
        "key": "temperature.status",
        "name": "Automatic Comfort Temperature",
        "translation_key": "automatic_comfort_temperature",
    },
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    host = entry.data["host"]
    api = ComfoClimeAPI(f"http://{host}")

    switches = []
    try:
        await api.async_get_uuid(hass)
    except Exception as e:
        _LOGGER.error(f"UUID konnte nicht geladen werden: {e}")
        return
    devices = await api.async_get_connected_devices(hass)
    main_device = next((d for d in devices if d.get("modelTypeId") == 20), None)

    switches.extend(
        ComfoClimeModeSwitch(
            hass,
            api,
            s["key"],
            s["translation_key"],
            s["name"],
            device=main_device,
            entry=entry,
        )
        for s in SWITCHES
    )

    async_add_entities(switches, True)


class ComfoClimeModeSwitch(SwitchEntity):
    def __init__(self, hass, api, key, translation_key, name, device=None, entry=None):
        self._hass = hass
        self._api = api
        self._key_path = key.split(".")
        self._name = name
        self._state = False
        self._device = device
        self._entry = entry
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_switch_{key}"
        # self._attr_name = name
        self._attr_translation_key = translation_key
        self._attr_has_entity_name = True

    @property
    def is_on(self):
        return self._state

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
        data = await self._api.async_get_thermal_profile(self._hass)
        try:
            # Zugriff auf verschachtelte Keys wie ["season"]["status"]
            val = data
            for key in self._key_path:
                val = val.get(key)
            self._state = val == 1
        except Exception as e:
            _LOGGER.error(f"Fehler beim Lesen des Switch-Zustands: {e}")
            self._state = None

    def turn_on(self, **kwargs):
        self._set_status(1)

    def turn_off(self, **kwargs):
        self._set_status(0)

    def _set_status(self, value):
        # Leeres Grundobjekt mit null
        updates = {"season": {"status": None}, "temperature": {"status": None}}

        section = self._key_path[0]
        key = self._key_path[1]

        updates[section][key] = value

        try:
            self._api.update_thermal_profile(updates)
            self._state = value == 1
        except Exception as e:
            _LOGGER.error(f"Fehler beim Setzen von {self._name}: {e}")
