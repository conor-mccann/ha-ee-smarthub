"""Device tracker platform for the EE SmartHub integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
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
    entity_registry = er.async_get(hass)
    tracked_devices: set[str] = set()

    @callback
    def async_add_new_entities() -> None:
        latest_devices = set(coordinator.data.keys())
        devices_to_remove = tracked_devices - latest_devices
        devices_to_add = latest_devices - tracked_devices

        for entity_entry in entity_registry.entities.get_entries_for_config_entry_id(
            entry.entry_id
        ):
            if entity_entry.unique_id in devices_to_remove:
                entity_registry.async_remove(entity_entry.entity_id)

        if devices_to_add:
            async_add_entities(
                EESmartHubScannerEntity(coordinator, mac_address)
                for mac_address in devices_to_add
            )

        tracked_devices.clear()
        tracked_devices.update(latest_devices)

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
    def available(self) -> bool:
        """Return True even when coordinator update fails.

        Transient timeouts should not send devices to "unknown" — the cached
        data and consider-home logic remain valid.
        """
        return True

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
