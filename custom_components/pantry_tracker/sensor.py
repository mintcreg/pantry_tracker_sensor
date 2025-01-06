# custom_components/pantry_tracker/sensor.py

import logging
from datetime import timedelta

import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import DOMAIN, CONF_UPDATE_INTERVAL, CONF_SOURCE

_LOGGER = logging.getLogger(__name__)

INCREASE_COUNT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("amount", default=1): vol.Coerce(int)
})

DECREASE_COUNT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("amount", default=1): vol.Coerce(int)
})

BARCODE_OPERATION_SCHEMA = vol.Schema({
    vol.Required("barcode"): cv.string,
    vol.Optional("amount", default=1): vol.Coerce(int)
})


def sanitize_entity_id(name: str) -> str:
    """Sanitize product name to create a unique entity ID."""
    return f"sensor.product_{name.lower().replace(' ', '_').replace('-', '_')}"


async def remove_entity_async(hass: HomeAssistant, entity_id: str):
    """Remove an entity from Home Assistant's Registry."""
    entity_registry = async_get_entity_registry(hass)
    entry = entity_registry.async_get(entity_id)
    if entry:
        entity_registry.async_remove(entity_id)
        _LOGGER.info(f"Removed entity from registry: {entity_id}")
    else:
        _LOGGER.warning(f"Entity not found in registry: {entity_id}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Pantry Tracker sensors from a config entry."""
    _LOGGER.debug("Starting setup of pantry_tracker sensors from config entry.")

    update_interval_seconds = entry.data.get(CONF_UPDATE_INTERVAL, 30)
    source = entry.data.get(CONF_SOURCE, "http://homeassistant.local:8099")

    SCAN_INTERVAL = timedelta(seconds=update_interval_seconds)
    _LOGGER.debug(f"Using update_interval: {SCAN_INTERVAL}, source: {source}")

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        session = aiohttp.ClientSession(connector=connector)
        _LOGGER.debug("Created aiohttp session with SSL verification disabled.")
    except Exception as e:
        _LOGGER.error(f"Failed to create aiohttp session: {e}")
        return

    # Stash data for further usage
    hass.data.setdefault(DOMAIN, {})
    entry_data = hass.data[DOMAIN].setdefault(entry.entry_id, {})
    entry_data["session"] = session
    entry_data["categories"] = []
    entry_data["products"] = []
    entry_data["product_counts"] = {}
    entry_data["entities"] = {}

    async def async_shutdown(event):
        if session:
            await session.close()
            _LOGGER.debug("Closed aiohttp session")

    hass.bus.async_listen_once("homeassistant_stop", async_shutdown)

    # Fetch initial data
    await fetch_pantry_data(session, source, entry_data)

    # Create the CategoriesSensor
    cat_sensor = CategoriesSensor(entry, entry_data["categories"])
    entry_data["entities"]["pantry_categories"] = cat_sensor

    # Create product sensors
    product_sensors = []
    for p in entry_data["products"]:
        try:
            product_attributes = p.copy()
            name = product_attributes.pop("name")
            unique_id = sanitize_entity_id(name)
            url = product_attributes.pop("url", "")
            category = product_attributes.pop("category", "")
        except KeyError as e:
            _LOGGER.error(f"Product missing key {e}: {p}")
            continue

        entity_id = sanitize_entity_id(name)
        current_count = entry_data["product_counts"].get(entity_id, 0)
        sensor = ProductSensor(
            config_entry=entry,
            name=name,
            url=url,
            category=category,
            unique_id=unique_id,
            initial_count=current_count,
            additional_attributes=product_attributes
        )
        product_sensors.append(sensor)
        entry_data["entities"][entity_id] = sensor

    # Add sensors
    sensors_to_add = [cat_sensor] + product_sensors
    if sensors_to_add:
        _LOGGER.info("Adding %d sensors (including categories).", len(sensors_to_add))
        async_add_entities(sensors_to_add, True)

    # -------------------------------------------------------------
    # IMPORTANT: define an async callback that we directly await
    # -------------------------------------------------------------
    async def async_update_interval(now):
        """Async callback that fetches updates and syncs sensors."""
        await async_update_sensors(hass, entry, entry_data, source, async_add_entities)

    # Schedule periodic updates
    async_track_time_interval(hass, async_update_interval, SCAN_INTERVAL)

    # Register services
    hass.services.async_register(
        DOMAIN, "increase_count",
        lambda call: handle_increase_count_service(hass, call, session, source, entry_data),
        schema=INCREASE_COUNT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "decrease_count",
        lambda call: handle_decrease_count_service(hass, call, session, source, entry_data),
        schema=DECREASE_COUNT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "barcode_increase",
        lambda call: handle_barcode_increase_service(hass, call, entry_data),
        schema=BARCODE_OPERATION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "barcode_decrease",
        lambda call: handle_barcode_decrease_service(hass, call, entry_data),
        schema=BARCODE_OPERATION_SCHEMA
    )


async def fetch_pantry_data(session, source, entry_data):
    """Fetch categories, products, and counts from your external API."""
    # Fetch categories
    try:
        async with session.get(f"{source}/categories") as resp:
            if resp.status == 200:
                categories = await resp.json()
                if isinstance(categories, list):
                    entry_data["categories"] = categories
                else:
                    _LOGGER.warning(f"Fetched categories is not a list: {categories}")
                    entry_data["categories"] = []
            else:
                _LOGGER.error(f"Failed to fetch categories. Status Code: {resp.status}")
                entry_data["categories"] = []
    except Exception as e:
        _LOGGER.error(f"Error while fetching categories: {e}")
        entry_data["categories"] = []

    # Fetch products
    try:
        async with session.get(f"{source}/products") as resp:
            if resp.status == 200:
                products = await resp.json()
                if isinstance(products, list):
                    entry_data["products"] = products
                else:
                    _LOGGER.warning(f"Fetched products is not a list: {products}")
                    entry_data["products"] = []
            else:
                _LOGGER.error(f"Failed to fetch products. Status Code: {resp.status}")
                entry_data["products"] = []
    except Exception as e:
        _LOGGER.error(f"Error while fetching products: {e}")
        entry_data["products"] = []

    # Fetch counts
    try:
        async with session.get(f"{source}/counts") as resp:
            if resp.status == 200:
                counts = await resp.json()
                if isinstance(counts, dict):
                    entry_data["product_counts"] = counts
                else:
                    _LOGGER.warning(f"Fetched counts is not a dict: {counts}")
                    entry_data["product_counts"] = {}
            else:
                _LOGGER.error(f"Failed to fetch counts. Status Code: {resp.status}")
                entry_data["product_counts"] = {}
    except Exception as e:
        _LOGGER.error(f"Error while fetching counts: {e}")
        entry_data["product_counts"] = {}


async def async_update_sensors(hass: HomeAssistant, entry: ConfigEntry, entry_data, source, async_add_entities):
    """Async method to update categories/products and sync sensors."""
    session = entry_data["session"]

    await fetch_pantry_data(session, source, entry_data)

    # Update categories sensor
    cat_sensor = entry_data["entities"].get("pantry_categories")
    if cat_sensor and isinstance(cat_sensor, CategoriesSensor):
        cat_sensor.update_categories(entry_data["categories"])

    fetched_entity_ids = set()
    new_sensors = []

    for p in entry_data["products"]:
        try:
            product_attributes = p.copy()
            name = product_attributes.pop("name")
            unique_id = sanitize_entity_id(name)
            url = product_attributes.pop("url", "")
            category = product_attributes.pop("category", "")
        except KeyError as e:
            _LOGGER.error(f"Product missing key {e}: {p}")
            continue

        entity_id = sanitize_entity_id(name)
        fetched_entity_ids.add(entity_id)

        existing = entry_data["entities"].get(entity_id)
        if isinstance(existing, ProductSensor):
            # Update existing sensor
            existing.update_attributes(url, category, product_attributes)
        else:
            # New product
            current_count = entry_data["product_counts"].get(entity_id, 0)
            sensor = ProductSensor(
                config_entry=entry,
                name=name,
                url=url,
                category=category,
                unique_id=unique_id,
                initial_count=current_count,
                additional_attributes=product_attributes
            )
            entry_data["entities"][entity_id] = sensor
            new_sensors.append(sensor)
            _LOGGER.info(f"Detected new product '{name}'. Adding sensor.")

    # Remove disappeared products
    existing_ids = set(entry_data["entities"].keys())
    removed_ids = existing_ids - fetched_entity_ids - {"pantry_categories"}
    for rid in removed_ids:
        sensor = entry_data["entities"].pop(rid, None)
        if sensor:
            _LOGGER.info(f"Removed sensor for entity_id {rid} as it's no longer present.")
            await remove_entity_async(hass, rid)

    # Add new sensors
    if new_sensors:
        _LOGGER.info(f"Adding {len(new_sensors)} new product sensors.")
        async_add_entities(new_sensors, True)

    # Update counts on all product sensors
    for entity_id, count in entry_data["product_counts"].items():
        sensor = entry_data["entities"].get(entity_id)
        if isinstance(sensor, ProductSensor):
            sensor.update_count(count)


# --------------------------- Service Handlers ---------------------------
async def handle_increase_count_service(hass: HomeAssistant, call: ServiceCall, session, source, entry_data):
    entity_id = call.data["entity_id"]
    amount = call.data["amount"]

    sensor = entry_data["entities"].get(entity_id)
    if not sensor or not isinstance(sensor, ProductSensor):
        _LOGGER.error(f"Entity {entity_id} not found for increase_count")
        return

    try:
        async with session.post(
            f"{source}/update_count",
            json={
                "product_name": sensor._product_name,
                "action": "increase",
                "amount": amount
            }
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "ok":
                    new_count = data.get("count")
                    sensor.update_count(new_count)
                    _LOGGER.debug("Successfully increased count via API.")
                else:
                    _LOGGER.error(f"Failed to increase count via API: {data.get('message')}")
            else:
                _LOGGER.error(f"Failed to increase count. Status={response.status}")
    except Exception as e:
        _LOGGER.error(f"Unexpected error while increasing count via API: {e}")


async def handle_decrease_count_service(hass: HomeAssistant, call: ServiceCall, session, source, entry_data):
    entity_id = call.data["entity_id"]
    amount = call.data["amount"]

    sensor = entry_data["entities"].get(entity_id)
    if not sensor or not isinstance(sensor, ProductSensor):
        _LOGGER.error(f"Entity {entity_id} not found for decrease_count")
        return

    try:
        async with session.post(
            f"{source}/update_count",
            json={
                "product_name": sensor._product_name,
                "action": "decrease",
                "amount": amount
            }
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "ok":
                    new_count = data.get("count")
                    sensor.update_count(new_count)
                    _LOGGER.debug("Successfully decreased count via API.")
                else:
                    _LOGGER.error(f"Failed to decrease count via API: {data.get('message')}")
            else:
                _LOGGER.error(f"Failed to decrease count. Status={response.status}")
    except Exception as e:
        _LOGGER.error(f"Unexpected error while decreasing count via API: {e}")


async def handle_barcode_increase_service(hass: HomeAssistant, call: ServiceCall, entry_data):
    barcode = call.data["barcode"]
    amount = call.data["amount"]

    matching_sensors = [
        s for s in entry_data["entities"].values()
        if isinstance(s, ProductSensor) and s.extra_state_attributes.get("barcode") == barcode
    ]
    if not matching_sensors:
        _LOGGER.error(f"No sensor found with barcode {barcode}")
        return

    for sensor in matching_sensors:
        new_count = sensor.native_value + amount
        sensor.update_count(new_count)
        _LOGGER.info(f"Increased count for sensor {sensor.entity_id} by {amount}. New count: {new_count}")


async def handle_barcode_decrease_service(hass: HomeAssistant, call: ServiceCall, entry_data):
    barcode = call.data["barcode"]
    amount = call.data["amount"]

    matching_sensors = [
        s for s in entry_data["entities"].values()
        if isinstance(s, ProductSensor) and s.extra_state_attributes.get("barcode") == barcode
    ]
    if not matching_sensors:
        _LOGGER.error(f"No sensor found with barcode {barcode}")
        return

    for sensor in matching_sensors:
        new_count = max(sensor.native_value - amount, 0)
        sensor.update_count(new_count)
        _LOGGER.info(f"Decreased count for sensor {sensor.entity_id} by {amount}. New count: {new_count}")


# --------------------------- Entities ---------------------------
class CategoriesSensor(SensorEntity):
    """Sensor to track the number of pantry categories."""

    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, entry: ConfigEntry, categories: list):
        self._entry = entry
        self._categories = categories
        self._attr_unique_id = f"{DOMAIN}_categories"
        self._attr_name = "Pantry Categories"

    @property
    def native_value(self):
        return len(self._categories)

    @property
    def extra_state_attributes(self):
        return {"categories": self._categories}

    @property
    def device_info(self):
        """Attach under a single device in the UI."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Pantry Tracker",
            "manufacturer": "Pantry Tracker"
        }

    def update_categories(self, categories: list):
        self._categories = categories
        self.async_write_ha_state()


class ProductSensor(SensorEntity):
    """Sensor to track individual product counts and attributes."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        name: str,
        url: str,
        category: str,
        unique_id: str,
        initial_count: int = 0,
        additional_attributes: dict = None
    ):
        self._entry = config_entry
        self._product_name = name
        self._url = url
        self._category = category
        self._attr_unique_id = unique_id
        self._attr_name = f"Product: {name}"
        self._attr_icon = "mdi:barcode-scan"
        self._count = initial_count
        self._additional_attributes = additional_attributes or {}

    @property
    def native_value(self):
        return self._count

    @property
    def extra_state_attributes(self):
        attrs = {
            "product_name": self._product_name,
            "url": self._url,
            "category": self._category,
            "count": self._count
        }
        attrs.update(self._additional_attributes)
        return attrs

    @property
    def device_info(self):
        """Attach under the same device as CategoriesSensor."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Pantry Tracker",
            "manufacturer": "PantryTracker"
        }

    def update_attributes(self, url: str, category: str, additional_attributes: dict):
        self._url = url
        self._category = category
        if additional_attributes:
            self._additional_attributes = additional_attributes
        self.async_write_ha_state()

    def update_count(self, new_count: int):
        self._count = new_count
        self.async_write_ha_state()