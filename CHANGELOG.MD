# Changelog

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
