"""HTTP client hub for the Sinewerx Mesh house gateway."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, POLL_SECONDS, SIGNAL_BRIDGE, SIGNAL_DEVICE, SIGNAL_NEW_DEVICE

_LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceState:
    node_id: str
    kind: str
    name: str
    object: dict[str, Any] = field(default_factory=dict)
    last_seen: datetime | None = None


class GatewayHub:
    """Polls the gateway HTTP API and tracks devices by kind."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        host: str,
        port: int = 80,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.host = host
        self.port = port
        self.base = f"http://{host}:{port}"
        self.devices: dict[str, DeviceState] = {}
        self.available = False
        self.status: dict[str, Any] = {}
        self._task: asyncio.Task | None = None
        self._session: aiohttp.ClientSession | None = None

    def _set_available(self, value: bool) -> None:
        if self.available == value:
            return
        self.available = value
        async_dispatcher_send(self.hass, f"{SIGNAL_BRIDGE}_{self.entry_id}")

    def device_info_bridge(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, f"bridge_{self.entry_id}")},
            "name": "Sinewerx Mesh Gateway",
            "manufacturer": "Sinewerx",
            "model": f"Gateway ({self.host})",
        }

    def device_info_node(self, node_id: str) -> dict[str, Any]:
        st = self.devices.get(node_id)
        name = st.name if st else f"Device {node_id[:8]}"
        kind = st.kind if st else "generic"
        model = {
            "sprayer": "Smart Sprayer (MeshCore)",
            "pump": "Pump Controller",
        }.get(kind, "Mesh Device")
        return {
            "identifiers": {(DOMAIN, node_id)},
            "name": name,
            "manufacturer": "Sinewerx",
            "model": model,
            "via_device": (DOMAIN, f"bridge_{self.entry_id}"),
        }

    async def async_start(self) -> None:
        self._session = async_get_clientsession(self.hass)
        self._task = self.hass.async_create_background_task(
            self._poll_loop(), name=f"{DOMAIN}_poll"
        )

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._set_available(False)

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self._refresh()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Gateway poll failed")
                self._set_available(False)
            await asyncio.sleep(POLL_SECONDS)

    async def _refresh(self) -> None:
        assert self._session is not None
        timeout = aiohttp.ClientTimeout(total=8)
        async with self._session.get(f"{self.base}/api/status", timeout=timeout) as resp:
            resp.raise_for_status()
            self.status = await resp.json(content_type=None)
        async with self._session.get(f"{self.base}/api/devices", timeout=timeout) as resp:
            resp.raise_for_status()
            devices = await resp.json(content_type=None)
        self._set_available(True)
        now = datetime.now(timezone.utc)
        if not isinstance(devices, list):
            return
        for item in devices:
            if not isinstance(item, dict):
                continue
            node_id = str(item.get("id") or "").lower()
            if not node_id:
                continue
            kind = str(item.get("kind") or "generic")
            name = str(item.get("name") or f"{kind} {node_id[:8]}")
            is_new = node_id not in self.devices
            st = self.devices.get(node_id) or DeviceState(node_id=node_id, kind=kind, name=name)
            st.kind = kind
            st.name = name
            st.object = dict(item)
            st.last_seen = now
            self.devices[node_id] = st
            if is_new:
                async_dispatcher_send(
                    self.hass, f"{SIGNAL_NEW_DEVICE}_{self.entry_id}", node_id
                )
            async_dispatcher_send(self.hass, f"{SIGNAL_DEVICE}_{self.entry_id}", node_id)

    async def async_send_command(self, node_id: str, cmd: str, kind: str | None = None) -> None:
        assert self._session is not None
        st = self.devices.get(node_id)
        body = {"cmd": cmd}
        if kind or (st and st.kind):
            body["kind"] = kind or st.kind  # type: ignore[assignment]
        url = f"{self.base}/api/devices/{node_id}/command"
        timeout = aiohttp.ClientTimeout(total=10)
        async with self._session.post(url, json=body, timeout=timeout) as resp:
            resp.raise_for_status()
