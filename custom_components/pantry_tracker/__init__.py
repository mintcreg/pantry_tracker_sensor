# custom_components/pantry_tracker/__init__.py

import logging
import os

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up Pantry Tracker integration (no YAML config)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Pantry Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    _LOGGER.info("Pantry Tracker integration set up successfully.")

    # Listen for option changes so we reload the integration
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Forward setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info("Unloading Pantry Tracker integration...")

    # Cancel the sensor update interval if stored in entry_data
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    unsub = entry_data.pop("update_interval_unsub", None)
    if unsub:
        _LOGGER.info("Cancelling the Pantry Tracker update interval before unloading.")
        unsub()

    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])

    # Remove all entities for this config entry
    registry = async_get(hass)  # Not an async call
    entities_to_remove = [
        entity.entity_id
        for entity in registry.entities.values()
        if entity.platform == DOMAIN and entity.config_entry_id == entry.entry_id
    ]
    for entity_id in entities_to_remove:
        registry.async_remove(entity_id)
        _LOGGER.info(f"Removed entity {entity_id} as part of cleanup.")

    # Optionally delete a data file
    data_file = hass.config.path("custom_components", DOMAIN, "pantry_data.json")
    if os.path.exists(data_file):
        try:
            os.remove(data_file)
            _LOGGER.info(f"Deleted data file {data_file} upon cleanup.")
        except Exception as e:
            _LOGGER.error(f"Error deleting data file {data_file}: {e}")
    else:
        _LOGGER.info(f"Data file {data_file} does not exist. No need to delete.")

    hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.info("Pantry Tracker integration unloaded successfully.")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Reload Pantry Tracker config entry when options change.
    This ensures the sensor code re-reads the updated port/URL.
    """
    _LOGGER.info("Reloading Pantry Tracker config entry: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
