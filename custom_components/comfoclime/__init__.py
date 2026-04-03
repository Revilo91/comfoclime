import asyncio
import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .comfoclime_api import ComfoClimeAPI
from .coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeDefinitionCoordinator,
    ComfoClimeMonitoringCoordinator,
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from .entity_helper import get_device_model_type_id
from .infrastructure import AccessTracker
from .services import async_register_services

DOMAIN = "comfoclime"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    return True  # wir nutzen keine YAML-Konfiguration mehr


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})

    host = entry.data["host"]
    _LOGGER.debug("Setting up ComfoClime integration for host: %s", host)

    # Get configuration options with defaults (no longer stored in config entry)
    read_timeout = 10
    write_timeout = 30
    polling_interval = 60
    cache_ttl = 30
    max_retries = 3
    min_request_interval = 0.1
    write_cooldown = 2.0
    request_debounce = 0.3

    _LOGGER.debug(
        "Configuration loaded: read_timeout=%s, write_timeout=%s, polling_interval=%s, "
        "cache_ttl=%s, max_retries=%s, min_request_interval=%s, write_cooldown=%s, request_debounce=%s",
        read_timeout,
        write_timeout,
        polling_interval,
        cache_ttl,
        max_retries,
        min_request_interval,
        write_cooldown,
        request_debounce,
    )

    # Create access tracker for monitoring API access patterns
    access_tracker = AccessTracker()

    # Create API instance with configured timeouts, cache TTL, max retries, and rate limiting
    api = ComfoClimeAPI(
        f"http://{host}",
        hass=hass,
        read_timeout=read_timeout,
        write_timeout=write_timeout,
        cache_ttl=cache_ttl,
        max_retries=max_retries,
        min_request_interval=min_request_interval,
        write_cooldown=write_cooldown,
        request_debounce=request_debounce,
    )
    _LOGGER.debug("ComfoClimeAPI instance created with base_url: http://%s", host)

    # Get connected devices before creating coordinators
    try:
        devices_response = await api.async_get_connected_devices()
        devices = devices_response.devices
        _LOGGER.debug("Connected devices retrieved: %s devices found", len(devices))
    except (aiohttp.ClientError, TimeoutError) as err:
        _LOGGER.error(
            "Failed to connect to ComfoClime device at %s: %s",
            host,
            err,
        )
        await api.close()
        raise ConfigEntryNotReady(f"Unable to connect to ComfoClime device at {host}: {err}") from err

    # Create Dashboard-Coordinator
    dashboard_coordinator = ComfoClimeDashboardCoordinator(
        hass, api, polling_interval, access_tracker=access_tracker, config_entry=entry
    )
    _LOGGER.debug(
        "Created ComfoClimeDashboardCoordinator with polling_interval=%s",
        polling_interval,
    )

    # Create Thermalprofile-Coordinator
    thermalprofile_coordinator = ComfoClimeThermalprofileCoordinator(
        hass, api, polling_interval, access_tracker=access_tracker, config_entry=entry
    )
    _LOGGER.debug(
        "Created ComfoClimeThermalprofileCoordinator with polling_interval=%s",
        polling_interval,
    )

    # Create Monitoring-Coordinator
    monitoring_coordinator = ComfoClimeMonitoringCoordinator(
        hass, api, polling_interval, access_tracker=access_tracker, config_entry=entry
    )
    _LOGGER.debug(
        "Created ComfoClimeMonitoringCoordinator with polling_interval=%s",
        polling_interval,
    )

    # Create definition coordinator for device definition data (mainly for ComfoAirQ)
    definitioncoordinator = ComfoClimeDefinitionCoordinator(
        hass,
        api,
        devices,
        polling_interval,
        access_tracker=access_tracker,
        config_entry=entry,
    )
    _LOGGER.debug(
        "Created ComfoClimeDefinitionCoordinator with polling_interval=%s",
        polling_interval,
    )

    # Parallel initialization of all coordinators for faster startup
    _LOGGER.debug("Starting parallel first refresh of all coordinators")
    results = await asyncio.gather(
        dashboard_coordinator.async_config_entry_first_refresh(),
        thermalprofile_coordinator.async_config_entry_first_refresh(),
        monitoring_coordinator.async_config_entry_first_refresh(),
        definitioncoordinator.async_config_entry_first_refresh(),
        return_exceptions=True,
    )

    # Check for failures and raise ConfigEntryNotReady if any coordinator failed
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            coordinator_names = [
                "dashboard",
                "thermalprofile",
                "monitoring",
                "definition",
            ]
            _LOGGER.error("Coordinator %s first refresh failed: %s", coordinator_names[i], result)
            raise ConfigEntryNotReady(f"Failed to initialize {coordinator_names[i]} coordinator: {result}") from result

    _LOGGER.debug("Coordinator first refresh completed successfully")

    # Create telemetry and property coordinators with device list
    tlcoordinator = ComfoClimeTelemetryCoordinator(
        hass,
        api,
        devices,
        polling_interval,
        access_tracker=access_tracker,
        config_entry=entry,
    )
    _LOGGER.debug(
        "Created ComfoClimeTelemetryCoordinator with polling_interval=%s",
        polling_interval,
    )

    propcoordinator = ComfoClimePropertyCoordinator(
        hass,
        api,
        devices,
        polling_interval,
        access_tracker=access_tracker,
        config_entry=entry,
    )
    _LOGGER.debug(
        "Created ComfoClimePropertyCoordinator with polling_interval=%s",
        polling_interval,
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": dashboard_coordinator,
        "tpcoordinator": thermalprofile_coordinator,
        "monitoringcoordinator": monitoring_coordinator,
        "tlcoordinator": tlcoordinator,
        "propcoordinator": propcoordinator,
        "definitioncoordinator": definitioncoordinator,
        "access_tracker": access_tracker,
        "devices": devices,
        "main_device": next((d for d in devices if get_device_model_type_id(d) == 20), None),
    }

    # Register update listener to reload integration when options change
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "switch", "number", "select", "fan", "climate"]
    )

    # Register services
    await async_register_services(hass, api, DOMAIN)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    await hass.config_entries.async_forward_entry_unload(entry, "switch")
    await hass.config_entries.async_forward_entry_unload(entry, "number")
    await hass.config_entries.async_forward_entry_unload(entry, "select")
    await hass.config_entries.async_forward_entry_unload(entry, "fan")
    await hass.config_entries.async_forward_entry_unload(entry, "climate")

    # Close the API session
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        api = hass.data[DOMAIN][entry.entry_id].get("api")
        if api:
            await api.close()

    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def async_reload_entry(hass, entry):
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
