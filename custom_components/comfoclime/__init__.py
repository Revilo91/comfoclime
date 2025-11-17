import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
import homeassistant.helpers.device_registry as dr

from .comfoclime_api import ComfoClimeAPI
from .coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeThermalprofileCoordinator,
)

DOMAIN = "comfoclime"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    return True  # wir nutzen keine YAML-Konfiguration mehr


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    host = entry.data["host"]
    api = ComfoClimeAPI(f"http://{host}")
    # Dashboard-Coordinator erstellen
    dashboard_coordinator = ComfoClimeDashboardCoordinator(hass, api)
    await dashboard_coordinator.async_config_entry_first_refresh()
    thermalprofile_coordinator = ComfoClimeThermalprofileCoordinator(hass, api)
    await thermalprofile_coordinator.async_config_entry_first_refresh()
    devices = await api.async_get_connected_devices(hass)
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": dashboard_coordinator,
        "tpcoordinator": thermalprofile_coordinator,
        "devices": devices,
        "main_device": next((d for d in devices if d.get("modelTypeId") == 20), None),
    }

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "switch", "number", "select", "fan", "climate"]
    )

    async def handle_set_property_service(call: ServiceCall):
        device_id = call.data["device_id"]
        path = call.data["path"]
        value = call.data["value"]
        byte_count = call.data["byte_count"]
        signed = call.data.get("signed", True)
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
                hass,
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

    async def handle_reset_system_service(call: ServiceCall):
        try:
            await api.async_reset_system(hass)
            _LOGGER.info("ComfoClime Neustart ausgelöst")
        except Exception as e:
            _LOGGER.error(f"Fehler beim Neustart des Geräts: {e}")
            raise HomeAssistantError(f"Fehler beim Neustart des Geräts: {e}")

    async def handle_set_scenario_mode_service(call: ServiceCall):
        """Handle set_scenario_mode service call."""
        entity_id = call.data["entity_id"]
        scenario = call.data["scenario"]
        duration = call.data.get("duration")

        # Get the climate entity
        climate_entity = None
        for entity in hass.data.get("climate", {}).values():
            if hasattr(entity, "entity_id") and entity.entity_id == entity_id:
                climate_entity = entity
                break

        if not climate_entity:
            # Try to find the entity via entity registry
            entity_reg = hass.helpers.entity_registry.async_get(hass)
            entity_entry = entity_reg.async_get(entity_id)
            if entity_entry:
                # Get the entity from the platform
                platform = hass.data.get(DOMAIN, {}).get(entity_entry.config_entry_id, {})
                # Since we can't easily get the entity instance, we'll call the preset mode directly
                # via the climate service
                await hass.services.async_call(
                    "climate",
                    "set_scenario_mode",
                    {
                        "entity_id": entity_id,
                        "scenario_mode": scenario,
                    },
                    blocking=True,
                )
                _LOGGER.info(f"Scenario mode {scenario} activated via climate service")
                return

        if climate_entity and hasattr(climate_entity, "async_set_scenario_mode"):
            try:
                # Call the preset mode with optional duration parameter
                await climate_entity.async_set_scenario_mode(scenario, duration=duration)
                _LOGGER.info(f"Scenario mode {scenario} set with duration {duration}s")
            except Exception as e:
                _LOGGER.error(f"Error setting scenario mode: {e}")
                raise HomeAssistantError(f"Error setting scenario mode: {e}")
        else:
            raise HomeAssistantError(f"Climate entity {entity_id} not found or does not support scenarios")

    hass.services.async_register(DOMAIN, "set_property", handle_set_property_service)
    hass.services.async_register(DOMAIN, "reset_system", handle_reset_system_service)
    hass.services.async_register(DOMAIN, "set_scenario_mode", handle_set_scenario_mode_service)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    await hass.config_entries.async_forward_entry_unload(entry, "switch")
    await hass.config_entries.async_forward_entry_unload(entry, "number")
    await hass.config_entries.async_forward_entry_unload(entry, "select")
    await hass.config_entries.async_forward_entry_unload(entry, "fan")
    await hass.config_entries.async_forward_entry_unload(entry, "climate")
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_reload_entry(hass, entry):
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
