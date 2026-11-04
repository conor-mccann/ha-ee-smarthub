"""Tests for integration setup."""

from __future__ import annotations

from unittest.mock import MagicMock

from ee_smarthub import AuthenticationError, SmartHubError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ee_smarthub.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .conftest import HOST, PASSWORD, SERIAL


async def test_setup_and_unload(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """An entry with a unique ID loads and unloads without extra validation."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_client.validate_connection.assert_not_called()

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


def _legacy_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST, CONF_PASSWORD: PASSWORD}
    )


async def test_legacy_entry_backfills_serial(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """Entries without a unique ID get the router serial on setup."""
    entry = _legacy_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id == SERIAL


@pytest.mark.parametrize(
    ("exception", "state"),
    [
        (AuthenticationError, ConfigEntryState.SETUP_ERROR),
        (SmartHubError, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_legacy_entry_backfill_failure(
    hass: HomeAssistant, mock_client: MagicMock, exception, state
) -> None:
    """Backfill failures map to reauth / retry and leave the ID unset."""
    mock_client.validate_connection.side_effect = exception
    entry = _legacy_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is state
    assert entry.unique_id is None
    if exception is AuthenticationError:
        assert any(
            flow["context"]["source"] == "reauth"
            for flow in hass.config_entries.flow.async_progress()
        )


async def test_auth_failure_starts_reauth(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """An auth error from the first poll triggers a reauth flow."""
    mock_client.get_hosts.side_effect = AuthenticationError
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    assert any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )
