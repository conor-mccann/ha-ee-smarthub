"""The EE SmartHub integration."""

from __future__ import annotations

from importlib import import_module

from ee_smarthub import SmartHubClient

from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import EESmartHubConfigEntry, EESmartHubDataUpdateCoordinator

_PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]


def _preload_pydantic_modules() -> None:
    """Pre-load pydantic modules to avoid lazy-import warnings in the event loop."""
    import_module("pydantic.dataclasses")
    import_module("pydantic.warnings")


async def async_setup_entry(hass: HomeAssistant, entry: EESmartHubConfigEntry) -> bool:
    """Set up EE SmartHub from a config entry."""
    await hass.async_add_executor_job(_preload_pydantic_modules)

    session = async_get_clientsession(hass)
    client = SmartHubClient(entry.data[CONF_HOST], entry.data[CONF_PASSWORD], session)
    coordinator = EESmartHubDataUpdateCoordinator(hass, entry, client)

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EESmartHubConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
