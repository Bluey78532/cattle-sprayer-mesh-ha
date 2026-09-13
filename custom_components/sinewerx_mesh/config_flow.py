"""Config flow for Sinewerx Mesh gateway (HTTP / zeroconf)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
try:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:  # pragma: no cover - older HA
    from homeassistant.components.zeroconf import ZeroconfServiceInfo  # type: ignore

from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _probe(hass, host: str, port: int) -> str | None:
    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}/api/status"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status != 200:
                return "cannot_connect"
            data = await resp.json(content_type=None)
            if not isinstance(data, dict):
                return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Probe failed for %s:%s", host, port, exc_info=True)
        return "cannot_connect"
    return None


class SinewerxMeshConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up Sinewerx Mesh via manual host or mDNS."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input.get(CONF_PORT) or DEFAULT_PORT)
            err = await _probe(self.hass, host, port)
            if err:
                errors["base"] = err
            else:
                await self.async_set_unique_id(f"swx_gw_{host}_{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Sinewerx Gateway ({host})",
                    data={CONF_HOST: host, CONF_PORT: port},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        self._host = discovery_info.host
        self._port = int(discovery_info.port or DEFAULT_PORT)
        await self.async_set_unique_id(f"swx_gw_{self._host}_{self._port}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
        err = await _probe(self.hass, self._host, self._port)
        if err:
            return self.async_abort(reason="cannot_connect")
        self.context["title_placeholders"] = {"name": self._host}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=f"Sinewerx Gateway ({self._host})",
                data={CONF_HOST: self._host, CONF_PORT: self._port},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"host": self._host or ""},
        )
