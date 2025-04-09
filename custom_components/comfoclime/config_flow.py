import voluptuous as vol

from homeassistant import config_entries

DOMAIN = "comfoclime"


class ComfoClimeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=f"ComfoClime @ {user_input['host']}",
                data={"host": user_input["host"]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("host", default="comfoclime.local"): str}
            ),
        )
