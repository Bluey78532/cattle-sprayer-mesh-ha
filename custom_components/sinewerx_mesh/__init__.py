"""Sinewerx Mesh — Home Assistant integration (HTTP to house gateway)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PORT, DOMAIN
from .hub import GatewayHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = GatewayHub(
        hass,
        entry.entry_id,
        host=entry.data[CONF_HOST],
        port=int(entry.data.get(CONF_PORT) or DEFAULT_PORT),
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    _LOGGER.info(
        "Sinewerx Mesh starting host=%s port=%s",
        entry.data.get(CONF_HOST),
        entry.data.get(CONF_PORT),
    )
    await hub.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hub: GatewayHub = hass.data[DOMAIN].pop(entry.entry_id)
    await hub.async_stop()
    return unload_ok
