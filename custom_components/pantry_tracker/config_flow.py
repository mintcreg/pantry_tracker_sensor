import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_UPDATE_INTERVAL, CONF_SOURCE
from . import async_get_addon_port  # <-- Import the helper from __init__.py

_LOGGER = logging.getLogger(__name__)


class PantryTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pantry Tracker."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step from the user."""
        errors = {}

        if user_input is not None:
            # Extract the update interval from user input
            update_interval = user_input.get(CONF_UPDATE_INTERVAL, 30)

            # Fetch the port from the 'pantry_tracker' add-on
            discovered_port = await async_get_addon_port(self.hass, "pantry_tracker")
            if discovered_port is None:
                # If we fail to discover the port, show an error in the form
                errors["base"] = "cannot_connect"
            else:
                # Build the source URL automatically using the discovered port
                dynamic_source = f"http://homeassistant.local:{discovered_port}"

                # Create the entry with the discovered source + user’s interval
                return self.async_create_entry(
                    title="Pantry Tracker",
                    data={
                        CONF_UPDATE_INTERVAL: update_interval,
                        CONF_SOURCE: dynamic_source
                    }
                )

        # Show the form (with optional errors) if the user hasn't submitted or we had an error
        data_schema = vol.Schema({
            vol.Required(CONF_UPDATE_INTERVAL, default=30): cv.positive_int
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
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for Pantry Tracker."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_data = dict(self.config_entry.data)
        options_schema = vol.Schema({
            vol.Optional(CONF_UPDATE_INTERVAL, default=current_data.get(CONF_UPDATE_INTERVAL, 30)): cv.positive_int,
            # We keep the source field here so a user could view/change it if they wish
            vol.Optional(CONF_SOURCE, default=current_data.get(CONF_SOURCE, "http://homeassistant.local:8099")): cv.string,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema
        )
