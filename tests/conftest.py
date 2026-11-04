"""Shared fixtures for the EE SmartHub tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from ee_smarthub import Host
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ee_smarthub.const import DOMAIN
from homeassistant.const import CONF_HOST, CONF_PASSWORD

HOST = "192.168.1.1"
PASSWORD = "secret"
SERIAL = "SERIAL123"
MAC = "aa:bb:cc:dd:ee:ff"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the custom integration in every test."""


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Patch SmartHubClient everywhere it is constructed."""
    with (
        patch("custom_components.ee_smarthub.SmartHubClient") as init_cls,
        patch("custom_components.ee_smarthub.config_flow.SmartHubClient") as flow_cls,
    ):
        client = MagicMock()
        client.validate_connection = AsyncMock(return_value=SERIAL)
        client.get_hosts = AsyncMock(
            return_value=[Host(mac_address=MAC, ip_address="192.168.1.20", active=True)]
        )
        init_cls.return_value = client
        flow_cls.return_value = client
        yield client


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry that already has the serial as unique ID."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"EE SmartHub ({HOST})",
        unique_id=SERIAL,
        data={CONF_HOST: HOST, CONF_PASSWORD: PASSWORD},
    )
