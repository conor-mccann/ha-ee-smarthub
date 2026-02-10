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

- **`__init__.py`** — Entry setup/unload. Creates the `SmartHubClient` and coordinator, forwards to the `device_tracker` platform.
- **`coordinator.py`** — `EESmartHubDataUpdateCoordinator` extends `DataUpdateCoordinator[dict[str, Host]]`. Polls every 30 seconds. Returns `{mac_address: Host}` dict. Raises `ConfigEntryAuthFailed` on auth errors. Also defines the `EESmartHubConfigEntry` type alias.
- **`device_tracker.py`** — `EESmartHubScannerEntity` extends both `CoordinatorEntity` and `ScannerEntity`. One entity per discovered MAC address. All entities are **disabled by default** (`_attr_entity_registry_enabled_default = False`); users enable the ones they want.
- **`config_flow.py`** — Single config flow (host + password, validates by calling `get_hosts()`). Uses `_async_abort_entries_match` to prevent duplicates. No options flow yet.
- **`const.py`** — Domain name and defaults (`DEFAULT_HOST`, `DEFAULT_SCAN_INTERVAL`). Uses HA's built-in `CONF_HOST` and `CONF_PASSWORD` constants.
- **`strings.json` / `translations/en.json`** — UI strings for the config flow, using HA common translation keys where possible.

## Key Patterns

- Coordinator stores data as `dict[str, Host]` keyed by MAC address.
- `entry.runtime_data` stores the coordinator instance (no `hass.data[DOMAIN]` pattern).
- `SmartHubClient` is created in `__init__.py` and injected into the coordinator.
- All discovered devices are added as disabled entities; users enable what they want.
- New devices connecting after initial setup are not added until integration reload.
- The integration uses `iot_class: local_polling` — all communication is local to the network.

## Development

Python 3.14 venv at `.venv/`. Activate with:

```
source .venv/bin/activate
```

No build system, tests, linter config, or CI are currently configured in this repo.

## Tool Usage

Always use Context7 MCP when you need library/API documentation, code generation, setup or configuration steps without the user having to explicitly ask.
