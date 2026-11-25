"""Device tracker platform for the EE SmartHub integration."""

from __future__ import annotations

from datetime import datetime

from ee_smarthub import Host

from homeassistant.components.device_tracker import STATE_HOME, ScannerEntity
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONSIDER_HOME_INTERVAL
from .coordinator import EESmartHubConfigEntry, EESmartHubDataUpdateCoordinator

PARALLEL_UPDATES = 0


@callback
def _async_remove_stale_entries(
    ent_reg: er.EntityRegistry, entry: EESmartHubConfigEntry, current: set[str]
) -> set[str]:
    """Remove disabled registry entries for MACs no longer on the router.

    Return the unique IDs removed.
    """
    removed: set[str] = set()
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.disabled_by is not None and reg_entry.unique_id not in current:
            ent_reg.async_remove(reg_entry.entity_id)
            removed.add(reg_entry.unique_id)
    return removed


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EESmartHubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EE SmartHub device tracker entities."""
    coordinator = entry.runtime_data
    ent_reg = er.async_get(hass)
    known: set[str] = set()

    @callback
    def _async_sync_entities() -> None:
        current = set(coordinator.data)
        known.difference_update(_async_remove_stale_entries(ent_reg, entry, current))
        if new := current - known:
            known.update(new)
            async_add_entities(EESmartHubScannerEntity(coordinator, mac) for mac in new)

    _async_sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_sync_entities))


class EESmartHubScannerEntity(
    CoordinatorEntity[EESmartHubDataUpdateCoordinator], ScannerEntity, RestoreEntity
):
    """Representation of a device connected to the EE SmartHub."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EESmartHubDataUpdateCoordinator, mac_address: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_mac_address = mac_address
        self._last_seen: datetime | None = None
        self._expiry_unsub: CALLBACK_TYPE | None = None

    @property
    def available(self) -> bool:
        """Return True so coordinator failures don't make devices unknown."""
        return True

    @property
    def name(self) -> str | None:
        """Return the name of the device."""
        return host.name if (host := self._host) else None

    @property
    def hostname(self) -> str | None:
        """Return the hostname of the device."""
        return (host.hostname or None) if (host := self._host) else None

    @property
    def ip_address(self) -> str | None:
        """Return the IP address of the device."""
        return host.ip_address if (host := self._host) else None

    @property
    def is_connected(self) -> bool:
        """Return True if the device was seen within the consider-home window."""
        return (
            self._last_seen is not None
            and dt_util.utcnow() - self._last_seen < CONSIDER_HOME_INTERVAL
        )

    @property
    def _host(self) -> Host | None:
        return self.coordinator.data.get(self._attr_mac_address)

    async def async_added_to_hass(self) -> None:
        """Seed last-seen from the restored state and current data."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and (
            last_state.state == STATE_HOME
        ):
            self._set_last_seen()
        self._update_last_seen()
        self.async_on_remove(self._cancel_expiry)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Refresh last-seen and write state."""
        self._update_last_seen()
        super()._handle_coordinator_update()

    def _update_last_seen(self) -> None:
        # Ignore stale data kept after a failed update.
        # `active` alone can stay set after a device has left.
        if (
            self.coordinator.last_update_success
            and (host := self._host)
            and host.active
            and host.connected
        ):
            self._set_last_seen()

    @callback
    def _set_last_seen(self) -> None:
        """Record a sighting and schedule the state write for when it expires.

        The coordinator does not notify listeners on repeated failed polls, so
        without this a device would stay home through a sustained outage.
        """
        self._last_seen = dt_util.utcnow()
        self._cancel_expiry()
        self._expiry_unsub = async_track_point_in_utc_time(
            self.hass, self._async_expire, self._last_seen + CONSIDER_HOME_INTERVAL
        )

    @callback
    def _cancel_expiry(self) -> None:
        if self._expiry_unsub:
            self._expiry_unsub()
            self._expiry_unsub = None

    @callback
    def _async_expire(self, _now: datetime) -> None:
        self._expiry_unsub = None
        self.async_write_ha_state()
