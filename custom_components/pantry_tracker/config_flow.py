# custom_components/pantry_tracker/config_flow.py

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_HOST,
    CONF_PORT,
    CONF_USE_SSL,
)

_LOGGER = logging.getLogger(__name__)


class PantryTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pantry Tracker."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step from the user."""
        errors = {}

        if user_input is not None:
            # Create the config entry with the 4 fields
            return self.async_create_entry(
                title="Pantry Tracker",
                data={
                    CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_USE_SSL: user_input[CONF_USE_SSL],
                }
            )

        # Build the schema for the user step
        data_schema = vol.Schema({
            vol.Required(CONF_UPDATE_INTERVAL, default=30): cv.positive_int,
            vol.Required(CONF_HOST, default="127.0.0.1"): cv.string,
            vol.Required(CONF_PORT, default=8099): cv.port,
            vol.Required(CONF_USE_SSL, default=False): cv.boolean,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Define the config flow to handle options."""
        return PantryTrackerOptionsFlowHandler(config_entry)


class PantryTrackerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Pantry Tracker."""

    def __init__(self, config_entry):
        self._entry_id = config_entry.entry_id

    async def async_step_init(self, user_input=None):
        """Manage the options for Pantry Tracker."""
        config_entry = self.hass.config_entries.async_get_entry(self._entry_id)

        if user_input is not None:
            # Save the new options
            return self.async_create_entry(title="", data=user_input)

        # Merge original data + existing options
        current_data = dict(config_entry.data)
        current_options = dict(config_entry.options)

        update_interval = current_options.get(
            CONF_UPDATE_INTERVAL,
            current_data.get(CONF_UPDATE_INTERVAL, 30)
        )
        host = current_options.get(
            CONF_HOST,
            current_data.get(CONF_HOST, "127.0.0.1")
        )
        port = current_options.get(
            CONF_PORT,
            current_data.get(CONF_PORT, 8099)
        )
        use_ssl = current_options.get(
            CONF_USE_SSL,
            current_data.get(CONF_USE_SSL, False)
        )

        data_schema = vol.Schema({
            vol.Optional(CONF_UPDATE_INTERVAL, default=update_interval): cv.positive_int,
            vol.Optional(CONF_HOST, default=host): cv.string,
            vol.Optional(CONF_PORT, default=port): cv.port,
            vol.Optional(CONF_USE_SSL, default=use_ssl): cv.boolean,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
