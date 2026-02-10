"""Device tracker platform for the EE SmartHub integration."""

from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, HomeAssistant

from .coordinator import EESmartHubConfigEntry, EESmartHubDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EESmartHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EE SmartHub device tracker entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        EESmartHubScannerEntity(coordinator, mac_address)
        for mac_address in coordinator.data
    )


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
        """Return true if the device is connected."""
        if (host := self.coordinator.data.get(self.unique_id)) is None:
            return False
        return host.active
