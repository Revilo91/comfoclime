"""ComfoClime configuration and options flow.

Setup asks for one thing: the host or IP of the ComfoClime unit. The
connection is validated by fetching a UUID from ``/monitoring/ping``.

The options flow deliberately does **not** offer entity selection. Home
Assistant's entity registry already does that job, per entity and per
device, with far better UX than a config flow can offer: entities the user
disables there are never added to ``hass``, so they also stop costing API
requests (telemetry and property entities register with their coordinator
in ``async_added_to_hass``). What remains here is the handful of settings
Home Assistant has no opinion about: timeouts, polling and rate limiting.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers import selector

from .constants import API_DEFAULTS
from .infrastructure import validate_host

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

DOMAIN = "comfoclime"

# Config entry version. Bumped to 2 when per-entity selection moved out of
# the options and into the entity registry; see async_migrate_entry.
CONFIG_ENTRY_VERSION = 2

DEFAULT_READ_TIMEOUT = API_DEFAULTS.READ_TIMEOUT
DEFAULT_WRITE_TIMEOUT = API_DEFAULTS.WRITE_TIMEOUT
DEFAULT_POLLING_INTERVAL = API_DEFAULTS.POLLING_INTERVAL
DEFAULT_CACHE_TTL = API_DEFAULTS.CACHE_TTL
DEFAULT_MAX_RETRIES = API_DEFAULTS.MAX_RETRIES
DEFAULT_MIN_REQUEST_INTERVAL = API_DEFAULTS.MIN_REQUEST_INTERVAL
DEFAULT_INTER_SENSOR_DELAY = API_DEFAULTS.INTER_SENSOR_DELAY
DEFAULT_WRITE_COOLDOWN = API_DEFAULTS.WRITE_COOLDOWN
DEFAULT_REQUEST_DEBOUNCE = API_DEFAULTS.REQUEST_DEBOUNCE

# Option keys written by the pre-2.x options flow. They are stripped during
# migration; their values are translated into entity-registry disabled state.
LEGACY_ENTITY_OPTION_KEYS = (
    "enabled_entities",
    "enabled_dashboard",
    "enabled_thermalprofile",
    "enabled_monitoring",
    "enabled_connected_device_telemetry",
    "enabled_connected_device_properties",
    "enabled_connected_device_definition",
    "enabled_connected_telemetry",
    "enabled_connected_properties",
    "enabled_connected_definition",
    "enabled_access_tracking",
    "enabled_switches",
    "enabled_numbers",
    "enabled_selects",
    "enabled_climate",
    "enabled_fan",
    "enable_diagnostics",
)

DEFAULT_OPTIONS: dict[str, Any] = {
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


async def _async_probe_host(host: str) -> str | None:
    """Return an error key if the host is not a reachable ComfoClime, else None."""
    is_valid, error_message = validate_host(host)
    if not is_valid:
        _LOGGER.warning("Invalid host provided: %s - %s", host, error_message)
        return "invalid_host"

    url = f"http://{host}/monitoring/ping"
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with (
            aiohttp.ClientSession(connector=connector) as session,
            session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp,
        ):
            if resp.status != 200:
                return "no_response"
            data = await resp.json()
            if "uuid" not in data:
                return "no_uuid"
    except TimeoutError, aiohttp.ClientError:
        _LOGGER.debug("Connection error while probing %s", host, exc_info=True)
        return "cannot_connect"
    return None


class ComfoClimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the ComfoClime integration."""

    VERSION = CONFIG_ENTRY_VERSION

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Ask for the host and validate that a ComfoClime answers there."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input["host"]
            error = await _async_probe_host(host)
            if error is None:
                return self.async_create_entry(
                    title=f"ComfoClime @ {host}",
                    data={"host": host},
                    options=dict(DEFAULT_OPTIONS),
                )
            errors["host"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("host", default="comfoclime.local"): str}),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Update the host of an existing entry, e.g. after a DHCP change."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            host = user_input["host"]
            error = await _async_probe_host(host)
            if error is None:
                self.hass.config_entries.async_update_entry(entry, data={"host": host})
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")
            errors["host"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required("host", default=entry.data.get("host", "")): str}),
            errors=errors,
            description_placeholders={"current_host": entry.data.get("host", "unknown")},
        )

    @classmethod
    def async_get_options_flow(cls, entry: ConfigEntry) -> OptionsFlow:
        return ComfoClimeOptionsFlow(entry)


class ComfoClimeOptionsFlow(OptionsFlow):
    """Options flow for polling and connection tuning.

    Entity selection lives in Home Assistant's entity registry, not here.
    """

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    def _current(self, key: str) -> Any:
        """Return the stored value for an option, falling back to its default."""
        return self.entry.options.get(key, DEFAULT_OPTIONS[key])

    def _seconds(
        self,
        key: str,
        *,
        minimum: float,
        maximum: float,
        step: float | None = None,
    ) -> tuple[Any, selector.NumberSelector]:
        """Build a seconds-valued number selector defaulting to the stored value."""
        config = selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="s",
        )
        # NumberSelectorConfig rejects an explicit None, so only whole-second
        # fields get to omit the step entirely.
        if step is not None:
            config["step"] = step

        return (
            vol.Optional(key, default=self._current(key)),
            selector.NumberSelector(config),
        )

    def _save(self, user_input: dict[str, Any]) -> FlowResult:
        """Merge one section's input into the stored options and finish."""
        return self.async_create_entry(title="", data={**self.entry.options, **user_input})

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["timeouts", "polling", "rate_limiting"],
        )

    async def async_step_timeouts(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Read and write timeouts."""
        if user_input is not None:
            return self._save(user_input)

        read_key, read_sel = self._seconds("read_timeout", minimum=1, maximum=120)
        write_key, write_sel = self._seconds("write_timeout", minimum=1, maximum=120)
        return self.async_show_form(
            step_id="timeouts",
            data_schema=vol.Schema({read_key: read_sel, write_key: write_sel}),
        )

    async def async_step_polling(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Polling interval, cache lifetime and retry count."""
        if user_input is not None:
            return self._save(user_input)

        poll_key, poll_sel = self._seconds("polling_interval", minimum=10, maximum=600)
        cache_key, cache_sel = self._seconds("cache_ttl", minimum=0, maximum=300)
        return self.async_show_form(
            step_id="polling",
            data_schema=vol.Schema(
                {
                    poll_key: poll_sel,
                    cache_key: cache_sel,
                    vol.Optional("max_retries", default=self._current("max_retries")): selector.NumberSelector(
                        selector.NumberSelectorConfig(min=0, max=10, mode=selector.NumberSelectorMode.BOX)
                    ),
                }
            ),
        )

    async def async_step_rate_limiting(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Request spacing and debouncing, which protect the Airduino board."""
        if user_input is not None:
            return self._save(user_input)

        schema: dict[Any, Any] = {}
        for key, maximum in (
            ("min_request_interval", 5.0),
            ("inter_sensor_delay", 5.0),
            ("write_cooldown", 10.0),
            ("request_debounce", 2.0),
        ):
            marker, number_selector = self._seconds(key, minimum=0.0, maximum=maximum, step=0.1)
            schema[marker] = number_selector

        return self.async_show_form(step_id="rate_limiting", data_schema=vol.Schema(schema))
