from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import aiohttp
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .comfoclime_api import ComfoClimeAPI
from .coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeDefinitionCoordinator,
    ComfoClimeMonitoringCoordinator,
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from .entities.number_definitions import CONNECTED_DEVICE_NUMBER_PROPERTIES, NUMBER_ENTITIES
from .entities.select_definitions import PROPERTY_SELECT_ENTITIES, SELECT_ENTITIES
from .entities.sensor_definitions import (
    ACCESS_TRACKING_SENSORS,
    CONNECTED_DEVICE_DEFINITION_SENSORS,
    CONNECTED_DEVICE_PROPERTIES,
    CONNECTED_DEVICE_SENSORS,
    DASHBOARD_SENSORS,
    MONITORING_SENSORS,
    TELEMETRY_SENSORS,
    THERMALPROFILE_SENSORS,
)
from .entities.switch_definitions import SWITCHES
from .entity_helper import (
    get_access_tracking_sensors,
    get_device_model_type_id,
    get_device_uuid,
    is_entity_category_enabled,
    is_entity_enabled,
)
from .infrastructure import AccessTracker
from .services import async_register_services

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

DOMAIN = "comfoclime"
PLATFORMS = ["sensor", "switch", "number", "select", "fan", "climate"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


def _get_expected_unique_ids(entry: ConfigEntry, devices: list, main_device) -> set[str]:
    """Return the set of unique IDs expected for the current options state."""
    expected: set[str] = set()
    entry_id = entry.entry_id

    # Core entities
    if entry.options.get("enabled_climate", True):
        expected.add(f"{entry_id}_climate")
    if entry.options.get("enabled_fan", True):
        expected.add(f"{entry_id}_fan_speed")

    # Sensor categories from dashboard/thermalprofile/monitoring
    if is_entity_category_enabled(entry.options, "sensors", "dashboard"):
        for sensor_def in DASHBOARD_SENSORS:
            if is_entity_enabled(entry.options, "sensors", "dashboard", sensor_def):
                expected.add(f"{entry_id}_dashboard_{sensor_def.key.replace('.', '_')}")

    if is_entity_category_enabled(entry.options, "sensors", "thermalprofile"):
        for sensor_def in THERMALPROFILE_SENSORS:
            if is_entity_enabled(entry.options, "sensors", "thermalprofile", sensor_def):
                expected.add(f"{entry_id}_thermalprofile_{sensor_def.key.replace('.', '_')}")

    if is_entity_category_enabled(entry.options, "sensors", "monitoring"):
        for sensor_def in MONITORING_SENSORS:
            if is_entity_enabled(entry.options, "sensors", "monitoring", sensor_def):
                expected.add(f"{entry_id}_monitoring_{sensor_def.key.replace('.', '_')}")

    # Fixed telemetry sensors are always created for the main device when uuid is available.
    main_device_uuid = get_device_uuid(main_device) if main_device else None
    if main_device_uuid and main_device_uuid != "NULL":
        for sensor_def in TELEMETRY_SENSORS:
            expected.add(f"{entry_id}_telemetry_{sensor_def['id']}")

    diagnostics_enabled = entry.options.get("enable_diagnostics", False)

    # Connected device entities
    for device in devices:
        model_id = get_device_model_type_id(device)
        device_uuid = get_device_uuid(device)
        if not device_uuid or device_uuid == "NULL":
            continue

        telemetry_defs = CONNECTED_DEVICE_SENSORS.get(model_id, [])
        if telemetry_defs and is_entity_category_enabled(entry.options, "sensors", "connected_telemetry"):
            for sensor_def in telemetry_defs:
                if not is_entity_enabled(entry.options, "sensors", "connected_telemetry", sensor_def):
                    continue
                if sensor_def.diagnose and not diagnostics_enabled:
                    continue
                expected.add(f"{entry_id}_telemetry_{sensor_def.telemetry_id}")

        property_defs = CONNECTED_DEVICE_PROPERTIES.get(model_id, [])
        if property_defs and is_entity_category_enabled(entry.options, "sensors", "connected_properties"):
            for prop_def in property_defs:
                if not is_entity_enabled(entry.options, "sensors", "connected_properties", prop_def):
                    continue
                expected.add(f"{entry_id}_property_{prop_def.path.replace('/', '_')}")

        definition_defs = CONNECTED_DEVICE_DEFINITION_SENSORS.get(model_id, [])
        if definition_defs and is_entity_category_enabled(entry.options, "sensors", "connected_definition"):
            for def_sensor in definition_defs:
                if not is_entity_enabled(entry.options, "sensors", "connected_definition", def_sensor):
                    continue
                expected.add(f"{entry_id}_definition_{device_uuid}_{def_sensor.key}")

        number_defs = CONNECTED_DEVICE_NUMBER_PROPERTIES.get(model_id, [])
        if number_defs and is_entity_category_enabled(entry.options, "numbers", "connected_properties"):
            for number_def in number_defs:
                if not is_entity_enabled(entry.options, "numbers", "connected_properties", number_def):
                    continue
                expected.add(f"{entry_id}_property_number_{number_def.property.replace('/', '_')}")

        select_defs = PROPERTY_SELECT_ENTITIES.get(model_id, [])
        if select_defs and is_entity_category_enabled(entry.options, "selects", "connected_properties"):
            for select_def in select_defs:
                if not is_entity_enabled(entry.options, "selects", "connected_properties", select_def):
                    continue
                expected.add(f"{entry_id}_select_{select_def.path.replace('/', '_')}")

    # Access tracking sensors
    if is_entity_category_enabled(entry.options, "sensors", "access_tracking"):
        for sensor_def in ACCESS_TRACKING_SENSORS:
            if not is_entity_enabled(entry.options, "sensors", "access_tracking", sensor_def):
                continue
            if sensor_def.coordinator:
                expected.add(f"{entry_id}_access_{sensor_def.coordinator.lower()}_{sensor_def.metric}")
            else:
                expected.add(f"{entry_id}_access_{sensor_def.metric}")

    # Switches
    if is_entity_category_enabled(entry.options, "switches", "all"):
        for switch_def in SWITCHES:
            if is_entity_enabled(entry.options, "switches", "all", switch_def):
                expected.add(f"{entry_id}_switch_{switch_def.key}")

    # Numbers (thermal profile)
    if is_entity_category_enabled(entry.options, "numbers", "thermal_profile"):
        for number_def in NUMBER_ENTITIES:
            if is_entity_enabled(entry.options, "numbers", "thermal_profile", number_def):
                expected.add(f"{entry_id}_{number_def.key}")

    # Selects (thermal profile)
    if is_entity_category_enabled(entry.options, "selects", "thermal_profile"):
        for select_def in SELECT_ENTITIES:
            if is_entity_enabled(entry.options, "selects", "thermal_profile", select_def):
                expected.add(f"{entry_id}_select_{select_def.key}")

    return expected


def _cleanup_disabled_entities_from_registry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entities from the registry that are no longer expected by options."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not entry_data:
        return

    devices = entry_data.get("devices", [])
    main_device = entry_data.get("main_device")
    expected_unique_ids = _get_expected_unique_ids(entry, devices, main_device)

    registry = er.async_get(hass)
    registry_entries = er.async_entries_for_config_entry(registry, entry.entry_id)

    removed_count = 0
    for reg_entry in registry_entries:
        unique_id = reg_entry.unique_id
        if not unique_id:
            continue
        if not unique_id.startswith(f"{entry.entry_id}_"):
            continue
        if unique_id in expected_unique_ids:
            continue

        _LOGGER.debug(
            "Removing stale entity from registry after options change: entity_id=%s unique_id=%s",
            reg_entry.entity_id,
            unique_id,
        )
        registry.async_remove(reg_entry.entity_id)
        removed_count += 1

    if removed_count:
        _LOGGER.info("Removed %s stale entities after options update", removed_count)


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
    _cleanup_disabled_entities_from_registry(hass, entry)
    await hass.config_entries.async_reload(entry.entry_id)
