import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.device_registry as dr

from .comfoclime_api import ComfoClimeAPI

DOMAIN = "comfoclime"

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    return True  # wir nutzen keine YAML-Konfiguration mehr


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    host = entry.data["host"]
    api = ComfoClimeAPI(f"http://{host}")
    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "switch", "number", "select", "fan"]
    )

    async def handle_set_property_service(call: ServiceCall):
        device_id = call.data["device_id"]
        path = call.data["path"]
        value = call.data["value"]
        byte_count = call.data["byte_count"]
        signed = call.data["signed"]
        faktor = call.data.get("faktor", 1.0)
        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if not device or not device.identifiers:
            _LOGGER.error("Gerät nicht gefunden oder ungültig")
            return
        domain, device_uuid = list(device.identifiers)[0]
        if domain != DOMAIN:
            _LOGGER.error(f"Gerät gehört nicht zur Integration {DOMAIN}")
            return
        try:
            await api.async_set_property_for_device(
                hass=hass,
                device_uuid=device_uuid,
                property_path=path,
                value=value,
                byte_count=byte_count,
                signed=signed,
                faktor=faktor,
            )
            _LOGGER.info(f"Property {path} auf {value} gesetzt für {device_uuid}")
        except Exception as e:
            _LOGGER.error(f"Fehler beim Setzen von Property {path}: {e}")
            raise HomeAssistantError(f"Fehler beim Setzen von Property {path}: {e}")

    hass.services.async_register(DOMAIN, "set_property", handle_set_property_service)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    await hass.config_entries.async_forward_entry_unload(entry, "switch")
    await hass.config_entries.async_forward_entry_unload(entry, "number")
    await hass.config_entries.async_forward_entry_unload(entry, "select")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_reload_entry(hass, entry):
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
