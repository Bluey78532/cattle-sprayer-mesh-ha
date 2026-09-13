"""Parse Cattle Sprayer MeshCore channel text (`CS …`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

TYPE_NAMES = {
    "hb": "heartbeat",
    "heartbeat": "heartbeat",
    "spray": "spray",
    "lvc": "lvc_park",
    "fault": "fault",
    "block": "spray_block",
    "evt": "event",
    "mix": "mix",
}

BLOCK_NAMES = {
    0: "none",
    1: "tank",
    2: "lux",
    3: "lvc",
    4: "rate",
    5: "crash",
    6: "stuck",
    7: "night",
}

FAULT_BITS = (
    (1 << 0, "i2c_mcp"),
    (1 << 1, "i2c_ads"),
    (1 << 2, "i2c_bh1750"),
    (1 << 3, "sensor_stuck"),
    (1 << 4, "spray_abort"),
    (1 << 5, "boot_loop"),
    (1 << 6, "lux_absent"),
)

_KV = re.compile(r"([A-Za-z_]+)=(\S+)")


@dataclass
class CsEvent:
    raw: str
    type_tag: str
    type_name: str
    name: str | None
    node_id: str | None
    vbat_mv: int | None
    lux: int | None
    uptime_s: int | None
    flags: int
    tank_low: bool | None
    spray_count: int | None

    @property
    def device_id(self) -> str:
        if self.node_id:
            return self.node_id.lower()
        if self.name:
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", self.name).strip("_").lower()
            return slug or "unknown"
        return "unknown"

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name.replace("_", " ")
        if self.node_id:
            return f"Sprayer {self.node_id[:8]}"
        return "Cattle Sprayer"

    def faults(self) -> dict[str, bool]:
        return {name: bool(self.flags & bit) for bit, name in FAULT_BITS}

    def block_name(self) -> str | None:
        if self.type_name != "spray_block":
            return None
        return BLOCK_NAMES.get(self.flags & 0x0F, "unknown")

    def to_object(self) -> dict[str, Any]:
        obj: dict[str, Any] = {
            "type_name": self.type_name,
            "type_tag": self.type_tag,
            "flags": self.flags,
            "faults": self.faults(),
            "node_id": self.node_id,
            "node_name": self.name,
        }
        if self.vbat_mv is not None:
            obj["vbat_mv"] = self.vbat_mv
            obj["vbat_v"] = round(self.vbat_mv / 1000.0, 3)
        if self.lux is not None:
            obj["lux"] = self.lux
        if self.uptime_s is not None:
            obj["uptime_s"] = self.uptime_s
        if self.tank_low is not None:
            obj["tank_low"] = bool(self.tank_low)
        if self.spray_count is not None:
            obj["spray_count"] = self.spray_count
        block = self.block_name()
        if block is not None:
            obj["block_name"] = block
        any_fault = any(self.faults().values())
        obj["fault"] = any_fault or self.type_name == "fault"
        obj["lvc_park"] = self.type_name == "lvc_park"
        obj["problem"] = bool(
            obj["fault"]
            or obj.get("tank_low")
            or obj["lvc_park"]
            or self.type_name == "spray_block"
        )
        return obj


def parse_cs(text: str) -> CsEvent | None:
    if not text:
        return None
    line = text.strip()
    if not line.upper().startswith("CS "):
        return None
    body = line[3:].strip()
    if not body:
        return None

    parts = body.split()
    type_tag = parts[0].lower()
    kv: dict[str, str] = {}
    for token in parts[1:]:
        m = _KV.fullmatch(token)
        if m:
            kv[m.group(1).lower()] = m.group(2)

    def as_int(key: str) -> int | None:
        raw = kv.get(key)
        if raw is None:
            return None
        try:
            return int(raw, 0)
        except ValueError:
            return None

    flags_raw = kv.get("f", "0")
    try:
        flags = int(flags_raw, 16) if re.fullmatch(r"[0-9A-Fa-f]+", flags_raw) else int(flags_raw)
    except ValueError:
        flags = 0

    node_id = kv.get("id")
    if node_id:
        node_id = re.sub(r"[^0-9A-Fa-f]", "", node_id).lower()
        if len(node_id) < 4:
            node_id = None
        else:
            node_id = node_id[:16]

    tank = as_int("tk")
    return CsEvent(
        raw=line,
        type_tag=type_tag,
        type_name=TYPE_NAMES.get(type_tag, "event"),
        name=kv.get("n"),
        node_id=node_id,
        vbat_mv=as_int("vb"),
        lux=as_int("lx"),
        uptime_s=as_int("up"),
        flags=flags & 0xFF,
        tank_low=None if tank is None else bool(tank),
        spray_count=as_int("sc"),
    )


def parse_pairing_blob(raw: str) -> dict[str, Any]:
    import json

    text = (raw or "").strip()
    if not text:
        raise ValueError("pairing card is empty")
    if text.startswith("{"):
        data = json.loads(text)
    else:
        data = {"key": text, "ch": "Sprayer", "freq": 915.8, "bw": 250, "sf": 10, "cr": 5}

    key = re.sub(r"[^0-9A-Fa-f]", "", str(data.get("key", "")))
    if len(key) != 32:
        raise ValueError("pairing card needs a 32-hex channel secret")
    ch = str(data.get("ch") or data.get("channel") or "Sprayer")[:32]
    freq = float(data.get("freq") or data.get("freq_mhz") or 915.8)
    bw = float(data.get("bw") or data.get("bw_khz") or 250)
    sf = int(data.get("sf") or 10)
    cr = int(data.get("cr") or 5)
    return {
        "v": int(data.get("v") or 1),
        "kind": data.get("kind") or "cattle-sprayer-mesh",
        "ch": ch,
        "key": key.lower(),
        "freq": freq,
        "bw": bw,
        "sf": sf,
        "cr": cr,
        "channel_idx": int(data.get("channel_idx") or data.get("idx") or 1),
    }
