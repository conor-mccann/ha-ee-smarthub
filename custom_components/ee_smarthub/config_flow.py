"""Config flow for the EE SmartHub integration."""

from __future__ import annotations

import logging
from typing import Any

from ee_smarthub import AuthenticationError, SmartHubClient, SmartHubError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DEFAULT_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    client = SmartHubClient(data[CONF_HOST], data[CONF_PASSWORD])
    await client.get_hosts()

    return {"title": f"EE SmartHub ({data[CONF_HOST]})"}


class EESmartHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EE SmartHub."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except SmartHubError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
