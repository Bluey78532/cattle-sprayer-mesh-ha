"""Buttons for Sinewerx Mesh devices."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_DEVICE
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


def _entities_for(hub: GatewayHub, node_id: str) -> list[ButtonEntity]:
    st = hub.devices.get(node_id)
    kind = st.kind if st else "generic"
    ents: list[ButtonEntity] = [
        SwxCmdButton(hub, node_id, "hb", "Request heartbeat", "mdi:heart-pulse", True),
        SwxCmdButton(
            hub, node_id, "reboot", "Restart", "mdi:restart", True, ButtonDeviceClass.RESTART
        ),
    ]
    if kind == "pump":
        ents.extend(
            [
                SwxCmdButton(hub, node_id, "start", "Start", "mdi:play", False),
                SwxCmdButton(hub, node_id, "stop", "Stop", "mdi:stop", False),
            ]
        )
    return ents


class SwxCmdButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        hub: GatewayHub,
        node_id: str,
        cmd: str,
        name: str,
        icon: str,
        diagnostic: bool,
        device_class: ButtonDeviceClass | None = None,
    ) -> None:
        self.hub = hub
        self.node_id = node_id
        self._cmd = cmd
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{hub.entry_id}_{node_id}_{cmd}"
        self._attr_device_info = hub.device_info_node(node_id)
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if device_class:
            self._attr_device_class = device_class

    async def async_press(self) -> None:
        await self.hub.async_send_command(self.node_id, self._cmd)
