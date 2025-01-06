import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_UPDATE_INTERVAL, CONF_SOURCE

_LOGGER = logging.getLogger(__name__)

class PantryTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pantry Tracker."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step from the user."""
        if user_input is not None:
            return self.async_create_entry(
                title="Pantry Tracker",
                data=user_input
            )

        data_schema = vol.Schema({
            vol.Optional(CONF_UPDATE_INTERVAL, default=30): cv.positive_int,
            vol.Optional(CONF_SOURCE, default="http://homeassistant.local:8099"): cv.string,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the config flow to handle options."""
        return PantryTrackerOptionsFlowHandler(config_entry)


class PantryTrackerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Pantry Tracker."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for Pantry Tracker."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_data = dict(self.config_entry.data)
        options_schema = vol.Schema({
            vol.Optional(CONF_UPDATE_INTERVAL, default=current_data.get(CONF_UPDATE_INTERVAL, 30)): cv.positive_int,
            vol.Optional(CONF_SOURCE, default=current_data.get(CONF_SOURCE, "http://homeassistant.local:8099")): cv.string,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        )
