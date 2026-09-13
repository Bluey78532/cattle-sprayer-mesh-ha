"""Constants for Sinewerx Mesh gateway integration."""

from __future__ import annotations

DOMAIN = "sinewerx_mesh"

CONF_HOST = "host"
CONF_PORT = "port"

DEFAULT_PORT = 80
STALE_SECONDS = 10800
POLL_SECONDS = 15

SIGNAL_DEVICE = f"{DOMAIN}_device_update"
SIGNAL_NEW_DEVICE = f"{DOMAIN}_new_device"
SIGNAL_BRIDGE = f"{DOMAIN}_bridge_update"
