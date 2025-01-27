# Changelog

## [Version 1.0.7-dev](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.7)

#### 🔨 Fixes:
- **Config flow update** - Updating the update interval or source would not actually apply new variables now fixed
- **Enhanced Exception Handling:** - Added comprehensive try-except blocks in setup functions to catch and log unexpected errors.
- **Sensor Initialization Stability:** - Fixed issues in sensor setup to gracefully handle missing or incomplete product data.
- **Failed to load integration** - The error failed to load integration NoneType: None has now been fixed


#### ⭐ Changes:
- **Expanded Configuration Options:** - Added fields for Host, Port, API Key, and Update Interval in the configuration flow. 
- **Enhanced Logging**
- **Reload Config** - When changing the config (Host, Port, API Key, and Update Interval) this will reload all sensors gracefully
- **API Key** - As of [Pantry Tracker V1.0.54](https://github.com/mintcreg/pantry_tracker/releases/tag/v1.0.54) API keys have been introduced and required for added security


#### TODO

- API Key
 

## [Version 1.0.6](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.6)

-  Updating to HA version 2025.1.2 breaks service calls (now fixed)

## [Version 1.0.5](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.5)

- Changed naming convention to Pantry Tracker Sensor (from components)
- Added config flow (this will not affect any sensors already created)

## Update Steps:

- After updating, add integration via Settings > Devices > Add Integration > Pantry Tracker Sensor
- Remove the below YAML from config.yaml
```yaml
sensor:
  - platform: pantry_tracker
    scan_interval: 30  # (Optional) defaults to 30 if not defined
```
- Restart HomeAssistant


## [Version 1.0.4](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.4)

- Barcode Attribute added
- Sensor attributes will now pull any additional attributes (future proofing for additional values later)
- Added barcode_increase / barcode_decrease services (I may look into this in future but it allows you to use this service with other automations etc...)
- Now handles ingress for Pantry Tracker v1.0.51

>[!IMPORTANT]
>Ensure you reboot HomeAssistant after updating!

## [Version 1.0.3](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.3)

## [Version 1.0.2](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.2)

## [Version 1.0.1](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.1)

## [Version 1.0.0](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.0)
