"""Config flow for the EE SmartHub integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from ee_smarthub import AuthenticationError, SmartHubClient, SmartHubError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PASSWORD): str,
    }
)
STEP_REAUTH_DATA_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


def _title(host: str) -> str:
    """Return the config entry title for a router host."""
    return f"EE SmartHub ({host})"


class EESmartHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EE SmartHub."""

    VERSION = 1

    async def _async_validate(
        self, host: str, password: str
    ) -> tuple[str | None, str | None]:
        """Try to connect; return (serial, None) or (None, error key)."""
        client = SmartHubClient(host, password, async_get_clientsession(self.hass))
        try:
            return await client.validate_connection(), None
        except AuthenticationError:
            return None, "invalid_auth"
        except SmartHubError:
            return None, "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return None, "unknown"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            serial, error = await self._async_validate(
                user_input[CONF_HOST], user_input[CONF_PASSWORD]
            )
            if serial:
                await self.async_set_unique_id(serial)
                # Router already set up: just follow it to its new address.
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: user_input[CONF_HOST]}
                )
                return self.async_create_entry(
                    title=_title(user_input[CONF_HOST]), data=user_input
                )
            errors["base"] = error or "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication when the stored password stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new password."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            serial, error = await self._async_validate(
                entry.data[CONF_HOST], user_input[CONF_PASSWORD]
            )
            if serial:
                await self.async_set_unique_id(serial)
                if entry.unique_id is not None:
                    self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=serial,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            errors["base"] = error or "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            description_placeholders={CONF_HOST: entry.data[CONF_HOST]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the router host and/or password."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            serial, error = await self._async_validate(
                user_input[CONF_HOST], user_input[CONF_PASSWORD]
            )
            if serial:
                await self.async_set_unique_id(serial)
                if entry.unique_id is not None:
                    self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=serial,
                    title=_title(user_input[CONF_HOST]),
                    data_updates=user_input,
                )
            errors["base"] = error or "unknown"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )
