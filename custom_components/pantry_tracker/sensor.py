import logging
from datetime import timedelta

import aiohttp
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

_LOGGER = logging.getLogger(__name__)

DOMAIN = "pantry_tracker"

# Define configuration keys
CONF_UPDATE_INTERVAL = "update_interval"
CONF_SOURCE = "source"

# Extend the PLATFORM_SCHEMA to include update_interval and source
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_UPDATE_INTERVAL, default=30): cv.positive_int,
        vol.Optional(CONF_SOURCE, default="http://homeassistant.local:8099"): cv.string,
        # Removed CONF_SSL_CERT as per request
        # Add other configuration options here if needed
    }
)

INCREASE_COUNT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("amount", default=1): vol.Coerce(int)
})

DECREASE_COUNT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Optional("amount", default=1): vol.Coerce(int)
})

# Define service schemas for barcode-based operations
BARCODE_OPERATION_SCHEMA = vol.Schema({
    vol.Required("barcode"): cv.string,
    vol.Optional("amount", default=1): vol.Coerce(int)
})

def sanitize_entity_id(name: str) -> str:
    """Sanitize the product name to create a unique entity ID without category."""
    return f"sensor.product_{name.lower().replace(' ', '_').replace('-', '_')}"


async def remove_entity_async(hass: HomeAssistant, entity_id: str):
    """Remove an entity from Home Assistant's Entity Registry asynchronously."""
    entity_registry = async_get_entity_registry(hass)
    entry = entity_registry.async_get(entity_id)
    if entry:
        entity_registry.async_remove(entry.entity_id)
        _LOGGER.info(f"Removed entity from registry: {entity_id}")
    else:
        _LOGGER.warning(f"Entity not found in registry: {entity_id}")


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None
):
    """Set up the Pantry Tracker sensors with persistent counts asynchronously."""
    _LOGGER.debug("Starting setup of pantry_tracker platform.")

    # Extract update_interval and source from config and convert to timedelta
    update_interval_seconds = config.get(CONF_UPDATE_INTERVAL, 30)
    SCAN_INTERVAL = timedelta(seconds=update_interval_seconds)
    _LOGGER.debug(f"Using update_interval: {SCAN_INTERVAL}")

    source = config.get(CONF_SOURCE, "https://127.0.0.1:5000")
    _LOGGER.debug(f"Using source: {source}")

    # Since SSL_CERT is removed, disable SSL verification by setting ssl=False
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        session = aiohttp.ClientSession(connector=connector)
        _LOGGER.debug("Created aiohttp session with SSL verification disabled.")
    except Exception as e:
        _LOGGER.error(f"Failed to create aiohttp session: {e}")
        return

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        _LOGGER.debug("Initialized hass.data for pantry_tracker.")

    # Initialize data structures
    hass.data[DOMAIN].setdefault("entities", {})
    hass.data[DOMAIN].setdefault("product_counts", {})
    hass.data[DOMAIN].setdefault("categories", [])
    hass.data[DOMAIN].setdefault("products", [])

    # Store session for cleanup
    hass.data[DOMAIN]["session"] = session

    # Register shutdown event to close the session
    async def async_shutdown(event):
        """Handle shutdown of the integration."""
        session = hass.data[DOMAIN].get("session")
        if session:
            await session.close()
            _LOGGER.debug("Closed aiohttp session")

    hass.bus.async_listen_once("homeassistant_stop", async_shutdown)

    # Fetch existing data from API
    try:
        # Fetch categories
        async with session.get(f"{source}/categories") as response:
            if response.status == 200:
                categories = await response.json()
                if isinstance(categories, list):
                    hass.data[DOMAIN]["categories"] = categories
                    _LOGGER.debug("Fetched categories: %s", categories)
                else:
                    _LOGGER.warning("Fetched categories is not a list: %s", categories)
                    hass.data[DOMAIN]["categories"] = []
            else:
                _LOGGER.error(f"Failed to fetch categories. Status Code: {response.status}")
                hass.data[DOMAIN]["categories"] = []

        # Fetch products
        async with session.get(f"{source}/products") as response:
            if response.status == 200:
                products = await response.json()
                if isinstance(products, list):
                    hass.data[DOMAIN]["products"] = products
                    _LOGGER.debug("Fetched products: %s", products)
                else:
                    _LOGGER.warning("Fetched products is not a list: %s", products)
                    hass.data[DOMAIN]["products"] = []
            else:
                _LOGGER.error(f"Failed to fetch products. Status Code: {response.status}")
                hass.data[DOMAIN]["products"] = []

        # Fetch current counts
        async with session.get(f"{source}/counts") as response:
            if response.status == 200:
                counts = await response.json()
                if isinstance(counts, dict):
                    hass.data[DOMAIN]["product_counts"] = counts
                    _LOGGER.debug("Fetched counts: %s", counts)
                else:
                    _LOGGER.warning("Fetched counts is not a dict: %s", counts)
                    hass.data[DOMAIN]["product_counts"] = {}
            else:
                _LOGGER.error(f"Failed to fetch counts. Status Code: {response.status}")
                hass.data[DOMAIN]["product_counts"] = {}
    except aiohttp.ClientError as e:
        _LOGGER.error(f"HTTP error while fetching initial data: {e}")
        await session.close()
        return
    except Exception as e:
        _LOGGER.error(f"Unexpected error while fetching initial data: {e}")
        await session.close()
        return

    # Initialize the CategoriesSensor
    cat_sensor = CategoriesSensor(hass.data[DOMAIN]["categories"])
    hass.data[DOMAIN]["entities"]["pantry_categories"] = cat_sensor

    # Initialize ProductSensors
    prod_sensors = []
    for p in hass.data[DOMAIN]["products"]:
        try:
            # Store all attributes from the product
            product_attributes = p.copy()
            name = product_attributes.pop("name")
            unique_id = sanitize_entity_id(name)
            url = product_attributes.pop("url", "")
            category = product_attributes.pop("category", "")
        except KeyError as e:
            _LOGGER.error("Product missing key %s: %s", e, p)
            continue

        entity_id = sanitize_entity_id(name)
        existing_entity = hass.data[DOMAIN]["entities"].get(entity_id)

        if existing_entity:
            _LOGGER.info("Entity %s already exists. Skipping creation.", existing_entity.entity_id)
            continue
        else:
            current_count = hass.data[DOMAIN]["product_counts"].get(entity_id, 0)
            product_sensor = ProductSensor(
                name=name,
                url=url,
                category=category,
                unique_id=unique_id,
                initial_count=current_count,
                additional_attributes=product_attributes
            )
            prod_sensors.append(product_sensor)
            hass.data[DOMAIN]["entities"][entity_id] = product_sensor

    # Add the CategoriesSensor and ProductSensors to Home Assistant
    entities_to_add = [cat_sensor] + prod_sensors
    if entities_to_add:
        _LOGGER.info("Adding %d sensors (including categories).", len(entities_to_add))
        async_add_entities(entities_to_add, True)

    # Define the async_update_sensors function for periodic updates
    async def async_update_sensors(now):
        """Periodically update sensors by fetching latest data asynchronously."""
        _LOGGER.debug("Periodic update: Fetching latest data.")
        try:
            # Fetch categories
            async with session.get(f"{source}/categories") as response:
                if response.status == 200:
                    categories = await response.json()
                    if isinstance(categories, list):
                        hass.data[DOMAIN]["categories"] = categories
                        _LOGGER.debug("Fetched categories: %s", categories)
                    else:
                        _LOGGER.warning("Fetched categories is not a list: %s", categories)
                        hass.data[DOMAIN]["categories"] = []
                else:
                    _LOGGER.error(f"Failed to fetch categories. Status Code: {response.status}")
                    hass.data[DOMAIN]["categories"] = []

            # Fetch products
            async with session.get(f"{source}/products") as response:
                if response.status == 200:
                    products = await response.json()
                    if isinstance(products, list):
                        hass.data[DOMAIN]["products"] = products
                        _LOGGER.debug("Fetched products: %s", products)
                    else:
                        _LOGGER.warning("Fetched products is not a list: %s", products)
                        hass.data[DOMAIN]["products"] = []
                else:
                    _LOGGER.error(f"Failed to fetch products. Status Code: {response.status}")
                    hass.data[DOMAIN]["products"] = []

            # Fetch current counts
            async with session.get(f"{source}/counts") as response:
                if response.status == 200:
                    counts = await response.json()
                    if isinstance(counts, dict):
                        hass.data[DOMAIN]["product_counts"] = counts
                        _LOGGER.debug("Fetched counts: %s", counts)
                    else:
                        _LOGGER.warning("Fetched counts is not a dict: %s", counts)
                        hass.data[DOMAIN]["product_counts"] = {}
                else:
                    _LOGGER.error(f"Failed to fetch counts. Status Code: {response.status}")
                    hass.data[DOMAIN]["product_counts"] = {}

            # Update CategoriesSensor
            cat_sensor.update_categories(hass.data[DOMAIN]["categories"])

            # Update or add ProductSensors
            existing_entity_ids = set(hass.data[DOMAIN]["entities"].keys())
            fetched_entity_ids = set()
            new_prod_sensors = []  # Initialize a new list for new sensors

            for p in hass.data[DOMAIN]["products"]:
                try:
                    # Store all attributes from the product
                    product_attributes = p.copy()
                    name = product_attributes.pop("name")
                    unique_id = sanitize_entity_id(name)
                    url = product_attributes.pop("url", "")
                    category = product_attributes.pop("category", "")
                except KeyError as e:
                    _LOGGER.error("Product missing key %s: %s", e, p)
                    continue

                entity_id = sanitize_entity_id(name)
                fetched_entity_ids.add(entity_id)

                if entity_id in hass.data[DOMAIN]["entities"]:
                    # Update existing sensor's attributes
                    sensor = hass.data[DOMAIN]["entities"][entity_id]
                    sensor.update_attributes(url, category, product_attributes)
                else:
                    # New product detected, create and add sensor
                    current_count = hass.data[DOMAIN]["product_counts"].get(entity_id, 0)
                    product_sensor = ProductSensor(
                        name=name,
                        url=url,
                        category=category,
                        unique_id=unique_id,
                        initial_count=current_count,
                        additional_attributes=product_attributes
                    )
                    new_prod_sensors.append(product_sensor)
                    hass.data[DOMAIN]["entities"][entity_id] = product_sensor
                    _LOGGER.info("Detected new product '%s'. Adding sensor.", name)

            # Detect and remove deleted entities
            removed_entity_ids = existing_entity_ids - fetched_entity_ids - {"pantry_categories"}
            for entity_id in removed_entity_ids:
                hass.data[DOMAIN]["entities"].pop(entity_id, None)
                _LOGGER.info(f"Removed sensor for entity_id {entity_id} as it's no longer present.")

                # Remove the entity from HA Registry
                await remove_entity_async(hass, entity_id)

            # Add any new sensors
            if new_prod_sensors:
                _LOGGER.info("Adding %d new product sensors.", len(new_prod_sensors))
                async_add_entities(new_prod_sensors, True)

            # Update Counts for Existing Sensors
            for entity_id, count in hass.data[DOMAIN]["product_counts"].items():
                if entity_id in hass.data[DOMAIN]["entities"]:
                    sensor = hass.data[DOMAIN]["entities"][entity_id]
                    sensor.update_count(count)
                    _LOGGER.debug(f"Updated count for {entity_id} to {count}")

        except aiohttp.ClientError as e:
            _LOGGER.error(f"HTTP error during periodic update: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error during periodic update: {e}")

    # Schedule periodic updates
    async_track_time_interval(hass, async_update_sensors, SCAN_INTERVAL)

    # Service to increase product count
    async def handle_increase_count_service(call: ServiceCall):
        """Handle the increase_count service call."""
        entity_id = call.data["entity_id"]
        amount = call.data["amount"]
        _LOGGER.debug(f"Service call to increase count: entity_id={entity_id}, amount={amount}")

        # Log available entity_ids for debugging
        available_entities = list(hass.data[DOMAIN]["entities"].keys())
        _LOGGER.debug(f"Available entities: {available_entities}")

        if entity_id not in hass.data[DOMAIN]["entities"]:
            _LOGGER.error(f"Entity {entity_id} not found for increase_count")
            return

        sensor = hass.data[DOMAIN]["entities"][entity_id]

        # Update counts via API
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
                    _LOGGER.error(f"Failed to increase count via API. Status Code: {response.status}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"HTTP error while increasing count via API: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error while increasing count via API: {e}")

    # Service to decrease product count
    async def handle_decrease_count_service(call: ServiceCall):
        """Handle the decrease_count service call."""
        entity_id = call.data["entity_id"]
        amount = call.data["amount"]
        _LOGGER.debug(f"Service call to decrease count: entity_id={entity_id}, amount={amount}")

        # Log available entity_ids for debugging
        available_entities = list(hass.data[DOMAIN]["entities"].keys())
        _LOGGER.debug(f"Available entities: {available_entities}")

        if entity_id not in hass.data[DOMAIN]["entities"]:
            _LOGGER.error(f"Entity {entity_id} not found for decrease_count")
            return

        sensor = hass.data[DOMAIN]["entities"][entity_id]

        # Update counts via API
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
                    _LOGGER.error(f"Failed to decrease count via API. Status Code: {response.status}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"HTTP error while decreasing count via API: {e}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error while decreasing count via API: {e}")

    # Service to increase product count by barcode
    async def handle_barcode_increase_service(call: ServiceCall):
        """Handle the barcode_increase service call."""
        barcode = call.data["barcode"]
        amount = call.data["amount"]
        _LOGGER.debug(f"Service call to increase count by barcode: barcode={barcode}, amount={amount}")

        # Find the sensor with the matching barcode
        matching_sensors = [
            sensor for sensor in hass.data[DOMAIN]["entities"].values()
            if isinstance(sensor, ProductSensor) and sensor.extra_state_attributes.get("barcode") == barcode
        ]

        if not matching_sensors:
            _LOGGER.error(f"No sensor found with barcode {barcode}")
            return

        for sensor in matching_sensors:
            try:
                new_count = sensor.native_value + amount
                sensor.update_count(new_count)
                _LOGGER.info(f"Increased count for sensor {sensor.entity_id} by {amount}. New count: {new_count}")
            except Exception as e:
                _LOGGER.error(f"Failed to increase count for {sensor.entity_id}: {e}")

    # Service to decrease product count by barcode
    async def handle_barcode_decrease_service(call: ServiceCall):
        """Handle the barcode_decrease service call."""
        barcode = call.data["barcode"]
        amount = call.data["amount"]
        _LOGGER.debug(f"Service call to decrease count by barcode: barcode={barcode}, amount={amount}")

        # Find the sensor with the matching barcode
        matching_sensors = [
            sensor for sensor in hass.data[DOMAIN]["entities"].values()
            if isinstance(sensor, ProductSensor) and sensor.extra_state_attributes.get("barcode") == barcode
        ]

        if not matching_sensors:
            _LOGGER.error(f"No sensor found with barcode {barcode}")
            return

        for sensor in matching_sensors:
            try:
                new_count = max(sensor.native_value - amount, 0)  # Ensure count doesn't go negative
                sensor.update_count(new_count)
                _LOGGER.info(f"Decreased count for sensor {sensor.entity_id} by {amount}. New count: {new_count}")
            except Exception as e:
                _LOGGER.error(f"Failed to decrease count for {sensor.entity_id}: {e}")

    # Register the services
    hass.services.async_register(
        DOMAIN, "barcode_increase", handle_barcode_increase_service, schema=BARCODE_OPERATION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "barcode_decrease", handle_barcode_decrease_service, schema=BARCODE_OPERATION_SCHEMA
    )
    
	
	
	# Register the services
    hass.services.async_register(
        DOMAIN, "increase_count", handle_increase_count_service, schema=INCREASE_COUNT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "decrease_count", handle_decrease_count_service, schema=DECREASE_COUNT_SCHEMA
    )


class CategoriesSensor(SensorEntity):
    """Sensor to track the number of pantry categories."""

    _attr_name = "Pantry Categories"
    _attr_icon = "mdi:format-list-bulleted"
    _attr_unique_id = f"{DOMAIN}_categories"

    def __init__(self, categories: list):
        """Initialize the CategoriesSensor."""
        self._categories = categories

    @property
    def native_value(self):
        """Return the number of categories."""
        return len(self._categories)

    @property
    def extra_state_attributes(self):
        """Return the list of categories as an attribute."""
        return {"categories": self._categories}

    def update_categories(self, categories: list):
        """Update the categories list."""
        self._categories = categories
        self.async_schedule_update_ha_state()
        _LOGGER.debug(f"Updated categories: {self._categories}")


class ProductSensor(SensorEntity):
    """Sensor to track individual product counts and all associated attributes."""

    def __init__(
        self,
        name: str,
        url: str,
        category: str,
        unique_id: str,
        initial_count: int = 0,
        additional_attributes: dict = None
    ):
        """Initialize the ProductSensor."""
        self._product_name = name
        self._url = url
        self._category = category
        self._attr_unique_id = unique_id
        self._attr_name = f"Product: {name}"
        self._attr_icon = "mdi:barcode-scan"
        self._count = initial_count
        self._additional_attributes = additional_attributes if additional_attributes else {}

    @property
    def native_value(self):
        """Return the current count of the product."""
        return self._count

    @property
    def extra_state_attributes(self):
        """Return additional attributes for the sensor."""
        attrs = {
            "product_name": self._product_name,
            "url": self._url,
            "category": self._category,
            "count": self._count
        }
        # Merge additional attributes
        attrs.update(self._additional_attributes)
        return attrs

    def update_attributes(self, url: str, category: str, additional_attributes: dict = None):
        """Update product attributes."""
        self._url = url
        self._category = category
        if additional_attributes:
            self._additional_attributes = additional_attributes
        self.async_schedule_update_ha_state()
        _LOGGER.debug(f"Updated attributes for {self.entity_id}: URL={self._url}, Category={self._category}, Additional Attributes={self._additional_attributes}")

    def update_count(self, new_count: int):
        """Update the count of the product."""
        self._count = new_count
        self.async_schedule_update_ha_state()
        _LOGGER.debug(f"Updated count for {self.entity_id} to {self._count}")
