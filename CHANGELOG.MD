# Changelog

## [Version 1.0.5](https://github.com/mintcreg/pantry_tracker_sensor/releases/tag/v1.0.5)

- Config flow now utilised

>[!IMPORTANT]
>Remove the below from config.yaml!

```yaml
sensor:
  - platform: pantry_tracker
    scan_interval: 30  # (Optional) defaults to 30 if not defined
```

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
