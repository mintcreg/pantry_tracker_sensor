# custom_components/pantry_tracker/__init__.py

import logging
import os

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # NEW IMPORT

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_addon_port(hass: HomeAssistant, addon_slug: str) -> int | None:
    """
    Query the Supervisor API for the add-on and extract the mapped host port
    for 8099/tcp if it exists. Return None if not found or on error.
    """
    _LOGGER.debug("Attempting to fetch port for add-on slug '%s'", addon_slug)

    session = async_get_clientsession(hass)
    supervisor_token = os.getenv("SUPERVISOR_TOKEN")

    if not supervisor_token:
        _LOGGER.error("No SUPERVISOR_TOKEN found. Are we running under Home Assistant OS or Supervised?")
        return None

    url = f"http://supervisor/addons/{addon_slug}/info"
    headers = {"Authorization": f"Bearer {supervisor_token}"}

    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                _LOGGER.error("Error calling Supervisor API (%s): %s", resp.status, await resp.text())
                return None

            data = await resp.json()
            addon_data = data.get("data", {})
            network_info = addon_data.get("network", {})

            # Example: network_info might be {"8099/tcp": 8123}
            for container_port, host_port in network_info.items():
                if container_port.startswith("8099"):
                    _LOGGER.info("Found mapped port for %s: %s", container_port, host_port)
                    return host_port

            _LOGGER.warning("Port 8099/tcp not found in add-on 'network' info: %s", network_info)
            return None

    except Exception as err:
        _LOGGER.error("Failed to fetch add-on info from Supervisor: %s", err)
        return None


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
