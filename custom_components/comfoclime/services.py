"""Service handlers for ComfoClime integration.

This module contains all service call handlers:
- set_property: Set device properties
- reset_system: Restart ComfoClime system
- set_scenario_mode: Activate scenario modes (cooking, party, away, boost)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp
import homeassistant.helpers.device_registry as dr
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError

from .infrastructure import validate_byte_value, validate_duration, validate_property_path
from .models import PropertyWriteRequest

if TYPE_CHECKING:
    from .comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)

DOMAIN = "comfoclime"


def _get_api_for_device(
    hass: HomeAssistant, domain: str, device: dr.DeviceEntry
) -> ComfoClimeAPI:
    """Return the ComfoClimeAPI for the config entry that owns *device*.

    Raises HomeAssistantError when no loaded entry is found.
    """
    for entry_id in device.config_entries:
        entry_data = hass.data.get(domain, {}).get(entry_id)
        if isinstance(entry_data, dict) and "api" in entry_data:
            return entry_data["api"]
    raise HomeAssistantError(
        f"Keine geladene ComfoClime-Integration für das Gerät gefunden"
    )


def _get_any_api(hass: HomeAssistant, domain: str) -> ComfoClimeAPI:
    """Return the first available ComfoClimeAPI.

    Raises HomeAssistantError when no loaded entry is found.
    """
    for entry_data in hass.data.get(domain, {}).values():
        if isinstance(entry_data, dict) and "api" in entry_data:
            return entry_data["api"]
    raise HomeAssistantError(
        "Keine ComfoClime-Integration ist geladen. Bitte zuerst konfigurieren."
    )


@callback
def async_setup_services(hass: HomeAssistant, domain: str = DOMAIN) -> None:
    """Register all ComfoClime services.

    Must be called from async_setup so that services are available
    across the full config-entry lifecycle (including reloads).

    Args:
        hass: Home Assistant instance
        domain: Integration domain (default: comfoclime)
    """

    async def handle_set_property_service(call: ServiceCall) -> None:
        """Handle set_property service call."""
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
        domain_check, device_uuid = next(iter(device.identifiers))
        if domain_check != domain:
            _LOGGER.error("Gerät gehört nicht zur Integration %s", domain)
            raise HomeAssistantError(f"Gerät gehört nicht zur Integration {domain}")

        api = _get_api_for_device(hass, domain, device)
        try:
            request = PropertyWriteRequest(
                device_uuid=device_uuid,
                path=path,
                value=value,
                byte_count=byte_count,
                signed=signed,
                faktor=faktor,
            )
            await api.async_set_property_for_device(request=request)
            _LOGGER.info("Property %s auf %s gesetzt für %s", path, value, device_uuid)
        except (TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.exception("Fehler beim Setzen von Property %s", path)
            raise HomeAssistantError(f"Fehler beim Setzen von Property {path}") from e

    async def handle_reset_system_service(call: ServiceCall) -> None:
        """Handle reset_system service call."""
        api = _get_any_api(hass, domain)
        try:
            await api.async_reset_system()
            _LOGGER.info("ComfoClime Neustart ausgelöst")
        except (TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.exception("Fehler beim Neustart des Geräts")
            raise HomeAssistantError("Fehler beim Neustart des Geräts") from e

    async def handle_set_scenario_mode_service(call: ServiceCall) -> None:
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

        # Validate duration if provided
        if duration is not None:
            is_valid, error_message = validate_duration(duration)
            if not is_valid:
                _LOGGER.error("Invalid duration: %s", error_message)
                raise HomeAssistantError(f"Invalid duration: {error_message}")

        # Validate start_delay if provided
        if start_delay is not None:
            is_valid, error_message = validate_duration(start_delay)
            if not is_valid:
                _LOGGER.error("Invalid start_delay: %s", error_message)
                raise HomeAssistantError(f"Invalid start_delay: {error_message}")

        # Find climate entity with matching entity_id in all ComfoClime integrations
        for _entry_id, data in hass.data.get(domain, {}).items():
            if isinstance(data, dict):  # Skip non-dict entries
                climate_entities = data.get("climate_entities", [])

                for climate_entity in climate_entities:
                    if (
                        climate_entity.entity_id == entity_id
                        and climate_entity
                        and hasattr(climate_entity, "async_set_scenario_mode")
                    ):
                        try:
                            await climate_entity.async_set_scenario_mode(
                                scenario_mode=scenario,
                                duration=duration,
                                start_delay=start_delay,
                            )
                        except (TimeoutError, aiohttp.ClientError, ValueError) as e:
                            _LOGGER.exception(
                                "Error setting scenario mode '%s' on %s", scenario, entity_id
                            )
                            raise HomeAssistantError(
                                f"Failed to set scenario mode '{scenario}'"
                            ) from e
                        else:
                            _LOGGER.info(
                                "Scenario mode '%s' activated for %s "
                                "with duration %s and start_delay %s",
                                scenario,
                                entity_id,
                                duration,
                                start_delay,
                            )
                            return

        # Entity not found or doesn't support scenarios
        raise HomeAssistantError(
            f"Climate entity '{entity_id}' not found or does not support scenario modes. "
            f"Make sure the entity exists and belongs to the ComfoClime integration."
        )

    # Register all services
    hass.services.async_register(domain, "set_property", handle_set_property_service)
    hass.services.async_register(domain, "reset_system", handle_reset_system_service)
    hass.services.async_register(domain, "set_scenario_mode", handle_set_scenario_mode_service)

    _LOGGER.debug("Registered ComfoClime services: set_property, reset_system, set_scenario_mode")
