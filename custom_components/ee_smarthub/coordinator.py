"""DataUpdateCoordinator for the EE SmartHub integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from ee_smarthub import (
    AuthenticationError,
    Host,
    SmartHubClient,
    SmartHubError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_HOSTNAME, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EESmartHubCoordinator(DataUpdateCoordinator[dict[str, Host]]):
    """Coordinator to fetch device data from the EE SmartHub."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="EE SmartHub",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self._hostname: str = entry.data[CONF_HOSTNAME]
        self._password: str = entry.data[CONF_PASSWORD]
        self._client = SmartHubClient(self._hostname, self._password)

    async def _async_update_data(self) -> dict[str, Host]:
        """Fetch hosts from the SmartHub."""
        try:
            hosts = await self._client.get_hosts()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain="ee_smarthub",
                translation_key="invalid_auth",
            ) from err
        except SmartHubError as err:
            raise UpdateFailed(f"Error communicating with SmartHub: {err}") from err

        return {host.mac_address: host for host in hosts}
