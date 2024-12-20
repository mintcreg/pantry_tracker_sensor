"""Pantry Tracker Integration."""

import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "pantry_tracker"

async def async_setup(hass, config):
    """Set up the Pantry Tracker integration."""
    _LOGGER.debug("Setting up Pantry Tracker integration.")
    # Initialize integration data storage
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    return True  # Indicate successful setup

async def async_setup_entry(hass, entry):
    """Set up Pantry Tracker from a config entry."""
    # No config entries are used in this integration
    return True

async def async_remove_entry(hass, entry):
    """Handle removal of a config entry."""
    # No config entries are used in this integration
    return True
