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

    # Instead of hass.async_create_task(...), we now await the forward setup
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info("Unloading Pantry Tracker integration.")

    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])

    # Remove all entities for this config entry
    registry = await async_get(hass)
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
