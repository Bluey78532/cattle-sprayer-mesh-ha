# Sinewerx Mesh — Home Assistant

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bluey78532&repository=cattle-sprayer-mesh-ha&category=integration)
[![Add integration to my Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sinewerx_mesh)

Public Home Assistant integration for the **Sinewerx Mesh house gateway** (Xiao S3 WIO) and field devices (sprayers, pumps, …) on a private MeshCore channel.

Firmware and product docs stay in the private product repo. This repository is the HACS-installable integration only.

## Prefer MQTT when possible

If the gateway **Settings → Home Assistant MQTT** has a broker set, Home Assistant only needs the built-in **MQTT** integration — no custom component. Use this HACS integration when you do **not** want MQTT.

## Install (HTTP / mDNS)

1. HACS → Custom repositories → add `https://github.com/Bluey78532/cattle-sprayer-mesh-ha` as **Integration** (or use the badge above).
2. Download **Sinewerx Mesh**, restart Home Assistant.
3. **Settings → Devices & services → Add integration → Sinewerx Mesh** (or accept zeroconf `_swx-gw._tcp`).
4. Enter the gateway LAN IP (e.g. `192.168.20.253`) or `sinewerx-gw.local`.

Do **not** also connect Home Assistant to the gateway companion TCP **5000** / USB / BLE — the gateway owns the radio.

Domain: `sinewerx_mesh`.

## Legacy

**Cattle Sprayer Mesh** (`cattle_sprayer_mesh`) — companion TCP/USB into HA — is deprecated. Remove it and use MQTT or **Sinewerx Mesh** instead.

## License

MIT — see product branding; integration code may be used with Sinewerx devices.
