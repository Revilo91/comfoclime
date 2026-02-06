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

import logging
from collections.abc import Callable
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .entity_helper import (
    # get_default_enabled_individual_entities,
    # get_individual_entity_options,
    get_access_tracking_sensors,
    get_connected_device_definition_sensors,
    get_connected_device_properties_sensors,
    get_connected_device_telemetry_sensors,
    get_dashboard_sensors,
    get_monitoring_sensors,
    get_numbers,
    get_selects,
    get_switches,
    get_thermalprofile_sensors,
)
from .validators import validate_host

_LOGGER = logging.getLogger(__name__)

DOMAIN = "comfoclime"

# Default values for configuration options
DEFAULT_READ_TIMEOUT = 10
DEFAULT_WRITE_TIMEOUT = 30
DEFAULT_POLLING_INTERVAL = 60
DEFAULT_CACHE_TTL = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_MIN_REQUEST_INTERVAL = 0.1
DEFAULT_WRITE_COOLDOWN = 2.0
DEFAULT_REQUEST_DEBOUNCE = 0.3


def _get_default_entity_options() -> dict[str, Any]:
    """Get default entity options for initial setup."""
    return {
        "enabled_dashboard": [opt["value"] for opt in get_dashboard_sensors()],
        "enabled_thermalprofile": [opt["value"] for opt in get_thermalprofile_sensors()],
        "enabled_monitoring": [opt["value"] for opt in get_monitoring_sensors()],
        "enabled_connected_telemetry": [opt["value"] for opt in get_connected_device_telemetry_sensors()],
        "enabled_connected_properties": [opt["value"] for opt in get_connected_device_properties_sensors()],
        "enabled_connected_device_definition": [opt["value"] for opt in get_connected_device_definition_sensors()],
        "enabled_access_tracking": [opt["value"] for opt in get_access_tracking_sensors()],
        "enabled_switches": [opt["value"] for opt in get_switches()],
        "enabled_numbers": [opt["value"] for opt in get_numbers()],
        "enabled_selects": [opt["value"] for opt in get_selects()],
    }


class ComfoClimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ComfoClime integration.

    Validates device connection by attempting to fetch the UUID from
    the monitoring/ping endpoint. If successful, creates a config entry.
    """

    VERSION = 1

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
                    async with (
                        aiohttp.ClientSession() as session,
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
                except (TimeoutError, aiohttp.ClientError):
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

    async def _entity_selection_step(
        self,
        step_id: str,
        options_key: str,
        get_options_fn: Callable[[], list[dict]],
        next_step: str,
        description: str,
        user_input: dict[str, Any] | None = None,
        filter_prefix: str | None = None,
    ) -> FlowResult:
        """Generic entity selection step handler.

        This method consolidates the common logic for all entity selection steps,
        reducing code duplication significantly.

        Args:
            step_id: The step ID for the form
            options_key: The key to store enabled entities (e.g., "enabled_dashboard")
            get_options_fn: Function that returns list of options dicts
            next_step: Name of the step to navigate to after submission
            description: Description placeholder text
            user_input: User submitted data or None to show form
            filter_prefix: Optional prefix to filter options (e.g., "switches_")

        Returns:
            FlowResult: Form or navigation to next step
        """
        if user_input is not None:
            user_input.setdefault(options_key, [])
            _LOGGER.debug("Entity selection submitted for %s: %d items", options_key, len(user_input[options_key]))
            self._update_pending(user_input)
            return await getattr(self, f"async_step_{next_step}")()

        try:
            options = get_options_fn()
            if filter_prefix:
                options = [opt for opt in options if opt["value"].startswith(filter_prefix)]

            enabled = self._get_current_value(options_key, [opt["value"] for opt in options])

            return self.async_show_form(
                step_id=step_id,
                data_schema=vol.Schema(
                    {
                        vol.Optional(options_key, default=enabled): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=options,
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
                ),
                description_placeholders={"info": description},
            )
        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Error in entity selection step %s", step_id)
            return self.async_show_form(
                step_id=step_id,
                data_schema=vol.Schema({}),
                errors={"base": "entity_options_error"},
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

        if user_input is not None:
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
                user_input.setdefault(key, [])

            _LOGGER.info("User submitted entity selection")
            self._update_pending(user_input)
            return await self.async_step_init()

        errors: dict[str, str] = {}
        try:
            # Get all sensor options
            dashboard_options = get_dashboard_sensors()
            thermalprofile_options = get_thermalprofile_sensors()
            monitoring_options = get_monitoring_sensors()
            connected_telemetry_options = get_connected_device_telemetry_sensors()
            connected_properties_options = get_connected_device_properties_sensors()
            connected_definition_options = get_connected_device_definition_sensors()
            access_tracking_options = get_access_tracking_sensors()

            # Get switch, number, select options
            all_switch_options = get_switches()
            switch_options = [opt for opt in all_switch_options if opt["value"].startswith("switches_")]

            all_number_options = get_numbers()
            number_options = [opt for opt in all_number_options if opt["value"].startswith("numbers_")]

            all_select_options = get_selects()
            select_options = [opt for opt in all_select_options if opt["value"].startswith("selects_")]

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

            if monitoring_options:
                schema_dict[vol.Optional("enabled_monitoring", default=monitoring_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=monitoring_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

            if connected_telemetry_options:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_telemetry",
                        default=connected_telemetry_enabled,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=connected_telemetry_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

            if connected_properties_options:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_properties",
                        default=connected_properties_enabled,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=connected_properties_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

            if connected_definition_options:
                schema_dict[
                    vol.Optional(
                        "enabled_connected_device_definition",
                        default=connected_definition_enabled,
                    )
                ] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=connected_definition_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

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

            # Switches
            if switch_options:
                schema_dict[vol.Optional("enabled_switches", default=switches_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=switch_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

            # Numbers
            if number_options:
                schema_dict[vol.Optional("enabled_numbers", default=numbers_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=number_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

            # Selects
            if select_options:
                schema_dict[vol.Optional("enabled_selects", default=selects_enabled)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=select_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

            return self.async_show_form(
                step_id="entities",
                data_schema=vol.Schema(schema_dict),
                description_placeholders={
                    "info": "Wähle die Entities aus, die aktiviert werden sollen. Jede Kategorie kann separat konfiguriert werden."
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
        return await self._entity_selection_step(
            "entities_sensors_dashboard",
            "enabled_dashboard",
            get_dashboard_sensors,
            "entities_sensors",
            "Select dashboard sensors to enable.",
            user_input,
        )

    async def async_step_entities_sensors_thermalprofile(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle thermal profile sensor entity selection."""
        return await self._entity_selection_step(
            "entities_sensors_thermalprofile",
            "enabled_thermalprofile",
            get_thermalprofile_sensors,
            "entities_sensors",
            "Select thermal profile sensors to enable.",
            user_input,
        )

    async def async_step_entities_sensors_monitoring(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle monitoring sensor entity selection."""
        return await self._entity_selection_step(
            "entities_sensors_monitoring",
            "enabled_monitoring",
            get_monitoring_sensors,
            "entities_sensors",
            "Select monitoring sensors to enable.",
            user_input,
        )

    async def async_step_entities_sensors_connected_telemetry(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle connected device telemetry sensor entity selection."""
        return await self._entity_selection_step(
            "entities_sensors_connected_telemetry",
            "enabled_connected_device_telemetry",
            get_connected_device_telemetry_sensors,
            "entities_sensors",
            "Select connected device telemetry sensors to enable.",
            user_input,
        )

    async def async_step_entities_sensors_connected_properties(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle connected device properties sensor entity selection."""
        return await self._entity_selection_step(
            "entities_sensors_connected_properties",
            "enabled_connected_device_properties",
            get_connected_device_properties_sensors,
            "entities_sensors",
            "Select connected device properties sensors to enable.",
            user_input,
        )

    async def async_step_entities_sensors_connected_definition(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle connected device definition sensor entity selection."""
        return await self._entity_selection_step(
            "entities_sensors_connected_definition",
            "enabled_connected_device_definition",
            get_connected_device_definition_sensors,
            "entities_sensors",
            "Select connected device definition sensors to enable.",
            user_input,
        )

    async def async_step_entities_sensors_access_tracking(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle access tracking sensor entity selection."""
        return await self._entity_selection_step(
            "entities_sensors_access_tracking",
            "enabled_access_tracking",
            get_access_tracking_sensors,
            "entities_sensors",
            "Select access tracking sensors to enable (diagnostic only).",
            user_input,
        )

    async def async_step_entities_switches(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle switch entity selection."""
        return await self._entity_selection_step(
            "entities_switches",
            "enabled_switches",
            get_switches,
            "entities_menu",
            "Select switches to enable.",
            user_input,
            filter_prefix="switches_",
        )

    async def async_step_entities_numbers(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle number entity selection."""
        return await self._entity_selection_step(
            "entities_numbers",
            "enabled_numbers",
            get_numbers,
            "entities_menu",
            "Select number controls to enable.",
            user_input,
            filter_prefix="numbers_",
        )

    async def async_step_entities_selects(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle select entity selection."""
        return await self._entity_selection_step(
            "entities_selects",
            "enabled_selects",
            get_selects,
            "entities_menu",
            "Select list controls to enable.",
            user_input,
            filter_prefix="selects_",
        )
