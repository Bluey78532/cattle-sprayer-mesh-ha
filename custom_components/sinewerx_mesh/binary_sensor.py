"""Binary sensors for Sinewerx Mesh devices."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_BRIDGE, SIGNAL_DEVICE, SIGNAL_NEW_DEVICE, STALE_SECONDS
from .hub import GatewayHub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: GatewayHub = hass.data[DOMAIN][entry.entry_id]

    @callback
    def _new(node_id: str) -> None:
        async_add_entities(_entities_for(hub, node_id))

    entry.async_on_unload(
        async_dispatcher_connect(hass, f"{SIGNAL_NEW_DEVICE}_{entry.entry_id}", _new)
    )
    for node_id in list(hub.devices):
        async_add_entities(_entities_for(hub, node_id))

    async_add_entities([GwConnected(hub)])


def _entities_for(hub: GatewayHub, node_id: str) -> list[BinarySensorEntity]:
    st = hub.devices.get(node_id)
    kind = st.kind if st else "generic"
    ents: list[BinarySensorEntity] = [SwxProblem(hub, node_id)]
    if kind == "sprayer":
        ents.extend([SwxTank(hub, node_id), SwxFault(hub, node_id)])
    elif kind == "pump":
        ents.append(SwxRunning(hub, node_id))
    return ents


class _SwxBin(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: GatewayHub, node_id: str, key: str) -> None:
        self.hub = hub
        self.node_id = node_id
        self._attr_unique_id = f"{hub.entry_id}_{node_id}_{key}"
        self._attr_device_info = hub.device_info_node(node_id)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_DEVICE}_{self.hub.entry_id}", self._handle
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_BRIDGE}_{self.hub.entry_id}", self._handle_bridge
            )
        )

    @callback
    def _handle(self, node_id: str) -> None:
        if node_id == self.node_id:
            self.async_write_ha_state()

    @callback
    def _handle_bridge(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        if not self.hub.available:
            return False
        st = self.hub.devices.get(self.node_id)
        if not st or not st.last_seen:
            return False
        age = (datetime.now(timezone.utc) - st.last_seen).total_seconds()
        return age < STALE_SECONDS

    def _obj(self) -> dict:
        st = self.hub.devices.get(self.node_id)
        return st.object if st else {}


class GwConnected(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_should_poll = False

    def __init__(self, hub: GatewayHub) -> None:
        self.hub = hub
        self._attr_unique_id = f"{hub.entry_id}_bridge_connected"
        self._attr_device_info = hub.device_info_bridge()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{SIGNAL_BRIDGE}_{self.hub.entry_id}", self._handle
            )
        )

    @callback
    def _handle(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self.hub.available


class SwxProblem(_SwxBin):
    _attr_name = "Problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "problem")

    @property
    def is_on(self) -> bool:
        return bool(self._obj().get("problem"))


class SwxTank(_SwxBin):
    _attr_name = "Tank low"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:barrel"

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "tank")

    @property
    def is_on(self) -> bool:
        return bool(self._obj().get("tank_low"))


class SwxFault(_SwxBin):
    _attr_name = "Fault"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "fault")

    @property
    def is_on(self) -> bool:
        return bool(self._obj().get("fault"))


class SwxRunning(_SwxBin):
    _attr_name = "Running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "running")

    @property
    def is_on(self) -> bool:
        return bool(self._obj().get("running"))
