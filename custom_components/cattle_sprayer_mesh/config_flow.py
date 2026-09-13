"""Config flow for Cattle Sprayer Mesh."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BAUD,
    CONF_CONNECTION,
    CONF_PAIRING,
    CONF_SERIAL_PORT,
    CONN_USB,
    CONN_WIFI,
    DEFAULT_BAUD,
    DEFAULT_TCP_PORT,
    DOMAIN,
)
from .cs_parse import parse_pairing_blob

_LOGGER = logging.getLogger(__name__)


def _list_ports() -> list[str]:
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    found: list[str] = []
    for p in list_ports.comports():
        # Prefer stable by-id style paths when pyserial exposes them via device
        if p.device:
            found.append(p.device)
    # De-dupe preserving order
    out: list[str] = []
    for d in found:
        if d not in out:
            out.append(d)
    return out


async def _probe_serial(port: str, baud: int) -> str | None:
    """Return None on success, or an error key."""
    try:
        from meshcore import MeshCore
    except Exception:  # noqa: BLE001
        _LOGGER.exception("meshcore import failed")
        return "cannot_connect"

    mc = None
    try:
        mc = await asyncio.wait_for(
            MeshCore.create_serial(port, baudrate=baud, debug=True),
            timeout=25,
        )
    except TimeoutError:
        _LOGGER.error("Timed out opening MeshCore on %s", port)
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed opening MeshCore on %s", port)
        return "cannot_connect"

    if mc is None:
        _LOGGER.error(
            "MeshCore did not answer on %s — use Companion USB firmware, not Bluetooth",
            port,
        )
        return "cannot_connect"

    try:
        await mc.disconnect()
    except Exception:  # noqa: BLE001
        pass
    return None


async def _probe_tcp(host: str, port: int) -> str | None:
    try:
        from meshcore import MeshCore
    except Exception:  # noqa: BLE001
        _LOGGER.exception("meshcore import failed")
        return "cannot_connect"

    mc = None
    try:
        mc = await asyncio.wait_for(
            MeshCore.create_tcp(host, port, debug=True),
            timeout=25,
        )
    except TimeoutError:
        _LOGGER.error("Timed out opening MeshCore TCP %s:%s", host, port)
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed opening MeshCore TCP %s:%s", host, port)
        return "cannot_connect"

    if mc is None:
        return "cannot_connect"

    try:
        await mc.disconnect()
    except Exception:  # noqa: BLE001
        pass
    return None


class CattleSprayerMeshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Wi‑Fi (TCP) or USB companion + SoftAP pairing card."""

    VERSION = 2

    def __init__(self) -> None:
        self._connection: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._connection = user_input[CONF_CONNECTION]
            if self._connection == CONN_WIFI:
                return await self.async_step_wifi()
            return await self.async_step_usb()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONNECTION, default=CONN_WIFI): vol.In(
                        {
                            CONN_WIFI: "Wi‑Fi gateway (recommended — radio can be far from HA)",
                            CONN_USB: "USB companion plugged into Home Assistant",
                        }
                    ),
                }
            ),
        )

    async def async_step_wifi(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                pairing = parse_pairing_blob(user_input[CONF_PAIRING])
            except Exception:  # noqa: BLE001
                errors["base"] = "invalid_pairing"
            else:
                host = user_input[CONF_HOST].strip()
                port = int(user_input.get(CONF_PORT) or DEFAULT_TCP_PORT)
                err = await _probe_tcp(host, port)
                if err:
                    errors["base"] = err
                else:
                    await self.async_set_unique_id(f"cs_mesh_tcp_{host}_{port}")
                    self._abort_if_unique_id_configured()
                    title = pairing.get("ch") or "Cattle Sprayer Mesh"
                    return self.async_create_entry(
                        title=f"Cattle Sprayer Mesh ({title} @ {host})",
                        data={
                            CONF_CONNECTION: CONN_WIFI,
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_PAIRING: user_input[CONF_PAIRING].strip(),
                            CONF_NAME: title,
                        },
                    )

        return self.async_show_form(
            step_id="wifi",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=""): str,
                    vol.Required(CONF_PORT, default=DEFAULT_TCP_PORT): int,
                    vol.Required(CONF_PAIRING, default=""): str,
                }
            ),
            errors=errors,
        )

    async def async_step_usb(
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
                baud = int(user_input.get(CONF_BAUD) or DEFAULT_BAUD)
                err = await _probe_serial(port, baud)
                if err:
                    errors["base"] = err
                else:
                    await self.async_set_unique_id(f"cs_mesh_{port}")
                    self._abort_if_unique_id_configured()
                    title = pairing.get("ch") or "Cattle Sprayer Mesh"
                    return self.async_create_entry(
                        title=f"Cattle Sprayer Mesh ({title})",
                        data={
                            CONF_CONNECTION: CONN_USB,
                            CONF_SERIAL_PORT: port,
                            CONF_BAUD: baud,
                            CONF_PAIRING: user_input[CONF_PAIRING].strip(),
                            CONF_NAME: title,
                        },
                    )

        port_default = ports[0] if ports else ""
        return self.async_show_form(
            step_id="usb",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SERIAL_PORT, default=port_default): str,
                    vol.Required(CONF_PAIRING, default=""): str,
                    vol.Optional(CONF_BAUD, default=DEFAULT_BAUD): int,
                }
            ),
            errors=errors,
            description_placeholders={
                "ports": ", ".join(ports) if ports else "none found — type the path from Hardware → ⓘ",
            },
        )
