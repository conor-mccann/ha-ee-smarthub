"""DataUpdateCoordinator for EE SmartHub integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from ee_smarthub import AuthenticationError, Host, SmartHubClient, SmartHubError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type EESmartHubConfigEntry = ConfigEntry[EESmartHubDataUpdateCoordinator]


class EESmartHubDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Host]]):
    """Coordinator to fetch data from EE SmartHub."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: EESmartHubConfigEntry,
        client: SmartHubClient,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )

        self._client = client

    async def _async_update_data(self) -> dict[str, Host]:
        """Fetch data from EE SmartHub."""
        try:
            hosts = await self._client.get_hosts()
            return {host.mac_address: host for host in hosts}
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="invalid_auth",
            ) from err
        except SmartHubError as err:
            raise UpdateFailed(f"Error communicating with SmartHub: {err}") from err
