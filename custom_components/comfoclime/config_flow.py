"""ComfoClime Configuration Flow.

Simple configuration flow for ComfoClime integration.
Handles initial setup: device discovery and connection validation.
"""

import logging

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow

from .infrastructure import validate_host

_LOGGER = logging.getLogger(__name__)

DOMAIN = "comfoclime"


class ComfoClimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ComfoClime integration.

    Validates device connection by attempting to fetch the UUID from
    the monitoring/ping endpoint. If successful, creates a config entry.
    """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where user provides device hostname.

        Validates that the device is reachable and responds with a valid UUID.
        If validation succeeds, creates the config entry.

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
                    async with aiohttp.ClientSession() as session, session.get(
                        url, timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
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
                except (TimeoutError, aiohttp.ClientError) as err:
                    errors["host"] = "cannot_connect"
                    _LOGGER.error("Connection error to %s: %s", host, err)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("host", default="comfoclime.local"): str}),
            errors=errors,
        )
