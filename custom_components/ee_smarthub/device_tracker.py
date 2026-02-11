"""Device tracker platform for the EE SmartHub integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import utcnow

from .const import CONSIDER_HOME_INTERVAL
from .coordinator import EESmartHubConfigEntry, EESmartHubDataUpdateCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EESmartHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EE SmartHub device tracker entities."""
    coordinator = entry.runtime_data
    tracked_devices: set[str] = set()

    @callback
    def async_add_new_entities() -> None:
        latest_devices = set(coordinator.data.keys())
        new_devices = latest_devices - tracked_devices

        if not new_devices:
            return

        tracked_devices.update(new_devices)
        async_add_entities(
            EESmartHubScannerEntity(coordinator, mac_address)
            for mac_address in new_devices
        )

    async_add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))


class EESmartHubScannerEntity(
    CoordinatorEntity[EESmartHubDataUpdateCoordinator], ScannerEntity
):
    """Representation of a device connected to the EE SmartHub."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: EESmartHubDataUpdateCoordinator,
        mac_address: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = mac_address
        self._attr_mac_address = mac_address
        self._last_seen: datetime | None = None

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        if (host := self.coordinator.data.get(self.unique_id)) is None:
            return None
        return host.name

    @property
    def hostname(self) -> str | None:
        """Return the hostname of the device."""
        if (host := self.coordinator.data.get(self.unique_id)) is None:
            return None
        return host.hostname or None

    @property
    def ip_address(self) -> str | None:
        """Return the IP address of the device."""
        if (host := self.coordinator.data.get(self.unique_id)) is None:
            return None
        return host.ip_address

    @property
    def is_connected(self) -> bool:
        """Return true if the device is connected or was recently seen."""
        host = self.coordinator.data.get(self.unique_id)
        if host is not None and host.active:
            return True
        if self._last_seen is None:
            return False
        return (utcnow() - self._last_seen).total_seconds() < CONSIDER_HOME_INTERVAL

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update last seen timestamp when device is active."""
        host = self.coordinator.data.get(self.unique_id)
        if host is not None and host.active:
            self._last_seen = utcnow()
        super()._handle_coordinator_update()
