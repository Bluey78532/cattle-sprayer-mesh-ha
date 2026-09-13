"""Binary sensors for Cattle Sprayer Mesh."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STALE_SECONDS
from .hub import MeshHub, SIGNAL_BRIDGE, SIGNAL_NEW_SPRAYER, SIGNAL_SPRAYER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: MeshHub = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    def _entities_for(node_id: str) -> list[BinarySensorEntity]:
        return [
            SprayerFaultBinary(hub, node_id),
            SprayerTankBinary(hub, node_id),
            SprayerLvcBinary(hub, node_id),
            SprayerProblemBinary(hub, node_id),
        ]

    @callback
    def _add_node(node_id: str) -> None:
        if node_id in known:
            return
        known.add(node_id)
        async_add_entities(_entities_for(node_id))

    async_add_entities([BridgeConnectedBinary(hub)])

    for nid in list(hub.sprayers):
        _add_node(nid)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{SIGNAL_NEW_SPRAYER}_{entry.entry_id}", _add_node
        )
    )


class BridgeConnectedBinary(BinarySensorEntity):
    """Shows whether the house MeshCore companion is connected."""

    _attr_has_entity_name = True
    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = False

    def __init__(self, hub: MeshHub) -> None:
        self._hub = hub
        self._attr_unique_id = f"{DOMAIN}_{hub.entry_id}_bridge_connected"
        self._attr_device_info = hub.device_info_bridge()

    @property
    def is_on(self) -> bool:
        return bool(self._hub.available)

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated() -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_BRIDGE}_{self._hub.entry_id}",
                _updated,
            )
        )


class SprayerBinaryBase(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: MeshHub, node_id: str, key: str) -> None:
        self._hub = hub
        self._node_id = node_id
        self._attr_unique_id = f"{DOMAIN}_{node_id}_{key}"
        self._attr_device_info = hub.device_info_sprayer(node_id)

    @property
    def available(self) -> bool:
        st = self._hub.sprayers.get(self._node_id)
        if not st or not st.last_seen:
            return False
        age = (datetime.now(st.last_seen.tzinfo) - st.last_seen).total_seconds()
        return age < STALE_SECONDS

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(node_id: str) -> None:
            if node_id == self._node_id:
                self._attr_device_info = self._hub.device_info_sprayer(node_id)
                self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_SPRAYER}_{self._hub.entry_id}",
                _updated,
            )
        )


class SprayerFaultBinary(SprayerBinaryBase):
    _attr_name = "Fault"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "fault")

    @property
    def is_on(self) -> bool | None:
        st = self._hub.sprayers.get(self._node_id)
        if not st:
            return None
        return bool(st.object.get("fault"))


class SprayerTankBinary(SprayerBinaryBase):
    _attr_name = "Tank low"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:barrel"

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "tank")

    @property
    def is_on(self) -> bool | None:
        st = self._hub.sprayers.get(self._node_id)
        if not st or "tank_low" not in st.object:
            return None
        return bool(st.object.get("tank_low"))


class SprayerLvcBinary(SprayerBinaryBase):
    _attr_name = "Low-voltage park"
    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "lvc_park")

    @property
    def is_on(self) -> bool | None:
        st = self._hub.sprayers.get(self._node_id)
        if not st:
            return None
        return bool(st.object.get("lvc_park"))


class SprayerProblemBinary(SprayerBinaryBase):
    _attr_name = "Problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "problem")

    @property
    def is_on(self) -> bool | None:
        st = self._hub.sprayers.get(self._node_id)
        if not st:
            return None
        return bool(st.object.get("problem"))
