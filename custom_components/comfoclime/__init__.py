"""ComfoClime integration setup.

Which entities exist is decided entirely by the entity definitions and the
devices found on the ComfoNet bus. Which of them are *visible* is decided by
Home Assistant's entity registry, not by this integration - see
``config_flow.py`` for why. Entries created before that change carried the
selection in their options; ``async_migrate_entry`` translates those lists
into registry state once and then drops them.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .comfoclime_api import ComfoClimeAPI
from .config_flow import CONFIG_ENTRY_VERSION, DEFAULT_OPTIONS, LEGACY_ENTITY_OPTION_KEYS
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
from .migration import matches, unique_ids_to_disable
from .services import async_setup_services

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

DOMAIN = "comfoclime"
PLATFORMS = ["sensor", "switch", "number", "select", "fan", "climate"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a config entry to the current version.

    Version 1 stored per-entity selection in the entry options. Version 2
    hands that job to the entity registry: entities the user had deselected
    are disabled there rather than deleted, so their history, area and
    customisations survive, and the now-meaningless option keys are dropped.
    """
    if entry.version >= CONFIG_ENTRY_VERSION:
        return True

    _LOGGER.info(
        "Migrating ComfoClime config entry %s from version %s to %s",
        entry.entry_id,
        entry.version,
        CONFIG_ENTRY_VERSION,
    )

    to_disable = unique_ids_to_disable(entry.options, entry.entry_id)
    if to_disable:
        registry = er.async_get(hass)
        disabled = 0
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if reg_entry.disabled or not matches(reg_entry.unique_id or "", to_disable):
                continue
            registry.async_update_entity(
                reg_entry.entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
            )
            disabled += 1
        if disabled:
            _LOGGER.info(
                "Disabled %s entities that were deselected in the previous options flow. "
                "They can be re-enabled individually under Settings > Devices & Services",
                disabled,
            )

    new_options = {key: value for key, value in entry.options.items() if key not in LEGACY_ENTITY_OPTION_KEYS}
    for key, default in DEFAULT_OPTIONS.items():
        new_options.setdefault(key, default)

    hass.config_entries.async_update_entry(entry, options=new_options, version=CONFIG_ENTRY_VERSION)
    return True


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the ComfoClime component.

    Args:
        hass: Home Assistant instance
        config: Configuration dictionary (not used, config entry only)

    Returns:
        True if setup successful
    """
    async_setup_services(hass, DOMAIN)
    return True  # wir nutzen keine YAML-Konfiguration mehr


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ComfoClime from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry with host configuration

    Returns:
        True if setup successful

    Raises:
        ConfigEntryNotReady: If device cannot be reached or initialized
    """
    hass.data.setdefault(DOMAIN, {})

    host = entry.data["host"]
    _LOGGER.debug("Setting up ComfoClime integration for host: %s", host)

    # Get configuration options with defaults
    read_timeout = int(entry.options.get("read_timeout", 10))
    write_timeout = int(entry.options.get("write_timeout", 30))
    polling_interval = int(entry.options.get("polling_interval", 60))
    cache_ttl = int(entry.options.get("cache_ttl", 30))
    max_retries = int(entry.options.get("max_retries", 3))
    min_request_interval = entry.options.get("min_request_interval", 0.5)
    inter_sensor_delay = entry.options.get("inter_sensor_delay", 0.3)
    write_cooldown = entry.options.get("write_cooldown", 2.0)
    request_debounce = entry.options.get("request_debounce", 0.3)

    _LOGGER.debug(
        "Configuration loaded: read_timeout=%s, write_timeout=%s, polling_interval=%s, "
        "cache_ttl=%s, max_retries=%s, min_request_interval=%s, inter_sensor_delay=%s, "
        "write_cooldown=%s, request_debounce=%s",
        read_timeout,
        write_timeout,
        polling_interval,
        cache_ttl,
        max_retries,
        min_request_interval,
        inter_sensor_delay,
        write_cooldown,
        request_debounce,
    )

    # Stagger coordinator intervals to reduce sustained API pressure on devices.
    dashboard_interval = polling_interval
    thermalprofile_interval = polling_interval
    monitoring_interval = polling_interval
    telemetry_interval = polling_interval * 2
    property_interval = polling_interval * 3
    definition_interval = polling_interval * 4

    _LOGGER.debug(
        "Coordinator polling intervals: dashboard=%s, thermalprofile=%s, monitoring=%s, "
        "telemetry=%s, property=%s, definition=%s",
        dashboard_interval,
        thermalprofile_interval,
        monitoring_interval,
        telemetry_interval,
        property_interval,
        definition_interval,
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
        hass, api, dashboard_interval, access_tracker=access_tracker, config_entry=entry
    )
    _LOGGER.debug(
        "Created ComfoClimeDashboardCoordinator with polling_interval=%s",
        polling_interval,
    )

    # Create Thermalprofile-Coordinator
    thermalprofile_coordinator = ComfoClimeThermalprofileCoordinator(
        hass,
        api,
        thermalprofile_interval,
        access_tracker=access_tracker,
        config_entry=entry,
    )
    _LOGGER.debug(
        "Created ComfoClimeThermalprofileCoordinator with polling_interval=%s",
        polling_interval,
    )

    # Create Monitoring-Coordinator
    monitoring_coordinator = ComfoClimeMonitoringCoordinator(
        hass,
        api,
        monitoring_interval,
        access_tracker=access_tracker,
        config_entry=entry,
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
        definition_interval,
        access_tracker=access_tracker,
        config_entry=entry,
    )
    _LOGGER.debug(
        "Created ComfoClimeDefinitionCoordinator with polling_interval=%s",
        definition_interval,
    )

    # Parallel initialization of all coordinators for faster startup
    # NOTE: We run them sequentially with a small stagger to prevent simultaneous
    # bursts of API requests on the first poll cycle after startup.
    _LOGGER.debug("Starting staggered first refresh of all coordinators")
    coordinator_init_pairs = [
        (dashboard_coordinator, "dashboard"),
        (thermalprofile_coordinator, "thermalprofile"),
        (monitoring_coordinator, "monitoring"),
        (definitioncoordinator, "definition"),
    ]
    for coord, name in coordinator_init_pairs:
        try:
            await coord.async_config_entry_first_refresh()
        except Exception as exc:
            _LOGGER.error("Coordinator %s first refresh failed: %s", name, exc)
            raise ConfigEntryNotReady(f"Failed to initialize {name} coordinator: {exc}") from exc
        # Small stagger between coordinator starts to desynchronize their poll cycles
        await asyncio.sleep(1)

    _LOGGER.debug("Coordinator first refresh completed successfully")

    # Create telemetry and property coordinators with device list
    tlcoordinator = ComfoClimeTelemetryCoordinator(
        hass,
        api,
        devices,
        telemetry_interval,
        access_tracker=access_tracker,
        config_entry=entry,
        sensor_delay=inter_sensor_delay,
    )
    _LOGGER.debug(
        "Created ComfoClimeTelemetryCoordinator with polling_interval=%s, sensor_delay=%s",
        telemetry_interval,
        inter_sensor_delay,
    )

    propcoordinator = ComfoClimePropertyCoordinator(
        hass,
        api,
        devices,
        property_interval,
        access_tracker=access_tracker,
        config_entry=entry,
        sensor_delay=inter_sensor_delay,
    )
    _LOGGER.debug(
        "Created ComfoClimePropertyCoordinator with polling_interval=%s, sensor_delay=%s",
        property_interval,
        inter_sensor_delay,
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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload successful
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Close the API session
    if unload_ok and DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        api = hass.data[DOMAIN][entry.entry_id].get("api")
        if api:
            await api.close()

        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its options changed."""
    await hass.config_entries.async_reload(entry.entry_id)
