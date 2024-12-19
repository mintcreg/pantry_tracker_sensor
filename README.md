# <p align="center"> Pantry Tracker - Custom Components </p>

<p align="center">
<img src="https://github.com/mintcreg/pantry_tracker/blob/main/images/logo.webp" alt="Pantry Tracker Card Logo" width="300">
</p>

> [!CAUTION]
> This is a work in progress and made using GPT and basic knowledge.

## Description

The **Pantry Tracker Custom Components** repository provides a set of Home Assistant integrations to enable seamless interaction between the **Pantry Tracker Add-on** and Home Assistant. These components allow you to automatically create sensors for pantry categories and products, update their counts in real time, and manage their lifecycle effectively.

---

## Features

- 🖥️ **Dynamic Sensor Creation**  
  Automatically creates sensors for each product and category stored in the Pantry Tracker database.

- 📊 **Real-Time Count Updates**  
  Synchronizes product counts between Home Assistant and the Pantry Tracker Add-on.

- ❌ **Automatic Cleanup**  
  Removes sensors for products that are deleted from the database to ensure a clean and up-to-date system.

- 🔄 **Bi-Directional Updates**  
  Supports increasing and decreasing product counts from Home Assistant services.

---

## Requirements

1. **Pantry Tracker Add-on**  
   The [Pantry Tracker Add-on](https://github.com/mintcreg/pantry_tracker) must be installed and running.

2. **Flask API Connection**  
   The custom component connects to the Flask API provided by the add-on. Ensure the API is accessible and running on the default port `5000`.

---

## Installation

1. Add [https://github.com/mintcreg/pantry_tracker_sensor](https://github.com/mintcreg/pantry_tracker_sensor) to HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mintcreg&repository=pantry_tracker_sensor&category=Integration)

3. Install from HACS

4. Add the below to config.yaml
   ```yaml
   sensor:
     - platform: pantry_tracker
       scan_interval: 30  # (Optional) defaults to 30 if not defined
       source: http://127.0.0.1:5000 # (Optional) defaults to http://127.0.0.1:5000 if not defined
   ```
   

5. Restart HomeAssistant

**Alternatively**

1. Download and Install 
   Copy the `pantry_tracker` folder to the `custom_components` directory in your Home Assistant configuration.

2. Add the below to config.yaml
   ```yaml
   sensor:
     - platform: pantry_tracker
       scan_interval: 30  # (Optional) defaults to 30 if not defined
       source: http://127.0.0.1:5000 # (Optional) defaults to http://127.0.0.1:5000 if not defined
   ```

## Usage

<details>
<summary>Auto Entities & Browsermod (No Tracker Card)</summary>
 
<br>

```yaml
type: custom:auto-entities
card:
  type: entities
  title: Pantry Products
  show_header_toggle: false
  state_color: true
filter:
  include:
    - entity_id: sensor.product_*
      options:
        type: custom:template-entity-row
        name: |
          {{ state_attr(config.entity, 'product_name') }}
        tap_action:
          action: fire-dom-event
          browser_mod:
            service: browser_mod.popup
            data:
              title: Update Stock
              content:
                type: vertical-stack
                cards:
                  - type: custom:mushroom-template-card
                    entity: this.entity_id
                    primary: |
                      Product: {{ state_attr(entity, 'product_name') }}
                    secondary: |
                      Stock Count: {{ states(entity) }}
                    icon: mdi:food-apple
                    layout: vertical
              right_button: Add 1 Item
              left_button: Remove 1 Item
              right_button_action:
                service: pantry_tracker.increase_count
                data:
                  entity_id: this.entity_id
                  amount: 1
              left_button_action:
                service: pantry_tracker.decrease_count
                data:
                  entity_id: this.entity_id
                  amount: 1

  ```

### Demo

![Categories](https://raw.githubusercontent.com/mintcreg/pantry_tracker_sensor/main/images/no-card.gif)



</details>

<details>
<summary>Tracker Card </summary>
<br>
Requires the Pantry Tracker Card - https://github.com/mintcreg/pantry_tracker_card
<br>

```yaml
type: custom:pantry-card
entity_prefix: sensor.product
search: true
show_images: true
category_filter: true
  ```


</details>





## Services

The custom component provides the following services to interact with pantry products:

| **Service**                    | **Parameters**                                                                                     | **Description**                                    |
|--------------------------------|---------------------------------------------------------------------------------------------------|----------------------------------------------------|
| `pantry_tracker.increase_count` | `product_name` (string) <br> `amount` (int, optional, default: 1)                                   | Increase the count of a specific product by its name. |
| `pantry_tracker.decrease_count` | `product_name` (string) <br> `amount` (int, optional, default: 1)                                   | Decrease the count of a specific product by its name. |



### `pantry_tracker.increase_count`
**Description**: Increases the count of a specified product.

- **Parameters**:
  - `entity_id` (string, required): The entity ID of the product. Example: `sensor.product_apple`.
  - `amount` (integer, optional): The amount to increase the count by (default: `1`).

- **Example Service Call**:
  ```yaml
  service: pantry_tracker.increase_count
  data:
    entity_id: sensor.product_apple
    amount: 2
  ```

### `pantry_tracker.decrease_count`

**Description**: Decreases the count of a specified product.

#### Parameters:
- `entity_id` (string, required): The entity ID of the product.  
  Example: `sensor.product_banana`.
- `amount` (integer, optional): The amount to decrease the count by (default: `1`).

#### Example Service Call:
```yaml
service: pantry_tracker.decrease_count
data:
  entity_id: sensor.product_banana
  amount: 1
```




## Future Improvements
- Ability to set the polling rate from default (30 seconds)


