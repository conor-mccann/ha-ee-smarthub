# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Home Assistant custom integration** for EE SmartHub routers, distributed via [HACS](https://hacs.xyz/). It provides device tracking (presence detection) by querying connected hosts from the router via USP (User Services Platform) over MQTT.

**Domain:** `ee_smarthub`
**Platform:** `device_tracker` (single platform)

## Dependencies

- **Python library:** `ee-smarthub==0.1.0` — async client that communicates with EE SmartHub routers. Fetches the router serial via HTTPS (`/config.json`), then queries `Device.Hosts.Host.*` via USP/MQTT to get connected devices.
- **Key types from `ee_smarthub`:** `SmartHubClient`, `Host`, `AuthenticationError`, `SmartHubError`
- The `Host` dataclass has fields: `mac_address`, `ip_address`, `hostname`, `user_friendly_name`, `interface_type`, `active`, `frequency_band`, `bytes_sent`, `bytes_received`.

## Architecture

All integration code lives under `custom_components/ee_smarthub/`.

- **`__init__.py`** — Entry setup/unload. Creates the coordinator, forwards to the `device_tracker` platform, and registers an update listener for options changes (which triggers a full reload).
- **`coordinator.py`** — `EESmartHubCoordinator` extends `DataUpdateCoordinator[dict[str, Host]]`. Polls every 30 seconds. Creates a new `SmartHubClient` per update cycle. Returns `{mac_address: Host}` dict. Raises `ConfigEntryAuthFailed` on auth errors.
- **`device_tracker.py`** — `EESmartHubScannerEntity` extends both `CoordinatorEntity` and `ScannerEntity`. One entity per tracked MAC address. On fresh install, all discovered devices are tracked; users can narrow via options flow.
- **`config_flow.py`** — Two flows: the initial config flow (hostname + password, validates by calling `get_hosts()`), and an options flow that shows a multi-select of discovered devices to choose which to track.
- **`const.py`** — Domain name, config keys (`hostname`, `password`, `tracked_devices`), defaults.
- **`strings.json` / `translations/en.json`** — UI strings for config and options flows (currently identical content).

## Key Patterns

- Coordinator stores data as `dict[str, Host]` keyed by MAC address.
- `entry.runtime_data` stores the coordinator instance (no `hass.data[DOMAIN]` pattern).
- No devices are tracked by default on fresh install; users must select devices via the options flow.
- Options updates trigger a full config entry reload via `_async_update_listener`.
- Config flow uses `_async_abort_entries_match` on hostname to prevent duplicates.
- The integration uses `iot_class: local_polling` — all communication is local to the network.

## Development

Python 3.14 venv at `.venv/`. Activate with:

```
source .venv/bin/activate
```

No build system, tests, linter config, or CI are currently configured in this repo.

## Tool Usage

Always use Context7 MCP when you need library/API documentation, code generation, setup or configuration steps without the user having to explicitly ask.
