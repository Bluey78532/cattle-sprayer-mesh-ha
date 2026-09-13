"""Cattle Sprayer Mesh — Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_BAUD, CONF_PAIRING, CONF_SERIAL_PORT, DEFAULT_BAUD, DOMAIN
from .hub import MeshHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = MeshHub(
        hass,
        entry.entry_id,
        serial_port=entry.data[CONF_SERIAL_PORT],
        baud=int(entry.data.get(CONF_BAUD) or DEFAULT_BAUD),
        pairing_raw=entry.data[CONF_PAIRING],
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    await hub.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hub: MeshHub = hass.data[DOMAIN].pop(entry.entry_id)
    await hub.async_stop()
    return unload_ok
