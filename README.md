# EE SmartHub for Home Assistant

A [Home Assistant](https://www.home-assistant.io/) custom integration for EE SmartHub routers. Provides device tracking (presence detection) by querying connected hosts from the router via USP (User Services Platform) over MQTT.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** > **Custom repositories**
3. Add `https://github.com/conor-mccann/ha-ee-smarthub` as an **Integration**
4. Search for "EE SmartHub" and install it
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/ee_smarthub` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "EE SmartHub"
3. Enter your router's host (default: `192.168.1.1`) and password
4. All discovered devices are added as **disabled entities** — enable the ones you want to track in the entity registry

## How It Works

The integration polls your EE SmartHub router every 30 seconds over your local network. It fetches the serial number via HTTPS, then queries connected devices using USP over MQTT. No cloud services are involved — all communication stays on your LAN.

- **New devices** are automatically discovered on each poll — no reload needed.
- **Removed devices** (deleted from the router) are automatically cleaned up from the entity registry.
- Devices remain marked as "home" for 5 minutes after they were last seen active, preventing rapid toggling between home and away states.

## Disclaimer

This project is not affiliated with, endorsed by, or associated with EE Limited or BT Group. "EE" and "SmartHub" are trademarks of their respective owners.

## License

[MIT](LICENSE)
