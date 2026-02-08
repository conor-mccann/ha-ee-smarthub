"""Device tracker platform for the EE SmartHub integration."""

from __future__ import annotations

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EESmartHubConfigEntry
from .const import CONF_HOSTNAME, CONF_TRACKED_DEVICES
from .coordinator import EESmartHubCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: EESmartHubConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up EE SmartHub device tracker entities."""
    coordinator = entry.runtime_data
    hostname = entry.data[CONF_HOSTNAME]

    tracked_macs: list[str] = entry.options.get(CONF_TRACKED_DEVICES, [])

    async_add_entities(
        EESmartHubScannerEntity(coordinator, mac, hostname)
        for mac in tracked_macs
        if mac in coordinator.data
    )


class EESmartHubScannerEntity(CoordinatorEntity[EESmartHubCoordinator], ScannerEntity):
    """Represent a device connected to the EE SmartHub."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EESmartHubCoordinator, mac: str, hostname: str
    ) -> None:
        """Initialize the scanner entity."""
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{hostname}_{mac}"

        host = coordinator.data[mac]
        self._attr_name = host.name

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected."""
        if (host := self.coordinator.data.get(self._mac)) is not None:
            return host.active
        return False

    @property
    def ip_address(self) -> str | None:
        """Return the IP address of the device."""
        if (host := self.coordinator.data.get(self._mac)) is not None:
            return host.ip_address or None
        return None

    @property
    def mac_address(self) -> str:
        """Return the MAC address of the device."""
        return self._mac

    @property
    def hostname(self) -> str | None:
        """Return the hostname of the device."""
        if (host := self.coordinator.data.get(self._mac)) is not None:
            return host.hostname or None
        return None

