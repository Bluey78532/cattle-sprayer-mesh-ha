"""Constants for Cattle Sprayer Mesh."""

from __future__ import annotations

DOMAIN = "cattle_sprayer_mesh"

CONF_CONNECTION = "connection"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUD = "baud"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_BLE_ADDRESS = "ble_address"
CONF_BLE_PIN = "ble_pin"
CONF_PAIRING = "pairing"
CONF_CHANNEL_IDX = "channel_idx"

CONN_WIFI = "wifi"
CONN_USB = "usb"
CONN_BLE = "ble"

DEFAULT_BAUD = 115200
DEFAULT_TCP_PORT = 5000
DEFAULT_BLE_PIN = "123456"
DEFAULT_CHANNEL_IDX = 1

# Stale after ~3 h (matches ~1 h heartbeat with margin)
STALE_SECONDS = 10800

ATTR_NODE_ID = "node_id"
ATTR_RAW = "raw"
