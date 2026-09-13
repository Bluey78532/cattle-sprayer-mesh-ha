"""Sensors for Cattle Sprayer Mesh."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, STALE_SECONDS
from .hub import MeshHub, SIGNAL_NEW_SPRAYER, SIGNAL_SPRAYER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: MeshHub = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    def _entities_for(node_id: str) -> list[SensorEntity]:
        return [
            SprayerVoltageSensor(hub, node_id),
            SprayerBatteryPctSensor(hub, node_id),
            SprayerLuxSensor(hub, node_id),
            SprayerEventSensor(hub, node_id),
            SprayerBlockSensor(hub, node_id),
            SprayerLastSeenSensor(hub, node_id),
            SprayerLastSpraySensor(hub, node_id),
            SprayerCountSensor(hub, node_id),
            SprayerUptimeSensor(hub, node_id),
        ]

    @callback
    def _add_node(node_id: str) -> None:
        if node_id in known:
            return
        known.add(node_id)
        async_add_entities(_entities_for(node_id))

    for nid in list(hub.sprayers):
        _add_node(nid)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{SIGNAL_NEW_SPRAYER}_{entry.entry_id}", _add_node
        )
    )


class SprayerSensorBase(SensorEntity):
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

    def _obj(self) -> dict[str, Any]:
        st = self._hub.sprayers.get(self._node_id)
        return st.object if st else {}


class SprayerVoltageSensor(SprayerSensorBase):
    _attr_name = "Battery"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 2

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "battery")

    @property
    def native_value(self) -> StateType:
        return self._obj().get("vbat_v")


class SprayerBatteryPctSensor(SprayerSensorBase):
    _attr_name = "Battery percent"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "battery_pct")

    @property
    def native_value(self) -> StateType:
        v = self._obj().get("vbat_v")
        if v is None:
            return None
        # Rough 12 V lead-acid style map for HomeKit/Google
        pct = (float(v) - 11.5) / (13.0 - 11.5) * 100.0
        return max(0, min(100, round(pct)))


class SprayerLuxSensor(SprayerSensorBase):
    _attr_name = "Light"
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "lx"

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "lux")

    @property
    def native_value(self) -> StateType:
        return self._obj().get("lux")


class SprayerEventSensor(SprayerSensorBase):
    _attr_name = "Last event"
    _attr_icon = "mdi:cow"

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "event")

    @property
    def native_value(self) -> StateType:
        return self._obj().get("type_name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        st = self._hub.sprayers.get(self._node_id)
        attrs = dict(self._obj())
        if st and st.raw:
            attrs["raw"] = st.raw
        return attrs


class SprayerBlockSensor(SprayerSensorBase):
    _attr_name = "Block reason"
    _attr_icon = "mdi:cancel"

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "block")

    @property
    def native_value(self) -> StateType:
        obj = self._obj()
        if obj.get("type_name") == "spray_block":
            return obj.get("block_name") or "unknown"
        if obj.get("type_name"):
            return "none"
        return None


class SprayerLastSeenSensor(SprayerSensorBase):
    _attr_name = "Last seen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "last_seen")

    @property
    def available(self) -> bool:
        return self._node_id in self._hub.sprayers

    @property
    def native_value(self) -> datetime | None:
        st = self._hub.sprayers.get(self._node_id)
        return st.last_seen if st else None


class SprayerLastSpraySensor(SprayerSensorBase):
    _attr_name = "Last spray"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:sprinkler"

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "last_spray")

    @property
    def available(self) -> bool:
        st = self._hub.sprayers.get(self._node_id)
        return bool(st and st.last_spray)

    @property
    def native_value(self) -> datetime | None:
        st = self._hub.sprayers.get(self._node_id)
        return st.last_spray if st else None


class SprayerCountSensor(SprayerSensorBase):
    _attr_name = "Spray count"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:counter"

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "sprays")

    @property
    def native_value(self) -> StateType:
        return self._obj().get("spray_count")


class SprayerUptimeSensor(SprayerSensorBase):
    _attr_name = "Uptime"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "uptime")

    @property
    def native_value(self) -> StateType:
        return self._obj().get("uptime_s")
