"""The EE SmartHub integration."""

from __future__ import annotations

from ee_smarthub import SmartHubClient

from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant

from .coordinator import EESmartHubConfigEntry, EESmartHubDataUpdateCoordinator

_PLATFORMS: list[Platform] = [Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: EESmartHubConfigEntry) -> bool:
    """Set up EE SmartHub from a config entry."""
    client = SmartHubClient(entry.data[CONF_HOST], entry.data[CONF_PASSWORD])
    coordinator = EESmartHubDataUpdateCoordinator(hass, entry, client)

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: EESmartHubConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
