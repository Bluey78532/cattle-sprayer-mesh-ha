"""Cattle Sprayer Mesh — Home Assistant integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BAUD,
    CONF_BLE_ADDRESS,
    CONF_BLE_PIN,
    CONF_CONNECTION,
    CONF_PAIRING,
    CONF_SERIAL_PORT,
    CONN_USB,
    CONN_WIFI,
    DEFAULT_BAUD,
    DEFAULT_BLE_PIN,
    DEFAULT_TCP_PORT,
    DOMAIN,
)
from .hub import MeshHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data
    connection = data.get(CONF_CONNECTION) or (
        CONN_USB if data.get(CONF_SERIAL_PORT) else CONN_WIFI
    )
    hub = MeshHub(
        hass,
        entry.entry_id,
        connection=connection,
        serial_port=data.get(CONF_SERIAL_PORT),
        baud=int(data.get(CONF_BAUD) or DEFAULT_BAUD),
        host=data.get(CONF_HOST),
        tcp_port=int(data.get(CONF_PORT) or DEFAULT_TCP_PORT),
        ble_address=data.get(CONF_BLE_ADDRESS),
        ble_pin=data.get(CONF_BLE_PIN) or DEFAULT_BLE_PIN,
        pairing_raw=data[CONF_PAIRING],
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    _LOGGER.warning(
        "Cattle Sprayer Mesh starting (%s) entry=%s port=%s host=%s ble=%s",
        connection,
        entry.entry_id,
        data.get(CONF_SERIAL_PORT),
        data.get(CONF_HOST),
        data.get(CONF_BLE_ADDRESS),
    )
    await hub.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hub: MeshHub = hass.data[DOMAIN].pop(entry.entry_id)
    await hub.async_stop()
    return unload_ok
