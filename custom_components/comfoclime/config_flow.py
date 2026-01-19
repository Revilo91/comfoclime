import logging

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
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
    get_sensors,
    get_switches,
    get_numbers,
    get_selects,
    get_thermalprofile_sensors,
)

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


class ComfoClimeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input["host"]
            url = f"http://{host}/monitoring/ping"

            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(url, timeout=5) as resp,
                ):
                    if resp.status == 200:
                        data = await resp.json()
                        if "uuid" in data:
                            return self.async_create_entry(
                                title=f"ComfoClime @ {host}",
                                data={"host": host},
                            )
                        errors["host"] = "no_uuid"
                    else:
                        errors["host"] = "no_response"
            except (TimeoutError, aiohttp.ClientError):
                errors["host"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("host", default="comfoclime.local"): str}
            ),
            errors=errors,
            last_step=False,
        )

    @classmethod
    def async_get_options_flow(cls, entry: ConfigEntry):
        return ComfoClimeOptionsFlow(entry)


class ComfoClimeOptionsFlow(OptionsFlow):
    def __init__(self, entry):
        self.entry = entry
        self._data = {}

    async def async_step_init(self, user_input=None):
        """Handle options flow - show menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "general": "⚙️ General Settings",
                "entities_menu": "📦 Entity Settings",
            },
        )

    async def async_step_entities_menu(self, user_input=None):
        """Show menu to select which entity category to configure."""
        return self.async_show_menu(
            step_id="entities_menu",
            menu_options={
                "entities_sensors": "📊 Sensors",
                "entities_switches": "🔌 Switches",
                "entities_numbers": "🔢 Numbers",
                "entities_selects": "📝 Selects",
            },
        )

    async def async_step_general(self, user_input=None):
        """Handle general configuration options - show menu."""
        return self.async_show_menu(
            step_id="general",
            menu_options={
                "general_diagnostics": "🔍 Diagnostics",
                "general_timeouts": "⏱️ Timeouts",
                "general_polling": "🔄 Polling & Caching",
                "general_rate_limiting": "🔁 Rate Limiting",
            },
        )

    async def async_step_general_diagnostics(self, user_input=None):
        """Handle diagnostic configuration options."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        return self.async_show_form(
            step_id="general_diagnostics",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "enable_diagnostics",
                        default=self.entry.options.get("enable_diagnostics", False),
                    ): bool,
                }
            ),
            description_placeholders={
                "info": "Enable diagnostic sensors for detailed API access tracking."
            },
            last_step=False,
        )

    async def async_step_general_timeouts(self, user_input=None):
        """Handle timeout configuration options."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        return self.async_show_form(
            step_id="general_timeouts",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "read_timeout",
                        default=self.entry.options.get("read_timeout", DEFAULT_READ_TIMEOUT),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=120, mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        "write_timeout",
                        default=self.entry.options.get("write_timeout", DEFAULT_WRITE_TIMEOUT),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=120, mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s"
                        )
                    ),
                }
            ),
            description_placeholders={
                "info": "Configure timeout values for read and write operations."
            },
            last_step=False,
        )

    async def async_step_general_polling(self, user_input=None):
        """Handle polling and caching configuration options."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        return self.async_show_form(
            step_id="general_polling",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "polling_interval",
                        default=self.entry.options.get("polling_interval", DEFAULT_POLLING_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=600, mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        "cache_ttl",
                        default=self.entry.options.get("cache_ttl", DEFAULT_CACHE_TTL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=300, mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        "max_retries",
                        default=self.entry.options.get("max_retries", DEFAULT_MAX_RETRIES),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=10, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
            description_placeholders={
                "info": "Configure polling intervals, caching, and retry behavior."
            },
            last_step=False,
        )

    async def async_step_general_rate_limiting(self, user_input=None):
        """Handle rate limiting configuration options."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        return self.async_show_form(
            step_id="general_rate_limiting",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "min_request_interval",
                        default=self.entry.options.get("min_request_interval", DEFAULT_MIN_REQUEST_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        "write_cooldown",
                        default=self.entry.options.get("write_cooldown", DEFAULT_WRITE_COOLDOWN),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s"
                        )
                    ),
                    vol.Optional(
                        "request_debounce",
                        default=self.entry.options.get("request_debounce", DEFAULT_REQUEST_DEBOUNCE),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0, max=2.0, step=0.1, mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s"
                        )
                    ),
                }
            ),
            description_placeholders={
                "info": "Configure request rate limiting and debouncing."
            },
            last_step=False,
        )

    async def async_step_entities_sensors(self, user_input=None):
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
            },
        )

    async def async_step_entities_sensors_dashboard(self, user_input=None):
        """Handle dashboard sensor entity selection."""
        _LOGGER.debug(f"===== async_step_entities_sensors_dashboard CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted dashboard sensor selection: {len(user_input.get('enabled_dashboard', []))} selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            dashboard_options = get_dashboard_sensors()
            dashboard_enabled = self.entry.options.get("enabled_dashboard", [opt['value'] for opt in dashboard_options])

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
                description_placeholders={
                    "info": "Select dashboard sensors to enable."
                },
                last_step=False,
                errors=errors,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_sensors_dashboard: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_dashboard",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

    async def async_step_entities_sensors_thermalprofile(self, user_input=None):
        """Handle thermal profile sensor entity selection."""
        _LOGGER.debug(f"===== async_step_entities_sensors_thermalprofile CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted thermal profile sensor selection: {len(user_input.get('enabled_thermalprofile', []))} selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            thermalprofile_options = get_thermalprofile_sensors()
            thermalprofile_enabled = self.entry.options.get("enabled_thermalprofile", [opt['value'] for opt in thermalprofile_options])

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
                description_placeholders={
                    "info": "Select thermal profile sensors to enable."
                },
                last_step=False,
                errors=errors,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_sensors_thermalprofile: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_thermalprofile",
                data_schema=vol.Schema({}),
                last_step=False,
                errors=errors,
            )

    async def async_step_entities_sensors_monitoring(self, user_input=None):
        """Handle monitoring sensor entity selection."""
        _LOGGER.debug(f"===== async_step_entities_sensors_monitoring CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted monitoring sensor selection: {len(user_input.get('enabled_monitoring', []))} selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            monitoring_options = get_monitoring_sensors()
            monitoring_enabled = self.entry.options.get("enabled_monitoring", [opt['value'] for opt in monitoring_options])

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
                description_placeholders={
                    "info": "Select monitoring sensors to enable."
                },
                last_step=False,
                errors=errors,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_sensors_monitoring: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_monitoring",
                data_schema=vol.Schema({}),
                last_step=False,
                errors=errors,
            )

    async def async_step_entities_sensors_connected_telemetry(self, user_input=None):
        """Handle connected device telemetry sensor entity selection."""
        _LOGGER.debug(f"===== async_step_entities_sensors_connected_telemetry CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted connected device telemetry sensor selection: {len(user_input.get('enabled_connected_device_telemetry', []))} selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            connected_device_telemetry_options = get_connected_device_telemetry_sensors()
            connected_device_telemetry_enabled = self.entry.options.get("enabled_connected_device_telemetry", [opt['value'] for opt in connected_device_telemetry_options])

            _LOGGER.info(f"✓ Retrieved {len(connected_device_telemetry_options)} connected device telemetry sensor options")

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
                description_placeholders={
                    "info": "Select connected device telemetry sensors to enable."
                },
                errors=errors,
                last_step=False,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_sensors_connected_telemetry: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_connected_telemetry",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

    async def async_step_entities_sensors_connected_properties(self, user_input=None):
        """Handle connected device properties sensor entity selection."""
        _LOGGER.debug(f"===== async_step_entities_sensors_connected_properties CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted connected device properties sensor selection: {len(user_input.get('enabled_connected_device_properties', []))} selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            connected_device_properties_options = get_connected_device_properties_sensors()
            connected_device_properties_enabled = self.entry.options.get("enabled_connected_device_properties", [opt['value'] for opt in connected_device_properties_options])

            _LOGGER.info(f"✓ Retrieved {len(connected_device_properties_options)} connected device properties sensor options")

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
                description_placeholders={
                    "info": "Select connected device properties sensors to enable."
                },
                errors=errors,
                last_step=False,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_sensors_connected_properties: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_connected_properties",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

    async def async_step_entities_sensors_connected_definition(self, user_input=None):
        """Handle connected device definition sensor entity selection."""
        _LOGGER.debug(f"===== async_step_entities_sensors_connected_definition CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted connected device definition sensor selection: {len(user_input.get('enabled_connected_device_definition', []))} selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            connected_device_definition_options = get_connected_device_definition_sensors()
            connected_device_definition_enabled = self.entry.options.get("enabled_connected_device_definition", [opt['value'] for opt in connected_device_definition_options])

            _LOGGER.info(f"✓ Retrieved {len(connected_device_definition_options)} connected device definition sensor options")

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
                description_placeholders={
                    "info": "Select connected device definition sensors to enable."
                },
                errors=errors,
                last_step=False,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_sensors_connected_definition: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_connected_definition",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

    async def async_step_entities_sensors_access_tracking(self, user_input=None):
        """Handle access tracking sensor entity selection."""
        _LOGGER.debug(f"===== async_step_entities_sensors_access_tracking CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted access tracking sensor selection: {len(user_input.get('enabled_access_tracking', []))} selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            access_tracking_options = get_access_tracking_sensors()
            access_tracking_enabled = self.entry.options.get("enabled_access_tracking", [opt['value'] for opt in access_tracking_options])

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
                description_placeholders={
                    "info": "Select access tracking sensors to enable (diagnostic only)."
                },
                errors=errors,
                last_step=False,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_sensors_access_tracking: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_sensors_access_tracking",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

    async def async_step_entities_switches(self, user_input=None):
        """Handle switch entity selection."""
        _LOGGER.debug(f"===== async_step_entities_switches CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted switch selection: {len(user_input.get('enabled_switches', []))} switches selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            all_options = get_switches()
            # Filter only switch options (start with "switches_")
            switch_options = [opt for opt in all_options if opt['value'].startswith('switches_')]

            current_enabled = self.entry.options.get("enabled_switches", [opt['value'] for opt in switch_options])

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
                description_placeholders={
                    "info": "Select switches to enable."
                },
                errors=errors,
                last_step=False,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_switches: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_switches",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

    async def async_step_entities_numbers(self, user_input=None):
        """Handle number entity selection."""
        _LOGGER.debug(f"===== async_step_entities_numbers CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted number selection: {len(user_input.get('enabled_numbers', []))} numbers selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            all_options = get_numbers()
            # Filter only number options (start with "numbers_")
            number_options = [opt for opt in all_options if opt['value'].startswith('numbers_')]

            current_enabled = self.entry.options.get("enabled_numbers", [opt['value'] for opt in number_options])

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
                description_placeholders={
                    "info": "Select number controls to enable."
                },
                errors=errors,
                last_step=False,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_numbers: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_numbers",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )

    async def async_step_entities_selects(self, user_input=None):
        """Handle select entity selection."""
        _LOGGER.debug(f"===== async_step_entities_selects CALLED =====")

        if user_input is not None:
            _LOGGER.info(f"User submitted select selection: {len(user_input.get('enabled_selects', []))} selects selected")
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        errors = {}
        try:
            all_options = get_selects()
            # Filter only select options (start with "selects_")
            select_options = [opt for opt in all_options if opt['value'].startswith('selects_')]

            current_enabled = self.entry.options.get("enabled_selects", [opt['value'] for opt in select_options])

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
                description_placeholders={
                    "info": "Select list controls to enable."
                },
                errors=errors,
                last_step=False,
            )
        except Exception as e:
            _LOGGER.error(f"✗ ERROR in async_step_entities_selects: {e}", exc_info=True)
            errors["base"] = "entity_options_error"
            return self.async_show_form(
                step_id="entities_selects",
                data_schema=vol.Schema({}),
                errors=errors,
                last_step=False,
            )
