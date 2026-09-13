"""Sensors for Sinewerx Mesh devices."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential, UnitOfIlluminance, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
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


def _entities_for(hub: GatewayHub, node_id: str) -> list[SensorEntity]:
    st = hub.devices.get(node_id)
    kind = st.kind if st else "generic"
    ents: list[SensorEntity] = [
        SwxBattery(hub, node_id),
        SwxEvent(hub, node_id),
        SwxLastSeen(hub, node_id),
    ]
    if kind == "sprayer":
        ents.extend(
            [
                SwxLux(hub, node_id),
                SwxSprays(hub, node_id),
                SwxUptime(hub, node_id),
            ]
        )
    elif kind == "pump":
        ents.append(SwxPsi(hub, node_id))
        ents.append(SwxFlow(hub, node_id))
    return ents


class _SwxSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: GatewayHub, node_id: str, key: str) -> None:
        self.hub = hub
        self.node_id = node_id
        self._key = key
        self._attr_unique_id = f"{hub.entry_id}_{node_id}_{key}"
        self._attr_device_info = hub.device_info_node(node_id)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_DEVICE}_{self.hub.entry_id}",
                self._handle,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_BRIDGE}_{self.hub.entry_id}",
                self._handle_bridge,
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
        from datetime import datetime, timezone

        age = (datetime.now(timezone.utc) - st.last_seen).total_seconds()
        return age < STALE_SECONDS

    def _obj(self) -> dict:
        st = self.hub.devices.get(self.node_id)
        return st.object if st else {}


class SwxBattery(_SwxSensor):
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 2

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "battery")

    @property
    def native_value(self):
        return self._obj().get("vbat_v")


class SwxLux(_SwxSensor):
    _attr_name = "Light"
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfIlluminance.LUX

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "lux")

    @property
    def native_value(self):
        return self._obj().get("lux")


class SwxSprays(_SwxSensor):
    _attr_name = "Spray count"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "sprays")

    @property
    def native_value(self):
        return self._obj().get("spray_count")


class SwxUptime(_SwxSensor):
    _attr_name = "Uptime"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "uptime")

    @property
    def native_value(self):
        return self._obj().get("uptime_s")


class SwxEvent(_SwxSensor):
    _attr_name = "Last event"
    _attr_icon = "mdi:cow"

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "event")

    @property
    def native_value(self):
        return self._obj().get("event")

    @property
    def extra_state_attributes(self):
        return self._obj()


class SwxLastSeen(_SwxSensor):
    _attr_name = "Last seen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "last_seen")

    @property
    def native_value(self):
        st = self.hub.devices.get(self.node_id)
        return st.last_seen if st else None


class SwxPsi(_SwxSensor):
    _attr_name = "Pressure"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "psi"
    _attr_icon = "mdi:gauge"

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "psi")

    @property
    def native_value(self):
        return self._obj().get("psi")


class SwxFlow(_SwxSensor):
    _attr_name = "Flow"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water-pump"

    def __init__(self, hub: GatewayHub, node_id: str) -> None:
        super().__init__(hub, node_id, "flow")

    @property
    def native_value(self):
        return self._obj().get("flow")
