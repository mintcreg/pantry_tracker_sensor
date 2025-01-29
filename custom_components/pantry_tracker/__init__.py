# custom_components/pantry_tracker/__init__.py

import logging
import os
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    CONF_SOURCE,          # Retained for migration
    CONF_HOST,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    CONF_API_KEY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """
    Set up Pantry Tracker integration (no YAML config).

    This method is called when Home Assistant starts and sets up any necessary data structures.
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Set up Pantry Tracker from a config entry.

    This method is called when a new configuration entry is created or an existing one is migrated.
    """
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    _LOGGER.info("Pantry Tracker integration set up successfully.")

    # Listen for option changes so we can reload the integration if options are updated
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Forward setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Unload a config entry.

    This method is called when a configuration entry is removed or when Home Assistant is shutting down.
    """
    _LOGGER.info("Unloading Pantry Tracker integration...")

    # Retrieve any stored data for this entry
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    unsub = entry_data.pop("update_interval_unsub", None)
    if unsub:
        _LOGGER.info("Cancelling the Pantry Tracker update interval before unloading.")
        unsub()

    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])

    # Remove all entities associated with this config entry
    registry = async_get(hass)  # Not an async call
    entities_to_remove = [
        entity.entity_id
        for entity in registry.entities.values()
        if entity.platform == DOMAIN and entity.config_entry_id == entry.entry_id
    ]
    for entity_id in entities_to_remove:
        registry.async_remove(entity_id)
        _LOGGER.info(f"Removed entity {entity_id} as part of cleanup.")

    # Optionally delete a data file associated with this integration
    data_file = hass.config.path("custom_components", DOMAIN, "pantry_data.json")
    if os.path.exists(data_file):
        try:
            os.remove(data_file)
            _LOGGER.info(f"Deleted data file {data_file} upon cleanup.")
        except Exception as e:
            _LOGGER.error(f"Error deleting data file {data_file}: {e}")
    else:
        _LOGGER.info(f"Data file {data_file} does not exist. No need to delete.")

    # Remove the entry from hass.data
    hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.info("Pantry Tracker integration unloaded successfully.")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Reload Pantry Tracker config entry when options change.

    This ensures the sensor code re-reads the updated port/URL or other options.
    """
    _LOGGER.info("Reloading Pantry Tracker config entry: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """
    Migrate a config entry from version 1 to version 2.

    This function transforms the configuration data from the old schema to the new one.
    """
    if config_entry.version != 1:
        _LOGGER.debug("No migration needed for version %s", config_entry.version)
        return True  # No migration needed

    _LOGGER.info("Migrating Pantry Tracker config from version 1 to 2")

    # Retrieve the old 'source' configuration
    source = config_entry.data.get(CONF_SOURCE)
    if not source:
        _LOGGER.error("CONF_SOURCE not found in config entry data. Cannot migrate.")
        return False  # Migration failed due to missing data

    parsed = urlparse(source)

    host = parsed.hostname
    port = parsed.port

    if not host or not port:
        _LOGGER.error("Invalid CONF_SOURCE format. Expected URL with host and port.")
        return False  # Migration failed due to invalid format

    # Prepare new data with the updated schema
    new_data = {
        CONF_UPDATE_INTERVAL: config_entry.data.get(CONF_UPDATE_INTERVAL, 30),
        CONF_HOST: host,
        CONF_PORT: port,
        CONF_API_KEY: "",  # Initialize API Key; user should update via options
    }

    # Update the configuration entry with the new data and version
    try:
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options={},  # Reset options or carry over existing ones as needed
            version=2,    # Update the version to reflect the new schema
        )
        _LOGGER.info("Migration to version 2 successful")
        return True  # Indicate successful migration
    except Exception as e:
        _LOGGER.error(f"Failed to migrate Pantry Tracker config entry: {e}")
        return False  # Migration failed due to an exception
