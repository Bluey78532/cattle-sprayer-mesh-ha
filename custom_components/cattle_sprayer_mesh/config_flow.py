"""Config flow for Cattle Sprayer Mesh."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BAUD,
    CONF_PAIRING,
    CONF_SERIAL_PORT,
    DEFAULT_BAUD,
    DOMAIN,
)
from .cs_parse import parse_pairing_blob

_LOGGER = logging.getLogger(__name__)


def _list_ports() -> list[str]:
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    return [p.device for p in list_ports.comports()]


class CattleSprayerMeshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up with USB port + SoftAP pairing card."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        ports = await self.hass.async_add_executor_job(_list_ports)

        if user_input is not None:
            try:
                pairing = parse_pairing_blob(user_input[CONF_PAIRING])
            except Exception:  # noqa: BLE001
                errors["base"] = "invalid_pairing"
            else:
                port = user_input[CONF_SERIAL_PORT].strip()
                await self.async_set_unique_id(f"cs_mesh_{port}")
                self._abort_if_unique_id_configured()
                title = pairing.get("ch") or "Cattle Sprayer Mesh"
                return self.async_create_entry(
                    title=f"Cattle Sprayer Mesh ({title})",
                    data={
                        CONF_SERIAL_PORT: port,
                        CONF_BAUD: int(user_input.get(CONF_BAUD) or DEFAULT_BAUD),
                        CONF_PAIRING: user_input[CONF_PAIRING].strip(),
                        CONF_NAME: title,
                    },
                )

        port_default = ports[0] if ports else ""
        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT, default=port_default): str,
                vol.Required(CONF_PAIRING, default=""): str,
                vol.Optional(CONF_BAUD, default=DEFAULT_BAUD): int,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "ports": ", ".join(ports) if ports else "none found — type the port manually",
            },
        )
