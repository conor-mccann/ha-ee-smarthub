# AGENTS.md

## Project Overview

This is a **Home Assistant custom integration** for EE SmartHub routers, distributed via [HACS](https://hacs.xyz/). It provides device tracking (presence detection) by querying connected hosts from the router via USP (User Services Platform) over MQTT.

**Domain:** `ee_smarthub`
**Platform:** `device_tracker` (single platform)

## Dependencies

- **Python library:** `ee-smarthub==0.6.0` — async client that communicates with EE SmartHub routers. Fetches the router serial via HTTPS (`/config.json`), then queries `Device.Hosts.Host.*` via USP/MQTT to get connected devices. Uses betterproto2 for USP protobuf messages.
- **Key types from `ee_smarthub`:** `SmartHubClient`, `Host`, `AuthenticationError`, `SmartHubError`
- The `Host` dataclass has fields: `mac_address`, `ip_address`, `hostname`, `user_friendly_name`, `interface_type`, `active`, `frequency_band`, `bytes_sent`, `bytes_received`, `connected`. A device counts as seen only if both `active` and `connected` are true, because the router can leave `active` set after a device has left. `Host.name` is a property that cascades: `user_friendly_name` → `hostname` → `mac_address`.
- `SmartHubClient` accepts an `aiohttp.ClientSession` parameter for shared session management.

## Architecture

All integration code lives under `custom_components/ee_smarthub/`.

- **`__init__.py`** — Entry setup/unload. Creates the `SmartHubClient` (with HA's shared aiohttp session) and coordinator, forwards to the `device_tracker` platform. Pre-loads pydantic modules on an executor to work around betterproto2's optional lazy import of pydantic failing in the event loop.
- **`coordinator.py`** — `EESmartHubDataUpdateCoordinator` extends `DataUpdateCoordinator[dict[str, Host]]`. Polls every 30 seconds. Returns `{mac_address: Host}` dict. Raises `ConfigEntryAuthFailed` on auth errors. Also defines the `EESmartHubConfigEntry` type alias.
- **`device_tracker.py`** — `EESmartHubScannerEntity` extends both `CoordinatorEntity` and `ScannerEntity`. One entity per discovered MAC address. Entities are **disabled by default** via HA's `ScannerEntity` logic (no matching device entry); users enable the ones they want. Still-disabled registry entries are removed once the router forgets the MAC; enabled ones are kept so person assignments survive. Implements a "consider home" interval (10 min, a `timedelta` in `const.py`) to prevent flapping from WiFi power-saving; each sighting schedules a state write at expiry, because the coordinator doesn't notify listeners on repeated failed polls. Overrides `available` to always return `True` so transient coordinator failures (timeouts) don't send devices to "unknown".
- **`config_flow.py`** — Config flow with `user`, `reauth`/`reauth_confirm` (new password; triggered by the coordinator's `ConfigEntryAuthFailed`) and `reconfigure` (change host and/or password) steps. All validate via `_async_validate()`, which calls `validate_connection()` and returns `(serial, error)`; the router serial is the entry's unique ID. The user step follows an already-configured router to a new host via `_abort_if_unique_id_configured(updates=...)`; reauth/reconfigure abort with `wrong_device` on serial mismatch; `async_setup_entry` backfills the serial for legacy entries. No options flow yet.
- **`const.py`** — Domain name and defaults (`DEFAULT_HOST`, `DEFAULT_SCAN_INTERVAL`, `CONSIDER_HOME_INTERVAL`). Uses HA's built-in `CONF_HOST` and `CONF_PASSWORD` constants.
- **`strings.json` / `translations/en.json`** — UI strings for the config flow, using HA common translation keys where possible.

## Key Patterns

- Coordinator stores data as `dict[str, Host]` keyed by MAC address.
- `entry.runtime_data` stores the coordinator instance (no `hass.data[DOMAIN]` pattern).
- `SmartHubClient` is created in `__init__.py` and injected into the coordinator.
- All discovered devices are added as disabled entities; users enable what they want.
- New devices are dynamically discovered on each coordinator poll — no reload needed.
- Disabled entities for MACs the router has forgotten are removed from the registry; enabled ones are never auto-removed.
- `SmartHubClient` receives HA's shared aiohttp session via `async_get_clientsession(hass)`.
- The integration uses `iot_class: local_polling` — all communication is local to the network.

## Development

Python 3.14 venv at `.venv/`. Activate with:

```
source .venv/bin/activate
```

Tests live in `tests/` (`pip install -r requirements_test.txt`, then `pytest`). They use `pytest-homeassistant-custom-component` with `SmartHubClient` mocked. No build system, linter config, or CI is configured.

## Tool Usage

Always use Context7 MCP when you need library/API documentation, code generation, setup or configuration steps without the user having to explicitly ask.
