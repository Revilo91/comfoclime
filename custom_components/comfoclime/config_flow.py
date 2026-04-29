"""ComfoClime Configuration Flow.

This module provides the Home Assistant configuration flow and options
flow for the ComfoClime integration. It handles:

    - Initial setup: Device discovery and connection validation
    - Options flow: Configuration of entities, polling intervals, timeouts, etc.

The configuration flow validates the device connection by attempting to
fetch the UUID from the monitoring endpoint. The options flow provides
a multi-step wizard for configuring:
    - Performance settings (polling intervals, timeouts, cache TTL)
    - Entity selection (sensors, switches, numbers, selects)
    - Individual entity enable/disable

Configuration data is stored in the config entry and can be modified
later through the integration options.

Example:
    >>> # User provides hostname during initial setup
    >>> host = "comfoclime.local"  # or IP address like "192.168.1.100"
    >>> # System validates connection and creates entry
    >>> # User can later configure options through Integration UI

Note:
    The configuration flow uses a stateful approach with _pending_changes
    to track modifications across multiple option steps before saving.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers import selector

from .entity_helper import (
    # get_individual_entity_options,
    get_access_tracking_sensors,
    get_connected_device_definition_sensors,
    get_connected_device_properties_sensors,
    get_connected_device_telemetry_sensors,
    get_dashboard_sensors,
    get_default_enabled_individual_entities,
    get_monitoring_sensors,
    get_numbers,
    get_selects,
    get_switches,
    get_thermalprofile_sensors,
)
from .infrastructure import validate_host

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

DOMAIN = "comfoclime"

# Default values for configuration options
DEFAULT_READ_TIMEOUT = 10
DEFAULT_WRITE_TIMEOUT = 30
DEFAULT_POLLING_INTERVAL = 60
DEFAULT_CACHE_TTL = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_MIN_REQUEST_INTERVAL = 0.5
DEFAULT_INTER_SENSOR_DELAY = 0.3
DEFAULT_WRITE_COOLDOWN = 2.0
DEFAULT_REQUEST_DEBOUNCE = 0.3

_BULK_ACTION_OPTIONS = [
    selector.SelectOptionDict(value="custom", label="Benutzerdefiniert"),
    selector.SelectOptionDict(value="all", label="Alle auswählen"),
    selector.SelectOptionDict(value="none", label="Keine auswählen"),
]


def _split_options_by_model_name(options: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Split option list by model prefix in label for visual separation."""
    grouped: dict[str, list[dict[str, str]]] = {
        "comfoclime": [],
        "comfoairq": [],
        "other": [],
    }
    for opt in options:
        label = opt.get("label", "")
        if "ComfoClime •" in label:
            grouped["comfoclime"].append(opt)
        elif "ComfoAirQ •" in label:
            grouped["comfoairq"].append(opt)
        else:
            grouped["other"].append(opt)
    return grouped


def _extract_option_values(options: list[dict[str, str]]) -> list[str]:
    """Return option values preserving list order."""
    return [opt["value"] for opt in options]


def _apply_bulk_action(action: str, selected_values: list[str], all_values: list[str]) -> list[str]:
    """Apply per-section bulk action to a selection list."""
    if action == "all":
        return list(all_values)
    if action == "none":
        return []
    return list(selected_values)


def _apply_bulk_action_to_target(
    data: dict[str, Any],
    target_key: str,
    all_values: list[str],
) -> None:
    """Apply bulk action for one target key by directly filling its list value."""
    action_key = f"{target_key}_bulk_action"
    action = data.pop(action_key, None)
    if action not in ("all", "none"):
        return

    current = data.get(target_key, [])
    if not isinstance(current, list):
        current = []
    data[target_key] = _apply_bulk_action(action, current, all_values)


def _get_default_entity_options() -> dict[str, Any]:
    """Get default entity options for initial setup."""
    default_enabled = get_default_enabled_individual_entities()

    enabled_connected_telemetry = [
        opt["value"] for opt in get_connected_device_telemetry_sensors() if opt["value"] in default_enabled
    ]

    return {
        "enabled_dashboard": [opt["value"] for opt in get_dashboard_sensors()],
        "enabled_thermalprofile": [opt["value"] for opt in get_thermalprofile_sensors()],
        "enabled_monitoring": [opt["value"] for opt in get_monitoring_sensors()],
        "enabled_connected_device_telemetry": enabled_connected_telemetry,
        "enabled_connected_device_properties": [opt["value"] for opt in get_connected_device_properties_sensors()],
        "enabled_connected_device_definition": [opt["value"] for opt in get_connected_device_definition_sensors()],
        # Access tracking sensors are diagnostic and disabled by default.
        "enabled_access_tracking": [],
        "enabled_switches": [opt["value"] for opt in get_switches()],
        "enabled_numbers": [opt["value"] for opt in get_numbers()],
        "enabled_selects": [opt["value"] for opt in get_selects()],
        # Core entities: enabled by default
        "enabled_climate": True,
        "enabled_fan": True,
    }


class ComfoClimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ComfoClime integration.

    Validates device connection by attempting to fetch the UUID from
    the monitoring/ping endpoint. If successful, creates a config entry.
    """

    VERSION = 1

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of the integration (e.g., IP address change).

        This allows users to update the host/IP address if the device has
        moved to a different network location without removing and re-adding
        the integration.

        Args:
            user_input: Dictionary with 'host' key containing new hostname or IP

        Returns:
            FlowResult: Either shows form or updates entry
        """
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            host = user_input["host"]

            # Validate host first for security
            is_valid, error_message = validate_host(host)
            if not is_valid:
                errors["host"] = "invalid_host"
                _LOGGER.warning("Invalid host provided during reconfigure: %s - %s", host, error_message)
            else:
                url = f"http://{host}/monitoring/ping"

                try:
                    connector = aiohttp.TCPConnector(ssl=False)
                    async with (
                        aiohttp.ClientSession(connector=connector) as session,
                        session.get(url, timeout=5) as resp,
                    ):
                        if resp.status == 200:
                            data = await resp.json()
                            if "uuid" in data:
                                # Update the entry with new host
                                self.hass.config_entries.async_update_entry(
                                    entry,
                                    data={"host": host},
                                )
                                # Reload the entry to apply changes
                                await self.hass.config_entries.async_reload(entry.entry_id)
                                return self.async_abort(reason="reconfigure_successful")
                            errors["host"] = "no_uuid"
                        else:
                            errors["host"] = "no_response"
                except TimeoutError, aiohttp.ClientError:
                    _LOGGER.exception("Connection error during reconfigure")
                    errors["host"] = "cannot_connect"

        # Show form with current host as default
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required("host", default=entry.data.get("host", "")): str}),
            errors=errors,
            description_placeholders={
                "current_host": entry.data.get("host", "unknown"),
            },
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step where user provides device hostname.

        Validates that the device is reachable and responds with a valid
        UUID. If validation succeeds, creates the config entry.

        Args:
            user_input: Dictionary with 'host' key containing hostname or IP

        Returns:
            FlowResult: Either shows form or creates entry
        """
        errors = {}

        if user_input is not None:
            host = user_input["host"]

            # Validate host first for security
            is_valid, error_message = validate_host(host)
            if not is_valid:
                errors["host"] = "invalid_host"
                _LOGGER.warning("Invalid host provided: %s - %s", host, error_message)
            else:
                url = f"http://{host}/monitoring/ping"

                try:
                    connector = aiohttp.TCPConnector(ssl=False)
                    async with (
                        aiohttp.ClientSession(connector=connector) as session,
                        session.get(url, timeout=5) as resp,
                    ):
                        if resp.status == 200:
                            data = await resp.json()
                            if "uuid" in data:
                                # Get default entity options for initial setup
                                default_options = _get_default_entity_options()
                                # Add default general settings
                                default_options.update(
                                    {
                                        "read_timeout": DEFAULT_READ_TIMEOUT,
                                        "write_timeout": DEFAULT_WRITE_TIMEOUT,
                                        "polling_interval": DEFAULT_POLLING_INTERVAL,
                                        "cache_ttl": DEFAULT_CACHE_TTL,
                                        "max_retries": DEFAULT_MAX_RETRIES,
                                        "min_request_interval": DEFAULT_MIN_REQUEST_INTERVAL,
                                        "inter_sensor_delay": DEFAULT_INTER_SENSOR_DELAY,
                                        "write_cooldown": DEFAULT_WRITE_COOLDOWN,
                                        "request_debounce": DEFAULT_REQUEST_DEBOUNCE,
                                    }
                                )
                                return self.async_create_entry(
                                    title=f"ComfoClime @ {host}",
                                    data={"host": host},
                                    options=default_options,
                                )
                            errors["host"] = "no_uuid"
                        else:
                            errors["host"] = "no_response"
                except TimeoutError, aiohttp.ClientError:
                    errors["host"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("host", default="comfoclime.local"): str}),
            errors=errors,
        )

    @classmethod
    def async_get_options_flow(cls, entry: ConfigEntry):
        return ComfoClimeOptionsFlow(entry)


class ComfoClimeOptionsFlow(OptionsFlow):
    """Handle options flow for ComfoClime integration.

    Provides a multi-step wizard for configuring integration options including:
        - Performance settings (polling intervals, timeouts)
        - Entity categories (sensors, switches, numbers, selects)
        - Individual entity enable/disable

    Changes are tracked in _pending_changes and only saved when the user
    completes the flow or explicitly saves.
    """

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the options flow.

        Args:
            entry: Config entry being configured
        """
        self.entry = entry
        self._data = {}
        self._pending_changes: dict[str, Any] = {}
        self._has_changes: bool = False

    def _get_current_value(self, key: str, default: Any) -> Any:
        """Get current value from pending changes first, then from saved options.

        Args:
            key: Option key to retrieve
            default: Default value if not found

        Returns:
            Current value for the option
        """
        if key in self._pending_changes:
            return self._pending_changes[key]
        return self.entry.options.get(key, default)

    def _update_pending(self, data: dict[str, Any]) -> None:
        """Update pending changes without saving.

        Args:
            data: Dictionary of changes to merge into pending changes
        """
        self._pending_changes.update(data)
        self._has_changes = True

    @staticmethod
    def _add_bulk_action_selector(schema_dict: dict, key: str) -> None:
        """Add bulk action selector for a multi-select key."""
        schema_dict[vol.Optional(f"{key}_bulk_action", default="custom")] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=_BULK_ACTION_OPTIONS,
                multiple=False,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

    async def async_step_save_and_exit(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Save all pending changes and exit."""
        new_options = {**self.entry.options, **self._pending_changes}

        _LOGGER.debug("Saving options: %s", new_options)

        return self.async_create_entry(title="", data=new_options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle options flow - show menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "general": "⚙️ Allgemeine Einstellungen",
                "entities": "📦 Entity Einstellungen",
                "save_and_exit": "💾 Speichern & Beenden",
            },
        )

    async def async_step_entities(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle all entity selection in one page with multiple selectors."""
        _LOGGER.debug("===== async_step_entities CALLED =====")

        # Get all sensor options
        dashboard_options = get_dashboard_sensors()
        thermalprofile_options = get_thermalprofile_sensors()
        monitoring_options = get_monitoring_sensors()
        connected_telemetry_options = get_connected_device_telemetry_sensors()
        connected_properties_options = get_connected_device_properties_sensors()
        connected_definition_options = get_connected_device_definition_sensors()
        access_tracking_options = get_access_tracking_sensors()

        # Split connected-device options by model for visual separation
        telemetry_by_model = _split_options_by_model_name(connected_telemetry_options)
        properties_by_model = _split_options_by_model_name(connected_properties_options)
        definition_by_model = _split_options_by_model_name(connected_definition_options)

        # Get switch, number, select options
        all_switch_options = get_switches()
        switch_options = [opt for opt in all_switch_options if opt["value"].startswith("switches_")]

        all_number_options = get_numbers()
        number_options = [opt for opt in all_number_options if opt["value"].startswith("numbers_")]

        all_select_options = get_selects()
        select_options = [opt for opt in all_select_options if opt["value"].startswith("selects_")]

        if user_input is not None:
            normalized_input = dict(user_input)

            bulk_targets = [
                ("enabled_dashboard", _extract_option_values(dashboard_options)),
                ("enabled_thermalprofile", _extract_option_values(thermalprofile_options)),
                ("enabled_monitoring", _extract_option_values(monitoring_options)),
                ("enabled_access_tracking", _extract_option_values(access_tracking_options)),
                ("enabled_switches", _extract_option_values(switch_options)),
                ("enabled_numbers", _extract_option_values(number_options)),
                ("enabled_selects", _extract_option_values(select_options)),
                (
                    "enabled_connected_device_telemetry_comfoclime",
                    _extract_option_values(telemetry_by_model["comfoclime"]),
                ),
                (
                    "enabled_connected_device_telemetry_comfoairq",
                    _extract_option_values(telemetry_by_model["comfoairq"]),
                ),
                (
                    "enabled_connected_device_telemetry_other",
                    _extract_option_values(telemetry_by_model["other"]),
                ),
                (
                    "enabled_connected_device_properties_comfoclime",
                    _extract_option_values(properties_by_model["comfoclime"]),
                ),
                (
                    "enabled_connected_device_properties_comfoairq",
                    _extract_option_values(properties_by_model["comfoairq"]),
                ),
                (
                    "enabled_connected_device_properties_other",
                    _extract_option_values(properties_by_model["other"]),
                ),
                (
                    "enabled_connected_device_definition_comfoclime",
                    _extract_option_values(definition_by_model["comfoclime"]),
                ),
                (
                    "enabled_connected_device_definition_comfoairq",
                    _extract_option_values(definition_by_model["comfoairq"]),
                ),
                (
                    "enabled_connected_device_definition_other",
                    _extract_option_values(definition_by_model["other"]),
                ),
            ]
            for target_key, all_values in bulk_targets:
                _apply_bulk_action_to_target(normalized_input, target_key, all_values)

            # Merge model-separated connected-device selections into persisted option keys
            normalized_input["enabled_connected_device_telemetry"] = (
                normalized_input.pop("enabled_connected_device_telemetry_comfoclime", [])
                + normalized_input.pop("enabled_connected_device_telemetry_comfoairq", [])
                + normalized_input.pop("enabled_connected_device_telemetry_other", [])
            )
            normalized_input["enabled_connected_device_properties"] = (
                normalized_input.pop("enabled_connected_device_properties_comfoclime", [])
                + normalized_input.pop("enabled_connected_device_properties_comfoairq", [])
                + normalized_input.pop("enabled_connected_device_properties_other", [])
            )
            normalized_input["enabled_connected_device_definition"] = (
                normalized_input.pop("enabled_connected_device_definition_comfoclime", [])
                + normalized_input.pop("enabled_connected_device_definition_comfoairq", [])
                + normalized_input.pop("enabled_connected_device_definition_other", [])
            )

            # Multi-select fields that are completely cleared by the user may be
            # omitted from user_input by the frontend. Ensure all expected
            # multi-select keys exist so an explicit empty list is saved.
            expected_keys = [
                "enabled_dashboard",
                "enabled_thermalprofile",
                "enabled_monitoring",
                "enabled_connected_device_telemetry",
                "enabled_connected_device_properties",
                "enabled_connected_device_definition",
                "enabled_access_tracking",
                "enabled_switches",
                "enabled_numbers",
                "enabled_selects",
            ]
            for key in expected_keys:
                normalized_input.setdefault(key, [])
            # Bool keys: default True when not submitted
            for key in ("enabled_climate", "enabled_fan"):
                normalized_input.setdefault(key, True)

            _LOGGER.info("User submitted entity selection")
            self._update_pending(normalized_input)
            return await self.async_step_init()

        errors: dict[str, str] = {}
        try:
            # Get current enabled values - Sensors
            dashboard_enabled = self._get_current_value(
                "enabled_dashboard", [opt["value"] for opt in dashboard_options]
            )
            thermalprofile_enabled = self._get_current_value(
                "enabled_thermalprofile",
                [opt["value"] for opt in thermalprofile_options],
            )
            monitoring_enabled = self._get_current_value(
                "enabled_monitoring", [opt["value"] for opt in monitoring_options]
            )
            connected_telemetry_enabled = self._get_current_value(
                "enabled_connected_device_telemetry",
                [opt["value"] for opt in connected_telemetry_options],
            )
            connected_properties_enabled = self._get_current_value(
                "enabled_connected_device_properties",
                [opt["value"] for opt in connected_properties_options],
            )
            connected_definition_enabled = self._get_current_value(
                "enabled_connected_device_definition",
                [opt["value"] for opt in connected_definition_options],
            )

            telemetry_comfoclime_values = _extract_option_values(telemetry_by_model["comfoclime"])
            telemetry_comfoairq_values = _extract_option_values(telemetry_by_model["comfoairq"])
            telemetry_other_values = _extract_option_values(telemetry_by_model["other"])

            properties_comfoclime_values = _extract_option_values(properties_by_model["comfoclime"])
            properties_comfoairq_values = _extract_option_values(properties_by_model["comfoairq"])
            properties_other_values = _extract_option_values(properties_by_model["other"])

            definition_comfoclime_values = _extract_option_values(definition_by_model["comfoclime"])
            definition_comfoairq_values = _extract_option_values(definition_by_model["comfoairq"])
            definition_other_values = _extract_option_values(definition_by_model["other"])

            connected_telemetry_enabled_comfoclime = [
                value for value in connected_telemetry_enabled if value in telemetry_comfoclime_values
            ]
            connected_telemetry_enabled_comfoairq = [
                value for value in connected_telemetry_enabled if value in telemetry_comfoairq_values
            ]
            connected_telemetry_enabled_other = [
                value for value in connected_telemetry_enabled if value in telemetry_other_values
            ]

            connected_properties_enabled_comfoclime = [
                value for value in connected_properties_enabled if value in properties_comfoclime_values
            ]
            connected_properties_enabled_comfoairq = [
                value for value in connected_properties_enabled if value in properties_comfoairq_values
            ]
            connected_properties_enabled_other = [
                value for value in connected_properties_enabled if value in properties_other_values
            ]

            connected_definition_enabled_comfoclime = [
                value for value in connected_definition_enabled if value in definition_comfoclime_values
            ]
            connected_definition_enabled_comfoairq = [
                value for value in connected_definition_enabled if value in definition_comfoairq_values
            ]
            connected_definition_enabled_other = [
                value for value in connected_definition_enabled if value in definition_other_values
            ]
            access_tracking_enabled = self._get_current_value(
                "enabled_access_tracking", []
            )  # Diagnostic, empty by default

            # Get current enabled values - Other entities
            switches_enabled = self._get_current_value("enabled_switches", [opt["value"] for opt in switch_options])
            numbers_enabled = self._get_current_value("enabled_numbers", [opt["value"] for opt in number_options])
            selects_enabled = self._get_current_value("enabled_selects", [opt["value"] for opt in select_options])

            _LOGGER.info(
                f"✓ Retrieved entity options: dashboard={len(dashboard_options)}, thermal={len(thermalprofile_options)}, "
                f"monitoring={len(monitoring_options)}, telemetry={len(connected_telemetry_options)}, "
                f"properties={len(connected_properties_options)}, definition={len(connected_definition_options)}, "
                f"access={len(access_tracking_options)}, switches={len(switch_options)}, "
                f"numbers={len(number_options)}, selects={len(select_options)}"
            )

            # Build schema with all entity categories
            schema_dict = {}

            # Sensors
            if dashboard_options:
                schema_dict[vol.Optional("enabled_dashboard", default=dashboard_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=dashboard_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_dashboard")

            if thermalprofile_options:
                schema_dict[vol.Optional("enabled_thermalprofile", default=thermalprofile_enabled)] = (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=thermalprofile_options,
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_thermalprofile")

            if monitoring_options:
                schema_dict[vol.Optional("enabled_monitoring", default=monitoring_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=monitoring_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_monitoring")

            if telemetry_by_model["comfoclime"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_telemetry_comfoclime",
                        default=connected_telemetry_enabled_comfoclime,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=telemetry_by_model["comfoclime"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_telemetry_comfoclime")

            if telemetry_by_model["comfoairq"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_telemetry_comfoairq",
                        default=connected_telemetry_enabled_comfoairq,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=telemetry_by_model["comfoairq"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_telemetry_comfoairq")

            if telemetry_by_model["other"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_telemetry_other",
                        default=connected_telemetry_enabled_other,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=telemetry_by_model["other"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_telemetry_other")

            if properties_by_model["comfoclime"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_properties_comfoclime",
                        default=connected_properties_enabled_comfoclime,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=properties_by_model["comfoclime"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_properties_comfoclime")

            if properties_by_model["comfoairq"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_properties_comfoairq",
                        default=connected_properties_enabled_comfoairq,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=properties_by_model["comfoairq"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_properties_comfoairq")

            if properties_by_model["other"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_properties_other",
                        default=connected_properties_enabled_other,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=properties_by_model["other"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_properties_other")

            if definition_by_model["comfoclime"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_definition_comfoclime",
                        default=connected_definition_enabled_comfoclime,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=definition_by_model["comfoclime"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_definition_comfoclime")

            if definition_by_model["comfoairq"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_definition_comfoairq",
                        default=connected_definition_enabled_comfoairq,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=definition_by_model["comfoairq"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_definition_comfoairq")

            if definition_by_model["other"]:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_definition_other",
                        default=connected_definition_enabled_other,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=definition_by_model["other"],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_connected_device_definition_other")

            if access_tracking_options:
                schema_dict[vol.Optional("enabled_access_tracking", default=access_tracking_enabled)] = (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=access_tracking_options,
                            multiple=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_access_tracking")

            # Switches
            if switch_options:
                schema_dict[vol.Optional("enabled_switches", default=switches_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=switch_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_switches")

            # Numbers
            if number_options:
                schema_dict[vol.Optional("enabled_numbers", default=numbers_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=number_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_numbers")

            # Selects
            if select_options:
                schema_dict[vol.Optional("enabled_selects", default=selects_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=select_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                self._add_bulk_action_selector(schema_dict, "enabled_selects")

            # Core entities (single bool per entity)
            schema_dict[
                vol.Optional(
                    "enabled_climate",
                    default=self._get_current_value("enabled_climate", True),
                )
            ] = selector.BooleanSelector()
            schema_dict[
                vol.Optional(
                    "enabled_fan",
                    default=self._get_current_value("enabled_fan", True),
                )
            ] = selector.BooleanSelector()

            return self.async_show_form(
                step_id="entities",
                data_schema=vol.Schema(schema_dict),
                description_placeholders={
                    "info": "Wähle die Entities aus, die aktiviert werden sollen. Pro Bereich gibt es eine Aktion für Alle/Keine/Benutzerdefiniert. Verbundene Geräte sind nach ComfoClime und ComfoAirQ getrennt."
                },
                errors=errors,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle general configuration options - show menu."""
        return self.async_show_menu(
            step_id="general",
            menu_options={
                "general_diagnostics": "🔍 Diagnostics",
                "general_timeouts": "⏱️ Timeouts",
                "general_polling": "🔄 Polling & Caching",
                "general_rate_limiting": "🔁 Rate Limiting",
                "init": "⬅️ Zurück zum Hauptmenü",
            },
        )

    async def async_step_general_diagnostics(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle diagnostic configuration options."""
        if user_input is not None:
            self._update_pending(user_input)
            return await self.async_step_general()

        return self.async_show_form(
            step_id="general_diagnostics",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "enable_diagnostics",
                        default=self._get_current_value("enable_diagnostics", False),
                    ): bool,
                }
            ),
            description_placeholders={"info": "Enable diagnostic sensors for detailed API access tracking."},
        )

    async def async_step_general_timeouts(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle timeout configuration options."""
        if user_input is not None:
            self._update_pending(user_input)
            return await self.async_step_general()

        return self.async_show_form(
            step_id="general_timeouts",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "read_timeout",
                        default=self._get_current_value("read_timeout", DEFAULT_READ_TIMEOUT),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=120,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Optional(
                        "write_timeout",
                        default=self._get_current_value("write_timeout", DEFAULT_WRITE_TIMEOUT),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=120,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                }
            ),
            description_placeholders={"info": "Configure timeout values for read and write operations."},
        )

    async def async_step_general_polling(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle polling and caching configuration options."""
        if user_input is not None:
            self._update_pending(user_input)
            return await self.async_step_general()

        return self.async_show_form(
            step_id="general_polling",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "polling_interval",
                        default=self._get_current_value("polling_interval", DEFAULT_POLLING_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10,
                            max=600,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Optional(
                        "cache_ttl",
                        default=self._get_current_value("cache_ttl", DEFAULT_CACHE_TTL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=300,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Optional(
                        "max_retries",
                        default=self._get_current_value("max_retries", DEFAULT_MAX_RETRIES),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=10, mode=selector.NumberSelectorMode.BOX)
                    ),
                }
            ),
            description_placeholders={"info": "Configure polling intervals, caching, and retry behavior."},
        )

    async def async_step_general_rate_limiting(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle rate limiting configuration options."""
        if user_input is not None:
            self._update_pending(user_input)
            return await self.async_step_general()

        return self.async_show_form(
            step_id="general_rate_limiting",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "min_request_interval",
                        default=self._get_current_value("min_request_interval", DEFAULT_MIN_REQUEST_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0,
                            max=5.0,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Optional(
                        "inter_sensor_delay",
                        default=self._get_current_value("inter_sensor_delay", DEFAULT_INTER_SENSOR_DELAY),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0,
                            max=5.0,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Optional(
                        "write_cooldown",
                        default=self._get_current_value("write_cooldown", DEFAULT_WRITE_COOLDOWN),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0,
                            max=10.0,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Optional(
                        "request_debounce",
                        default=self._get_current_value("request_debounce", DEFAULT_REQUEST_DEBOUNCE),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0,
                            max=2.0,
                            step=0.1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                }
            ),
            description_placeholders={"info": "Configure request rate limiting and debouncing."},
        )

    async def async_step_entities_sensors(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show menu to select which sensor category to configure."""
        return self.async_show_menu(
            step_id="entities_sensors",
            menu_options={
                "entities_sensors_dashboard": "📈 Dashboard Sensors",
                "entities_sensors_thermalprofile": "🌡️ Thermal Profile Sensors",
                "entities_sensors_monitoring": "⏱️ Monitoring Sensors",
                "entities_sensors_connected_telemetry": "📡 Connected Device Telemetry",
                "entities_sensors_connected_properties": "🔧 Connected Device Properties",
                "entities_sensors_connected_definition": "📋 Connected Device Definition",
                "entities_sensors_access_tracking": "🔍 Access Tracking (Diagnostic)",
                "entities_menu": "⬅️ Zurück zu Entity Settings",
            },
        )

    async def async_step_entities_menu(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show submenu for entity categories (sensors, switches, numbers, selects)."""
        return self.async_show_menu(
            step_id="entities_menu",
            menu_options={
                "entities_sensors": "📋 Sensors",
                "entities_switches": "🔌 Switches",
                "entities_numbers": "🔢 Numbers",
                "entities_selects": "📝 Selects",
                "entities": "⬅️ Back to Entity Settings",
            },
        )

    async def async_step_entities_sensors_dashboard(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle dashboard sensor entity selection."""
        _LOGGER.debug("===== async_step_entities_sensors_dashboard CALLED =====")

        if user_input is not None:
            # Ensure empty selection is preserved when frontend omits the key
            user_input.setdefault("enabled_dashboard", [])
            _LOGGER.info(
                f"User submitted dashboard sensor selection: {len(user_input.get('enabled_dashboard', []))} selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_sensors()

        errors: dict[str, str] = {}
        try:
            dashboard_options = get_dashboard_sensors()
            dashboard_enabled = self._get_current_value(
                "enabled_dashboard", [opt["value"] for opt in dashboard_options]
            )

            _LOGGER.info(f"✓ Retrieved {len(dashboard_options)} dashboard sensor options")

            return self.async_show_form(
                step_id="entities_sensors_dashboard",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_dashboard",
                            default=dashboard_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=dashboard_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select dashboard sensors to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_sensors_dashboard")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_dashboard",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_sensors_thermalprofile(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle thermal profile sensor entity selection."""
        _LOGGER.debug("===== async_step_entities_sensors_thermalprofile CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_thermalprofile", [])
            _LOGGER.info(
                f"User submitted thermal profile sensor selection: {len(user_input.get('enabled_thermalprofile', []))} selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_sensors()

        errors: dict[str, str] = {}
        try:
            thermalprofile_options = get_thermalprofile_sensors()
            thermalprofile_enabled = self._get_current_value(
                "enabled_thermalprofile",
                [opt["value"] for opt in thermalprofile_options],
            )

            _LOGGER.info(f"✓ Retrieved {len(thermalprofile_options)} thermal profile sensor options")

            return self.async_show_form(
                step_id="entities_sensors_thermalprofile",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_thermalprofile",
                            default=thermalprofile_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=thermalprofile_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select thermal profile sensors to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_sensors_thermalprofile")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_thermalprofile",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_sensors_monitoring(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle monitoring sensor entity selection."""
        _LOGGER.debug("===== async_step_entities_sensors_monitoring CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_monitoring", [])
            _LOGGER.info(
                f"User submitted monitoring sensor selection: {len(user_input.get('enabled_monitoring', []))} selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_sensors()

        errors: dict[str, str] = {}
        try:
            monitoring_options = get_monitoring_sensors()
            monitoring_enabled = self._get_current_value(
                "enabled_monitoring", [opt["value"] for opt in monitoring_options]
            )

            _LOGGER.info(f"✓ Retrieved {len(monitoring_options)} monitoring sensor options")

            return self.async_show_form(
                step_id="entities_sensors_monitoring",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_monitoring",
                            default=monitoring_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=monitoring_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select monitoring sensors to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_sensors_monitoring")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_monitoring",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_sensors_connected_telemetry(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle connected device telemetry sensor entity selection."""
        _LOGGER.debug("===== async_step_entities_sensors_connected_telemetry CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_connected_device_telemetry", [])
            _LOGGER.info(
                f"User submitted connected device telemetry sensor selection: {len(user_input.get('enabled_connected_device_telemetry', []))} selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_sensors()

        errors: dict[str, str] = {}
        try:
            connected_device_telemetry_options = get_connected_device_telemetry_sensors()
            connected_device_telemetry_enabled = self._get_current_value(
                "enabled_connected_device_telemetry",
                [opt["value"] for opt in connected_device_telemetry_options],
            )

            _LOGGER.info(
                f"✓ Retrieved {len(connected_device_telemetry_options)} connected device telemetry sensor options"
            )

            return self.async_show_form(
                step_id="entities_sensors_connected_telemetry",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_connected_device_telemetry",
                            default=connected_device_telemetry_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=connected_device_telemetry_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select connected device telemetry sensors to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_sensors_connected_telemetry")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_connected_telemetry",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_sensors_connected_properties(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle connected device properties sensor entity selection."""
        _LOGGER.debug("===== async_step_entities_sensors_connected_properties CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_connected_device_properties", [])
            _LOGGER.info(
                f"User submitted connected device properties sensor selection: {len(user_input.get('enabled_connected_device_properties', []))} selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_sensors()

        errors: dict[str, str] = {}
        try:
            connected_device_properties_options = get_connected_device_properties_sensors()
            connected_device_properties_enabled = self._get_current_value(
                "enabled_connected_device_properties",
                [opt["value"] for opt in connected_device_properties_options],
            )

            _LOGGER.info(
                f"✓ Retrieved {len(connected_device_properties_options)} connected device properties sensor options"
            )

            return self.async_show_form(
                step_id="entities_sensors_connected_properties",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_connected_device_properties",
                            default=connected_device_properties_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=connected_device_properties_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select connected device properties sensors to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_sensors_connected_properties")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_connected_properties",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_sensors_connected_definition(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle connected device definition sensor entity selection."""
        _LOGGER.debug("===== async_step_entities_sensors_connected_definition CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_connected_device_definition", [])
            _LOGGER.info(
                f"User submitted connected device definition sensor selection: {len(user_input.get('enabled_connected_device_definition', []))} selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_sensors()

        errors: dict[str, str] = {}
        try:
            connected_device_definition_options = get_connected_device_definition_sensors()
            connected_device_definition_enabled = self._get_current_value(
                "enabled_connected_device_definition",
                [opt["value"] for opt in connected_device_definition_options],
            )

            _LOGGER.info(
                f"✓ Retrieved {len(connected_device_definition_options)} connected device definition sensor options"
            )

            return self.async_show_form(
                step_id="entities_sensors_connected_definition",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_connected_device_definition",
                            default=connected_device_definition_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=connected_device_definition_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select connected device definition sensors to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_sensors_connected_definition")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_connected_definition",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_sensors_access_tracking(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle access tracking sensor entity selection."""
        _LOGGER.debug("===== async_step_entities_sensors_access_tracking CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_access_tracking", [])
            _LOGGER.info(
                f"User submitted access tracking sensor selection: {len(user_input.get('enabled_access_tracking', []))} selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_sensors()

        errors: dict[str, str] = {}
        try:
            access_tracking_options = get_access_tracking_sensors()
            access_tracking_enabled = self._get_current_value(
                "enabled_access_tracking",
                [opt["value"] for opt in access_tracking_options],
            )

            _LOGGER.info(f"✓ Retrieved {len(access_tracking_options)} access tracking sensor options")

            return self.async_show_form(
                step_id="entities_sensors_access_tracking",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_access_tracking",
                            default=access_tracking_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=access_tracking_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select access tracking sensors to enable (diagnostic only)."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_sensors_access_tracking")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_access_tracking",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_switches(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle switch entity selection."""
        _LOGGER.debug("===== async_step_entities_switches CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_switches", [])
            _LOGGER.info(
                f"User submitted switch selection: {len(user_input.get('enabled_switches', []))} switches selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_menu()

        errors: dict[str, str] = {}
        try:
            all_options = get_switches()
            # Filter only switch options (start with "switches_")
            switch_options = [opt for opt in all_options if opt["value"].startswith("switches_")]

            current_enabled = self._get_current_value("enabled_switches", [opt["value"] for opt in switch_options])

            _LOGGER.info(f"✓ Retrieved {len(switch_options)} switch options")

            return self.async_show_form(
                step_id="entities_switches",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_switches",
                            default=current_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=switch_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select switches to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_switches")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_switches",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_numbers(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle number entity selection."""
        _LOGGER.debug("===== async_step_entities_numbers CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_numbers", [])
            _LOGGER.info(
                f"User submitted number selection: {len(user_input.get('enabled_numbers', []))} numbers selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_menu()

        errors: dict[str, str] = {}
        try:
            all_options = get_numbers()
            # Filter only number options (start with "numbers_")
            number_options = [opt for opt in all_options if opt["value"].startswith("numbers_")]

            current_enabled = self._get_current_value("enabled_numbers", [opt["value"] for opt in number_options])

            _LOGGER.info(f"✓ Retrieved {len(number_options)} number options")

            return self.async_show_form(
                step_id="entities_numbers",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_numbers",
                            default=current_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=number_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select number controls to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_numbers")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_numbers",
                data_schema=vol.Schema({}),
                errors=errors,
            )

    async def async_step_entities_selects(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle select entity selection."""
        _LOGGER.debug("===== async_step_entities_selects CALLED =====")

        if user_input is not None:
            user_input.setdefault("enabled_selects", [])
            _LOGGER.info(
                f"User submitted select selection: {len(user_input.get('enabled_selects', []))} selects selected"
            )
            self._update_pending(user_input)
            return await self.async_step_entities_menu()

        errors: dict[str, str] = {}
        try:
            all_options = get_selects()
            # Filter only select options (start with "selects_")
            select_options = [opt for opt in all_options if opt["value"].startswith("selects_")]

            current_enabled = self._get_current_value("enabled_selects", [opt["value"] for opt in select_options])

            _LOGGER.info(f"✓ Retrieved {len(select_options)} select options")

            return self.async_show_form(
                step_id="entities_selects",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "enabled_selects",
                            default=current_enabled,
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=select_options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": "Select list controls to enable."},
                errors=errors,
            )
        except KeyError, TypeError, ValueError:
            _LOGGER.exception("✗ ERROR in async_step_entities_selects")
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_selects",
                data_schema=vol.Schema({}),
                errors=errors,
            )
