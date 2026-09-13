"""MeshCore radio hub for Cattle Sprayer Mesh."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONN_BLE, CONN_USB, CONN_WIFI, DOMAIN
from .cs_parse import CsEvent, parse_cs, parse_pairing_blob

_LOGGER = logging.getLogger(__name__)

SIGNAL_SPRAYER = f"{DOMAIN}_sprayer_update"
SIGNAL_NEW_SPRAYER = f"{DOMAIN}_new_sprayer"
SIGNAL_BRIDGE = f"{DOMAIN}_bridge_update"


@dataclass
class SprayerState:
    node_id: str
    name: str
    object: dict[str, Any] = field(default_factory=dict)
    last_seen: datetime | None = None
    last_spray: datetime | None = None
    raw: str | None = None


class MeshHub:
    """Owns the MeshCore companion session (Wi‑Fi / USB / BLE) and sprayer state."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        connection: str,
        pairing_raw: str,
        serial_port: str | None = None,
        baud: int = 115200,
        host: str | None = None,
        tcp_port: int = 5000,
        ble_address: str | None = None,
        ble_pin: str | None = None,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.connection = connection
        self.serial_port = serial_port
        self.baud = baud
        self.host = host
        self.tcp_port = tcp_port
        self.ble_address = (ble_address or "").strip() or None
        self.ble_pin = (ble_pin or "").strip() or None
        self.pairing = parse_pairing_blob(pairing_raw)
        self.channel_idx = int(self.pairing.get("channel_idx") or 1)
        self.sprayers: dict[str, SprayerState] = {}
        self._mc = None
        self._task: asyncio.Task | None = None
        self._cmd_queue: asyncio.Queue[str] = asyncio.Queue()
        self.available = False

    def _set_available(self, value: bool) -> None:
        if self.available == value:
            return
        self.available = value
        async_dispatcher_send(self.hass, f"{SIGNAL_BRIDGE}_{self.entry_id}")

    def device_info_bridge(self) -> dict[str, Any]:
        if self.connection == CONN_WIFI and self.host:
            model = f"MeshCore Wi‑Fi gateway ({self.host})"
        elif self.connection == CONN_BLE:
            model = f"MeshCore BLE gateway ({self.ble_address or 'scan'})"
        elif self.connection == CONN_USB:
            model = "MeshCore USB gateway"
        else:
            model = "MeshCore house gateway"
        return {
            "identifiers": {(DOMAIN, f"bridge_{self.entry_id}")},
            "name": "Cattle Sprayer Mesh bridge",
            "manufacturer": "Sinewerx",
            "model": model,
        }

    def device_info_sprayer(self, node_id: str) -> dict[str, Any]:
        st = self.sprayers.get(node_id)
        name = st.name if st else f"Sprayer {node_id[:8]}"
        return {
            "identifiers": {(DOMAIN, node_id)},
            "name": name,
            "manufacturer": "Sinewerx",
            "model": "Smart Sprayer (MeshCore)",
            "via_device": (DOMAIN, f"bridge_{self.entry_id}"),
        }

    async def async_start(self) -> None:
        _LOGGER.warning(
            "Mesh hub task starting connection=%s serial=%s host=%s:%s ble=%s",
            self.connection,
            self.serial_port,
            self.host,
            self.tcp_port,
            self.ble_address,
        )
        self._task = self.hass.async_create_background_task(
            self._run(),
            name=f"{DOMAIN}_hub_{self.entry_id}",
        )

    async def async_stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._mc is not None:
            try:
                await self._mc.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._mc = None
        self._set_available(False)

    async def async_send_channel(self, text: str) -> None:
        await self._cmd_queue.put(text.strip())

    async def _run(self) -> None:
        from meshcore import EventType, MeshCore

        while True:
            try:
                await self._session(EventType, MeshCore)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Mesh hub session failed; retrying in 10s")
                self._set_available(False)
                await asyncio.sleep(10)

    async def _session(self, EventType, MeshCore) -> None:
        if self.connection == CONN_WIFI:
            if not self.host:
                raise RuntimeError("Wi‑Fi companion host not set")
            _LOGGER.warning(
                "Connecting MeshCore companion via TCP %s:%s",
                self.host,
                self.tcp_port,
            )
            try:
                mc = await asyncio.wait_for(
                    MeshCore.create_tcp(
                        self.host,
                        self.tcp_port,
                        auto_reconnect=True,
                        max_reconnect_attempts=5,
                        debug=True,
                    ),
                    timeout=30,
                )
            except TimeoutError as exc:
                raise RuntimeError(
                    f"Timed out opening MeshCore TCP {self.host}:{self.tcp_port}"
                ) from exc
        elif self.connection == CONN_BLE:
            _LOGGER.warning(
                "Connecting MeshCore companion via BLE %s",
                self.ble_address or "(scan MeshCore-*)",
            )
            try:
                mc = await asyncio.wait_for(
                    MeshCore.create_ble(
                        self.ble_address,
                        pin=self.ble_pin,
                        auto_reconnect=True,
                        max_reconnect_attempts=5,
                        debug=True,
                    ),
                    timeout=45,
                )
            except TimeoutError as exc:
                raise RuntimeError(
                    f"Timed out opening MeshCore BLE {self.ble_address or 'scan'}"
                ) from exc
        else:
            if not self.serial_port:
                raise RuntimeError("USB companion port not set")
            _LOGGER.warning("Connecting MeshCore companion on %s", self.serial_port)
            try:
                mc = await asyncio.wait_for(
                    MeshCore.create_serial(
                        self.serial_port,
                        baudrate=self.baud,
                        auto_reconnect=True,
                        max_reconnect_attempts=5,
                        debug=True,
                    ),
                    timeout=30,
                )
            except TimeoutError as exc:
                raise RuntimeError(
                    f"Timed out opening MeshCore on {self.serial_port}"
                ) from exc
        if mc is None:
            raise RuntimeError("MeshCore companion did not answer")
        self._mc = mc
        p = self.pairing
        res = await mc.commands.set_radio(p["freq"], p["bw"], p["sf"], p["cr"])
        if getattr(res, "type", None) == EventType.ERROR:
            _LOGGER.warning("set_radio rejected: %s", getattr(res, "payload", res))

        secret = bytes.fromhex(p["key"])
        res = await mc.commands.set_channel(self.channel_idx, p["ch"], secret)
        if getattr(res, "type", None) == EventType.ERROR:
            raise RuntimeError(f"set_channel failed: {getattr(res, 'payload', res)}")

        async def on_channel(event):
            try:
                await self._handle_channel_event(event)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("channel handler failed")

        mc.subscribe(EventType.CHANNEL_MSG_RECV, on_channel)
        await mc.start_auto_message_fetching()
        self._set_available(True)
        _LOGGER.warning(
            "Listening for cattle sprayers on channel %s (%s)",
            self.channel_idx,
            p["ch"],
        )

        worker = asyncio.create_task(self._command_worker(EventType))
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            self._set_available(False)
            try:
                await mc.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._mc = None

    async def _command_worker(self, EventType) -> None:
        while True:
            text = await self._cmd_queue.get()
            if not text or self._mc is None:
                continue
            _LOGGER.info("TX channel: %s", text)
            try:
                res = await self._mc.commands.send_chan_msg(self.channel_idx, text)
                if getattr(res, "type", None) == EventType.ERROR:
                    _LOGGER.warning("send_chan_msg failed: %s", res.payload)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("send_chan_msg error")

    async def _handle_channel_event(self, event) -> None:
        payload = event.payload or {}
        text = payload.get("text") or payload.get("message") or ""
        ch = payload.get("channel_idx")
        if ch is not None and int(ch) not in (0, self.channel_idx):
            return
        evt = parse_cs(text)
        if not evt:
            return
        node_id = evt.device_id
        if node_id == "unknown":
            node_id = "legacy"
        is_new = node_id not in self.sprayers
        now = datetime.now(timezone.utc)
        obj = evt.to_object()
        st = self.sprayers.get(node_id) or SprayerState(node_id=node_id, name=evt.display_name)
        st.name = evt.display_name
        # Merge: keep last known tank/spray_count if omitted
        merged = dict(st.object)
        merged.update(obj)
        st.object = merged
        st.last_seen = now
        st.raw = evt.raw
        if evt.type_name == "spray":
            st.last_spray = now
        self.sprayers[node_id] = st
        if is_new:
            async_dispatcher_send(self.hass, f"{SIGNAL_NEW_SPRAYER}_{self.entry_id}", node_id)
        async_dispatcher_send(self.hass, f"{SIGNAL_SPRAYER}_{self.entry_id}", node_id)
        _LOGGER.debug("RX %s", text)
