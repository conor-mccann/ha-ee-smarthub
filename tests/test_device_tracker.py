"""Tests for the EE SmartHub device tracker platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from ee_smarthub import Host, SmartHubError
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache,
)

from custom_components.ee_smarthub.const import CONSIDER_HOME_INTERVAL, DOMAIN
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from .conftest import MAC

OTHER_MAC = "11:22:33:44:55:66"


def _enable(
    hass: HomeAssistant, entry: MockConfigEntry, mac: str = MAC
) -> er.RegistryEntry:
    """Pre-register an enabled tracker (they are disabled by default)."""
    return er.async_get(hass).async_get_or_create(
        "device_tracker", DOMAIN, mac, config_entry=entry, suggested_object_id=mac[-2:]
    )


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _poll(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


def _set_hosts(mock_client: MagicMock, *hosts: Host) -> None:
    mock_client.get_hosts.return_value = list(hosts)


async def test_new_entities_disabled_by_default(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Discovered devices are registered but disabled until the user opts in."""
    await _setup(hass, mock_config_entry)

    reg_entry = er.async_get(hass).async_get_entity_id("device_tracker", DOMAIN, MAC)
    assert reg_entry is not None
    entity = er.async_get(hass).async_get(reg_entry)
    assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_active_device_is_home(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """An enabled, active device reports home with its IP address."""
    mock_config_entry.add_to_hass(hass)
    entity = _enable(hass, mock_config_entry)
    await _setup(hass, mock_config_entry)

    state = hass.states.get(entity.entity_id)
    assert state.state == STATE_HOME
    assert state.attributes["ip"] == "192.168.1.20"


async def test_consider_home_expiry(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """An inactive device stays home until the consider-home window passes."""
    mock_config_entry.add_to_hass(hass)
    entity = _enable(hass, mock_config_entry)
    await _setup(hass, mock_config_entry)

    _set_hosts(mock_client, Host(mac_address=MAC, active=False))
    freezer.tick(CONSIDER_HOME_INTERVAL - timedelta(seconds=1))
    await _poll(hass, mock_config_entry)
    assert hass.states.get(entity.entity_id).state == STATE_HOME

    freezer.tick(timedelta(seconds=2))
    await _poll(hass, mock_config_entry)
    assert hass.states.get(entity.entity_id).state == STATE_NOT_HOME


async def test_active_but_unconnected_device_expires(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A device the router calls active but shows no link for goes away."""
    mock_config_entry.add_to_hass(hass)
    entity = _enable(hass, mock_config_entry)
    await _setup(hass, mock_config_entry)
    assert hass.states.get(entity.entity_id).state == STATE_HOME

    _set_hosts(mock_client, Host(mac_address=MAC, active=True, connected=False))
    freezer.tick(CONSIDER_HOME_INTERVAL - timedelta(seconds=1))
    await _poll(hass, mock_config_entry)
    assert hass.states.get(entity.entity_id).state == STATE_HOME

    freezer.tick(timedelta(seconds=2))
    await _poll(hass, mock_config_entry)
    assert hass.states.get(entity.entity_id).state == STATE_NOT_HOME


async def test_failed_poll_does_not_refresh_last_seen(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Stale 'active' data kept after a failed poll must not keep a device home."""
    mock_config_entry.add_to_hass(hass)
    entity = _enable(hass, mock_config_entry)
    await _setup(hass, mock_config_entry)
    assert hass.states.get(entity.entity_id).state == STATE_HOME

    mock_client.get_hosts.side_effect = SmartHubError
    freezer.tick(CONSIDER_HOME_INTERVAL - timedelta(seconds=1))
    await _poll(hass, mock_config_entry)
    state = hass.states.get(entity.entity_id)
    assert state.state == STATE_HOME  # not unavailable/unknown

    # HA does not notify listeners on repeated failures; the entity's own expiry
    # timer must flip the state.
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity.entity_id).state == STATE_NOT_HOME


async def test_device_missing_from_router_expires(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A device the router no longer lists goes away after the window."""
    mock_config_entry.add_to_hass(hass)
    entity = _enable(hass, mock_config_entry)
    await _setup(hass, mock_config_entry)

    _set_hosts(mock_client, Host(mac_address=OTHER_MAC, active=True))
    freezer.tick(CONSIDER_HOME_INTERVAL + timedelta(seconds=1))
    await _poll(hass, mock_config_entry)
    assert hass.states.get(entity.entity_id).state == STATE_NOT_HOME


async def test_duplicate_mac_prefers_active(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """If the router lists a MAC twice, the active record wins."""
    _set_hosts(
        mock_client,
        Host(mac_address=MAC, ip_address="10.0.0.1", active=True),
        Host(mac_address=MAC, ip_address="10.0.0.2", active=False),
    )
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.runtime_data.data[MAC].ip_address == "10.0.0.1"


async def test_restores_home_state(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """A device that was home before a restart is home again until it expires."""
    mock_config_entry.add_to_hass(hass)
    entity = _enable(hass, mock_config_entry)
    mock_restore_cache(hass, [State(entity.entity_id, STATE_HOME)])
    _set_hosts(mock_client, Host(mac_address=MAC, active=False))
    await _setup(hass, mock_config_entry)

    assert hass.states.get(entity.entity_id).state == STATE_HOME


async def test_new_device_added_on_poll(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Devices that appear later are registered without a reload."""
    await _setup(hass, mock_config_entry)
    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id("device_tracker", DOMAIN, OTHER_MAC) is None

    _set_hosts(
        mock_client,
        Host(mac_address=MAC, active=True),
        Host(mac_address=OTHER_MAC, active=True),
    )
    await _poll(hass, mock_config_entry)

    assert ent_reg.async_get_entity_id("device_tracker", DOMAIN, OTHER_MAC)


async def test_stale_cleanup_removes_only_disabled(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Forgotten MACs lose disabled entries but keep enabled ones."""
    await _setup(hass, mock_config_entry)  # MAC registered (disabled)
    ent_reg = er.async_get(hass)
    kept = _enable(hass, mock_config_entry, OTHER_MAC)

    _set_hosts(mock_client, Host(mac_address="de:ad:be:ef:00:01", active=True))
    await _poll(hass, mock_config_entry)

    assert ent_reg.async_get_entity_id("device_tracker", DOMAIN, MAC) is None
    assert ent_reg.async_get(kept.entity_id) is not None
