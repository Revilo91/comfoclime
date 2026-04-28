from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import aiohttp
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
from .entity_helper import get_access_tracking_sensors, get_device_model_type_id
from .infrastructure import AccessTracker
from .services import async_register_services

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

DOMAIN = "comfoclime"
PLATFORMS = ["sensor", "switch", "number", "select", "fan", "climate"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the ComfoClime component.

    Args:
        hass: Home Assistant instance
        config: Configuration dictionary (not used, config entry only)

    Returns:
        True if setup successful
    """
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

    # Migration: Add missing default entity options for existing setups
    # This ensures that existing configurations have all entity options
    needs_update = False
    new_options = dict(entry.options)

    if "enabled_dashboard" not in entry.options:
        from .config_flow import _get_default_entity_options

        default_options = _get_default_entity_options()
        new_options = {**entry.options, **default_options}
        needs_update = True

    # Also migrate if enabled_monitoring is missing (older configs may have other keys but not this one)
    if "enabled_monitoring" not in new_options:
        from .config_flow import _get_default_entity_options
        from .entity_helper import get_monitoring_sensors

        new_options["enabled_monitoring"] = [opt["value"] for opt in get_monitoring_sensors()]
        needs_update = True

    # Migrate legacy option keys to the current options-flow keys.
    legacy_to_current_keys = {
        "enabled_connected_telemetry": "enabled_connected_device_telemetry",
        "enabled_connected_properties": "enabled_connected_device_properties",
        "enabled_connected_definition": "enabled_connected_device_definition",
    }
    for legacy_key, current_key in legacy_to_current_keys.items():
        if current_key not in new_options and legacy_key in new_options:
            new_options[current_key] = new_options.get(legacy_key, [])
            needs_update = True

    # Legacy versions enabled all access-tracking sensors by default.
    # If we detect that exact legacy default, disable them to avoid noisy helper entities.
    legacy_access_tracking_default = {opt["value"] for opt in get_access_tracking_sensors()}
    current_access_tracking = set(new_options.get("enabled_access_tracking", []))
    if current_access_tracking == legacy_access_tracking_default:
        new_options["enabled_access_tracking"] = []
        needs_update = True

    # Migrate: add core entity toggles if missing (legacy installs have no such key)
    for core_key in ("enabled_climate", "enabled_fan"):
        if core_key not in new_options:
            new_options[core_key] = True
            needs_update = True

    if needs_update:
        hass.config_entries.async_update_entry(entry, options=new_options)
        entry.options = new_options

    # Get configuration options with defaults
    read_timeout = int(entry.options.get("read_timeout", 10))
    write_timeout = int(entry.options.get("write_timeout", 30))
    polling_interval = int(entry.options.get("polling_interval", 60))
    cache_ttl = int(entry.options.get("cache_ttl", 30))
    max_retries = int(entry.options.get("max_retries", 3))
    min_request_interval = entry.options.get("min_request_interval", 0.1)
    write_cooldown = entry.options.get("write_cooldown", 2.0)
    request_debounce = entry.options.get("request_debounce", 0.3)

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
        telemetry_interval,
        access_tracker=access_tracker,
        config_entry=entry,
    )
    _LOGGER.debug(
        "Created ComfoClimeTelemetryCoordinator with polling_interval=%s",
        telemetry_interval,
    )

    propcoordinator = ComfoClimePropertyCoordinator(
        hass,
        api,
        devices,
        property_interval,
        access_tracker=access_tracker,
        config_entry=entry,
    )
    _LOGGER.debug(
        "Created ComfoClimePropertyCoordinator with polling_interval=%s",
        property_interval,
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

    # Register services
    await async_register_services(hass, api, DOMAIN)

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
    await hass.config_entries.async_reload(entry.entry_id)
