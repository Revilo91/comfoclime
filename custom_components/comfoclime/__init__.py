import asyncio
import logging

import aiohttp
import homeassistant.helpers.device_registry as dr
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .access_tracker import AccessTracker
from .comfoclime_api import ComfoClimeAPI
from .coordinator import (
    ComfoClimeDashboardCoordinator,
    ComfoClimeDefinitionCoordinator,
    ComfoClimeMonitoringCoordinator,
    ComfoClimePropertyCoordinator,
    ComfoClimeTelemetryCoordinator,
    ComfoClimeThermalprofileCoordinator,
)
from .validators import validate_byte_value, validate_duration, validate_property_path

DOMAIN = "comfoclime"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    return True  # wir nutzen keine YAML-Konfiguration mehr


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
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
        devices = await api.async_get_connected_devices()
        _LOGGER.debug("Connected devices retrieved: %s devices found", len(devices))
    except (aiohttp.ClientError, TimeoutError) as err:
        _LOGGER.error(
            "Failed to connect to ComfoClime device at %s: %s",
            host,
            err,
        )
        await api.close()
        raise ConfigEntryNotReady(
            f"Unable to connect to ComfoClime device at {host}: {err}"
        ) from err

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
        "main_device": next((d for d in devices if d.get("modelTypeId") == 20), None),
    }

    # Register update listener to reload integration when options change
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

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

        # Validate property path format
        is_valid, error_message = validate_property_path(path)
        if not is_valid:
            _LOGGER.error("Ungültiger Property-Pfad: %s - %s", path, error_message)
            raise HomeAssistantError(f"Ungültiger Property-Pfad: {error_message}")

        # Validate byte count
        if byte_count not in (1, 2):
            _LOGGER.error("Ungültige byte_count: %s (muss 1 oder 2 sein)", byte_count)
            raise HomeAssistantError("byte_count muss 1 oder 2 sein")

        # Validate value fits in byte count
        # Convert value with factor before validation (use same rounding as API)
        actual_value = round(value / faktor)
        is_valid, error_message = validate_byte_value(actual_value, byte_count, signed)
        if not is_valid:
            _LOGGER.error(
                "Ungültiger Wert %s für byte_count=%s, signed=%s: %s",
                actual_value,
                byte_count,
                signed,
                error_message,
            )
            raise HomeAssistantError(f"Ungültiger Wert: {error_message}")

        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if not device or not device.identifiers:
            _LOGGER.error("Gerät nicht gefunden oder ungültig")
            raise HomeAssistantError("Gerät nicht gefunden oder ungültig")
        domain, device_uuid = next(iter(device.identifiers))
        if domain != DOMAIN:
            _LOGGER.error(f"Gerät gehört nicht zur Integration {DOMAIN}")
            raise HomeAssistantError(f"Gerät gehört nicht zur Integration {DOMAIN}")
        try:
            await api.async_set_property_for_device(
                device_uuid=device_uuid,
                property_path=path,
                value=value,
                byte_count=byte_count,
                signed=signed,
                faktor=faktor,
            )
            _LOGGER.info(f"Property {path} auf {value} gesetzt für {device_uuid}")
        except (TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.exception("Fehler beim Setzen von Property %s", path)
            raise HomeAssistantError(f"Fehler beim Setzen von Property {path}") from e

    async def handle_reset_system_service(call: ServiceCall):
        try:
            await api.async_reset_system()
            _LOGGER.info("ComfoClime Neustart ausgelöst")
        except (TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.exception("Fehler beim Neustart des Geräts")
            raise HomeAssistantError("Fehler beim Neustart des Geräts") from e

    async def handle_set_scenario_mode_service(call: ServiceCall):
        """Handle set_scenario_mode service call.

        This service activates special operating modes (scenarios) on the ComfoClime
        climate entity with optional custom duration.

        Supported scenarios:
        - cooking: High ventilation for cooking (default: 30 min)
        - party: High ventilation for parties (default: 30 min)
        - away: Reduced mode for vacation (default: 24 hours)
        - scenario_boost: Maximum power boost (default: 30 min)
        """
        entity_id = call.data["entity_id"]
        scenario = call.data["scenario"]
        duration = call.data.get("duration")
        start_delay = call.data.get("start_delay")

        # Validate scenario parameter
        from .climate import SCENARIO_REVERSE_MAPPING

        valid_scenarios = list(SCENARIO_REVERSE_MAPPING.keys())
        if scenario not in valid_scenarios:
            raise HomeAssistantError(f"Invalid scenario '{scenario}'. Must be one of: {', '.join(valid_scenarios)}")

        # Validate duration if provided
        if duration is not None:
            is_valid, error_message = validate_duration(duration)
            if not is_valid:
                _LOGGER.error("Ungültige Dauer: %s - %s", duration, error_message)
                raise HomeAssistantError(f"Ungültige Dauer: {error_message}")

        # Validate start_delay format if provided
        if start_delay is not None and not isinstance(start_delay, str):
            raise HomeAssistantError(
                f"start_delay must be a datetime string (e.g. 'YYYY-MM-DD HH:MM:SS'), got: {type(start_delay).__name__}"
            )

        _LOGGER.debug(
            f"Service call: set_scenario_mode for {entity_id}, "
            f"scenario={scenario}, duration={duration}, start_delay={start_delay}"
        )

        # Get climate entity from component
        # Access the entity via the state machine's entities
        component = hass.data.get("entity_components", {}).get("climate")
        if component:
            climate_entity = component.get_entity(entity_id)

            if climate_entity and hasattr(climate_entity, "async_set_scenario_mode"):
                try:
                    await climate_entity.async_set_scenario_mode(
                        scenario_mode=scenario,
                        duration=duration,
                        start_delay=start_delay,
                    )
                except (TimeoutError, aiohttp.ClientError, ValueError) as e:
                    _LOGGER.exception("Error setting scenario mode '%s' on %s", scenario, entity_id)
                    raise HomeAssistantError(f"Failed to set scenario mode '{scenario}'") from e
                else:
                    _LOGGER.info(
                        f"Scenario mode '{scenario}' activated for {entity_id} "
                        f"with duration {duration} and start_delay {start_delay}"
                    )
                    return

        # Entity not found or doesn't support scenarios
        raise HomeAssistantError(
            f"Climate entity '{entity_id}' not found or does not support scenario modes. "
            f"Make sure the entity exists and belongs to the ComfoClime integration."
        )

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
