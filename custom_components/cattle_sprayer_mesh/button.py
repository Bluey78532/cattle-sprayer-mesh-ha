"""Buttons for Cattle Sprayer Mesh."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import MeshHub, SIGNAL_NEW_SPRAYER, SIGNAL_SPRAYER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub: MeshHub = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    def _entities_for(node_id: str) -> list[ButtonEntity]:
        return [
            SprayerHeartbeatButton(hub, node_id),
            SprayerRebootButton(hub, node_id),
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


class SprayerButtonBase(ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub: MeshHub, node_id: str, key: str) -> None:
        self._hub = hub
        self._node_id = node_id
        self._attr_unique_id = f"{DOMAIN}_{node_id}_{key}"
        self._attr_device_info = hub.device_info_sprayer(node_id)

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


class SprayerHeartbeatButton(SprayerButtonBase):
    _attr_name = "Request heartbeat"
    _attr_icon = "mdi:heart-pulse"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "heartbeat")

    async def async_press(self) -> None:
        await self._hub.async_send_channel("hb")


class SprayerRebootButton(SprayerButtonBase):
    _attr_name = "Restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hub: MeshHub, node_id: str) -> None:
        super().__init__(hub, node_id, "reboot")

    async def async_press(self) -> None:
        await self._hub.async_send_channel("reboot")
