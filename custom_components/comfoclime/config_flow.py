import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers import selector

from .entity_helper import get_default_enabled_entities, get_entity_selection_options

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
            menu_options=["general", "entities"],
        )

    async def async_step_general(self, user_input=None):
        """Handle general configuration options."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "enable_diagnostics",
                        default=self.entry.options.get("enable_diagnostics", False),
                    ): bool,
                    vol.Optional(
                        "read_timeout",
                        default=self.entry.options.get("read_timeout", DEFAULT_READ_TIMEOUT),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=120, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(
                        "write_timeout",
                        default=self.entry.options.get("write_timeout", DEFAULT_WRITE_TIMEOUT),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=120, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(
                        "polling_interval",
                        default=self.entry.options.get("polling_interval", DEFAULT_POLLING_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=600, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(
                        "cache_ttl",
                        default=self.entry.options.get("cache_ttl", DEFAULT_CACHE_TTL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=300, mode=selector.NumberSelectorMode.BOX
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
                    vol.Optional(
                        "min_request_interval",
                        default=self.entry.options.get("min_request_interval", DEFAULT_MIN_REQUEST_INTERVAL),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0, max=5.0, step=0.1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(
                        "write_cooldown",
                        default=self.entry.options.get("write_cooldown", DEFAULT_WRITE_COOLDOWN),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                    vol.Optional(
                        "request_debounce",
                        default=self.entry.options.get("request_debounce", DEFAULT_REQUEST_DEBOUNCE),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0.0, max=2.0, step=0.1, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
        )

    async def async_step_entities(self, user_input=None):
        """Handle entity selection configuration."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data={**self.entry.options, **self._data})

        # Get current enabled entities or use defaults
        current_enabled = self.entry.options.get(
            "enabled_entities", list(get_default_enabled_entities())
        )

        # Get all available entity selection options
        selection_options = get_entity_selection_options()

        return self.async_show_form(
            step_id="entities",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "enabled_entities",
                        default=current_enabled,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=opt["value"], label=opt["label"])
                                for opt in selection_options
                            ],
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )
