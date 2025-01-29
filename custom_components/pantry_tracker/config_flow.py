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
    CONF_API_KEY,  # Import the new constant
)

_LOGGER = logging.getLogger(__name__)


class PantryTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pantry Tracker."""

    VERSION = 2  # Increment the version since we're making changes

    async def async_step_user(self, user_input=None):
        """Handle the initial step from the user."""
        errors = {}

        if user_input is not None:
            # Validate the host does not contain 'http://' or 'https://'
            host = user_input[CONF_HOST]
            if "://" in host:
                errors["base"] = "invalid_host"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_schema(),
                    errors=errors
                )

            # Create the config entry with the fields
            return self.async_create_entry(
                title="Pantry Tracker",
                data={
                    CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                    CONF_HOST: host,
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_API_KEY: user_input[CONF_API_KEY],  # Save the API key
                }
            )

        # Build the schema for the user step
        data_schema = self._get_schema()

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    def _get_schema(self):
        """Return the schema for the user step."""
        return vol.Schema({
            vol.Required(CONF_UPDATE_INTERVAL, default=30): cv.positive_int,
            vol.Required(CONF_HOST, default="homeassistant.local"): cv.string,
            vol.Required(CONF_PORT, default=8099): cv.port,
            vol.Required(CONF_API_KEY): cv.string,  # New API key field
        })

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
        api_key = current_options.get(
            CONF_API_KEY,
            current_data.get(CONF_API_KEY, "")
        )

        data_schema = vol.Schema({
            vol.Optional(CONF_UPDATE_INTERVAL, default=update_interval): cv.positive_int,
            vol.Optional(CONF_HOST, default=host): cv.string,
            vol.Optional(CONF_PORT, default=port): cv.port,
            vol.Optional(CONF_API_KEY, default=api_key): cv.string,  # API key in options
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
