"""Config flow to configure Coolmaster."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import core
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PROTOCOL
from homeassistant.data_entry_flow import FlowResult
from pycoolmasternet_ng import exceptions, models

from . import _get_transport_from_config_data
from .const import (
    CONF_SERIAL_BAUD,
    CONF_SERIAL_URL,
    DEFAULT_BAUD_RATE,
    DEFAULT_PORT,
    DOMAIN,
    PROTOCOL_SERIAL,
    PROTOCOL_SOCKET,
)


class CoolmasterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Coolmaster config flow."""

    VERSION = 2

    @core.callback
    def _async_get_entry(self, user_input: dict[str, Any]) -> FlowResult:
        if self.protocol == PROTOCOL_SOCKET:
            title = "TCP at " + user_input[CONF_HOST]

            if port := user_input.get(CONF_PORT):
                title += f":{port}"
        elif self.protocol == PROTOCOL_SERIAL:
            title = "Serial at " + user_input[CONF_SERIAL_URL]

            if baud_rate := user_input.get(CONF_SERIAL_BAUD):
                title += f" @ {baud_rate} baud"
        else:
            raise ValueError(f"Unsupported protocol {self.protocol}")

        return self.async_create_entry(
            title=title,
            data={CONF_PROTOCOL: self.protocol, **user_input},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if user_input:
            self.protocol = user_input[CONF_PROTOCOL]
            return await self.async_step_protocol()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROTOCOL): vol.In([PROTOCOL_SOCKET, PROTOCOL_SERIAL]),
                }
            ),
        )

    async def async_step_protocol(self, user_input: dict | None = None):
        errors = {}

        if user_input:
            config_data = {CONF_PROTOCOL: self.protocol, **user_input}

            transport = _get_transport_from_config_data(config_data)

            try:
                await models.Gateway.from_transport(transport)
            except (exceptions.CoolMasterNetRemoteError, OSError):
                errors["base"] = "cannot_connect"

            if not errors:
                return self._async_get_entry(user_input)

        if self.protocol == PROTOCOL_SOCKET:
            schema = vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            )
        elif self.protocol == PROTOCOL_SERIAL:
            schema = vol.Schema(
                {
                    vol.Required(CONF_SERIAL_URL): str,
                    vol.Required(CONF_SERIAL_BAUD, default=DEFAULT_BAUD_RATE): int,
                }
            )
        else:
            raise ValueError(f"Unsupported protocol {self.protocol}")

        return self.async_show_form(
            step_id="protocol",
            data_schema=schema,
            errors=errors,
        )
