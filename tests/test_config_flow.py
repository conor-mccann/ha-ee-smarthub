"""Tests for the EE SmartHub config flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ee_smarthub import AuthenticationError, SmartHubError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ee_smarthub.const import DOMAIN
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import HOST, PASSWORD, SERIAL

USER_INPUT = {CONF_HOST: HOST, CONF_PASSWORD: PASSWORD}


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Skip real setup after a flow finishes."""
    with patch(
        "custom_components.ee_smarthub.async_setup_entry", return_value=True
    ) as mock:
        yield mock


async def _start_user_flow(hass: HomeAssistant, user_input=USER_INPUT):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )


async def test_user_flow(hass: HomeAssistant, mock_client: MagicMock) -> None:
    """A valid submission creates an entry keyed by the router serial."""
    result = await _start_user_flow(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"EE SmartHub ({HOST})"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == SERIAL


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (AuthenticationError, "invalid_auth"),
        (SmartHubError, "cannot_connect"),
        (RuntimeError, "unknown"),
    ],
)
async def test_user_flow_errors_then_recovers(
    hass: HomeAssistant, mock_client: MagicMock, exception, error
) -> None:
    """Errors are shown on the form and the flow can still complete."""
    mock_client.validate_connection.side_effect = exception
    result = await _start_user_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_client.validate_connection.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured_updates_host(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Adding a known router at a new address aborts and follows the new host."""
    mock_config_entry.add_to_hass(hass)

    result = await _start_user_flow(
        hass, {CONF_HOST: "192.168.1.2", CONF_PASSWORD: PASSWORD}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "192.168.1.2"


async def test_reauth_flow(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Reauth stores the new password and aborts with success."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == {CONF_HOST: HOST, CONF_PASSWORD: "new"}


async def test_reauth_flow_invalid_auth(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """A wrong password keeps the form open with an error."""
    mock_config_entry.add_to_hass(hass)
    mock_client.validate_connection.side_effect = AuthenticationError
    result = await mock_config_entry.start_reauth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "bad"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert mock_config_entry.data[CONF_PASSWORD] == PASSWORD


async def test_reauth_flow_wrong_device(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Reauth aborts if a different router answers at the stored host."""
    mock_config_entry.add_to_hass(hass)
    mock_client.validate_connection.return_value = "OTHER"
    result = await mock_config_entry.start_reauth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert mock_config_entry.data[CONF_PASSWORD] == PASSWORD


async def test_reauth_flow_sets_missing_unique_id(
    hass: HomeAssistant, mock_client: MagicMock
) -> None:
    """A legacy entry without a unique ID gets the serial during reauth."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new"}
    )

    assert result["reason"] == "reauth_successful"
    assert entry.unique_id == SERIAL


async def test_reconfigure_flow(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfigure updates host, password and title on the same entry."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.1", CONF_PASSWORD: "new"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == {CONF_HOST: "10.0.0.1", CONF_PASSWORD: "new"}
    assert mock_config_entry.title == "EE SmartHub (10.0.0.1)"
    assert mock_config_entry.unique_id == SERIAL
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reconfigure_flow_wrong_device(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfiguring to a different router is rejected."""
    mock_config_entry.add_to_hass(hass)
    mock_client.validate_connection.return_value = "OTHER"
    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.1", CONF_PASSWORD: "new"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert mock_config_entry.data[CONF_HOST] == HOST


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant, mock_client: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """A failed connection keeps the form open with an error."""
    mock_config_entry.add_to_hass(hass)
    mock_client.validate_connection.side_effect = SmartHubError
    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.1", CONF_PASSWORD: "new"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
