"""Service handlers for ComfoClime integration.

This module contains all service call handlers:
- set_property: Set device properties
- reset_system: Restart ComfoClime system
- set_scenario_mode: Activate scenario modes (cooking, party, away, boost)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import aiohttp
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import voluptuous as vol
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.service import async_register_platform_entity_service

from .constants import DOMAIN, ScenarioMode
from .infrastructure import validate_byte_value, validate_duration, validate_property_path
from .models import PropertyWriteRequest

if TYPE_CHECKING:
    from .comfoclime_api import ComfoClimeAPI

_LOGGER = logging.getLogger(__name__)


START_DELAY_FORMAT = "%Y-%m-%d %H:%M:%S"

# Older services.yaml versions offered "boost" while the climate entity only knows the
# preset name "scenario_boost" (which avoids clashing with the temperature preset "boost").
SCENARIO_ALIASES = {"boost": ScenarioMode.BOOST.preset_name}


def _normalize_scenario(value: str) -> str:
    """Map legacy scenario aliases to the preset names the climate entity understands."""
    return SCENARIO_ALIASES.get(value, value)


def _validate_scenario_duration(value: float) -> float:
    """Reject non-positive durations (minutes) before any API call is made."""
    is_valid, error_message = validate_duration(value)
    if not is_valid:
        raise vol.Invalid(error_message)
    return value


def _validate_start_delay(value: str) -> str:
    """Ensure start_delay matches the datetime format the climate entity parses."""
    try:
        datetime.strptime(value, START_DELAY_FORMAT)
    except ValueError as err:
        raise vol.Invalid(f"start_delay must match YYYY-MM-DD HH:MM:SS: {value}") from err
    return value


SET_SCENARIO_MODE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("scenario"): vol.All(
            cv.string,
            _normalize_scenario,
            vol.In([mode.preset_name for mode in ScenarioMode]),
        ),
        vol.Optional("duration"): vol.All(vol.Coerce(float), _validate_scenario_duration),
        vol.Optional("start_delay"): vol.All(cv.string, _validate_start_delay),
    }
)


def _get_api_for_device(hass: HomeAssistant, domain: str, device: dr.DeviceEntry) -> ComfoClimeAPI:
    """Return the ComfoClimeAPI for the config entry that owns *device*.

    Raises HomeAssistantError when no loaded entry is found.
    """
    for entry in hass.config_entries.async_loaded_entries(domain):
        if entry.entry_id == device.config_entry_id:
            return entry.runtime_data.api
    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="device_entry_not_loaded",
    )


def _get_any_api(hass: HomeAssistant, domain: str) -> ComfoClimeAPI:
    """Return the first available ComfoClimeAPI.

    Raises HomeAssistantError when no loaded entry is found.
    """
    for entry in hass.config_entries.async_loaded_entries(domain):
        return entry.runtime_data.api
    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="no_entry_loaded",
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
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_property_path",
                translation_placeholders={"error": error_message},
            )

        # Validate byte count
        if byte_count not in (1, 2):
            _LOGGER.error("Ungültige byte_count: %s (muss 1 oder 2 sein)", byte_count)
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_byte_count",
            )

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
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_value",
                translation_placeholders={"error": error_message},
            )

        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get(device_id)
        if not device or not device.identifiers:
            _LOGGER.error("Gerät nicht gefunden oder ungültig")
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            )
        domain_check, device_uuid = next(iter(device.identifiers))
        if domain_check != domain:
            _LOGGER.error("Gerät gehört nicht zur Integration %s", domain)
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="device_wrong_integration",
                translation_placeholders={"domain": domain},
            )

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
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="property_write_failed",
                translation_placeholders={"path": path},
            ) from e

    async def handle_reset_system_service(call: ServiceCall) -> None:
        """Handle reset_system service call."""
        api = _get_any_api(hass, domain)
        try:
            await api.async_reset_system()
            _LOGGER.info("ComfoClime Neustart ausgelöst")
        except (TimeoutError, aiohttp.ClientError) as e:
            _LOGGER.exception("Fehler beim Neustart des Geräts")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reset_failed",
            ) from e

    # Register all services
    hass.services.async_register(domain, "set_property", handle_set_property_service)
    hass.services.async_register(domain, "reset_system", handle_reset_system_service)
    async_register_platform_entity_service(
        hass,
        domain,
        "set_scenario_mode",
        entity_domain=CLIMATE_DOMAIN,
        func="async_set_scenario_mode",
        schema=SET_SCENARIO_MODE_SCHEMA,
    )

    _LOGGER.debug("Registered ComfoClime services: set_property, reset_system, set_scenario_mode")
