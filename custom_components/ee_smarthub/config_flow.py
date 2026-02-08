"""Config flow for the EE SmartHub integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from ee_smarthub import AuthenticationError, SmartHubClient, SmartHubError

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_HOSTNAME,
    CONF_PASSWORD,
    CONF_TRACKED_DEVICES,
    DEFAULT_HOSTNAME,
    DOMAIN,
)
from .coordinator import EESmartHubCoordinator

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOSTNAME, default=DEFAULT_HOSTNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class EESmartHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EE SmartHub."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOSTNAME])
            self._abort_if_unique_id_configured()

            client = SmartHubClient(
                user_input[CONF_HOSTNAME], user_input[CONF_PASSWORD]
            )
            try:
                await client.get_hosts()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except SmartHubError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"EE SmartHub ({user_input[CONF_HOSTNAME]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EESmartHubOptionsFlow:
        """Get the options flow for this handler."""
        return EESmartHubOptionsFlow()


class EESmartHubOptionsFlow(OptionsFlow):
    """Handle options flow for EE SmartHub."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the tracked devices option."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        coordinator: EESmartHubCoordinator = self.config_entry.runtime_data

        # Build multi-select options from discovered devices
        device_options: dict[str, str] = {}
        for mac, host in coordinator.data.items():
            device_options[mac] = f"{host.name} ({mac})"

        # Default to currently tracked devices, or all devices
        current_tracked = self.config_entry.options.get(
            CONF_TRACKED_DEVICES, list(device_options.keys())
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TRACKED_DEVICES, default=current_tracked
                    ): cv.multi_select(device_options),
                }
            ),
        )
