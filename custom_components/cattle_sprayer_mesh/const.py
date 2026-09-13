"""Constants for Cattle Sprayer Mesh."""

from __future__ import annotations

DOMAIN = "cattle_sprayer_mesh"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUD = "baud"
CONF_PAIRING = "pairing"
CONF_CHANNEL_IDX = "channel_idx"

DEFAULT_BAUD = 115200
DEFAULT_CHANNEL_IDX = 1

# Stale after ~3 h (matches ~1 h heartbeat with margin)
STALE_SECONDS = 10800

ATTR_NODE_ID = "node_id"
ATTR_RAW = "raw"
