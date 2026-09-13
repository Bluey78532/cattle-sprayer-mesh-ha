# Sinewerx Mesh — Home Assistant

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bluey78532&repository=sinewerx-mesh-ha&category=integration)
[![Add integration to my Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sinewerx_mesh)

Public Home Assistant integration for the **Sinewerx Mesh house gateway** (Xiao S3 WIO) and field devices on a private MeshCore channel.

## Prefer MQTT when possible

If the gateway **Settings → Home Assistant MQTT** has a broker set, use the built-in **MQTT** integration instead. Use this HACS integration when you do not want MQTT.

## Install

1. HACS → Custom repositories → add `https://github.com/Bluey78532/sinewerx-mesh-ha` as **Integration**.
2. Download **Sinewerx Mesh**, then restart Home Assistant.
3. Settings → Devices & services → Add integration → **Sinewerx Mesh**.
4. Enter the gateway LAN IP (for example `192.168.20.253`) or `sinewerx-gw.local`.

Do **not** connect Home Assistant to companion TCP 5000 / USB / BLE. The gateway owns the radio.

Domain: `sinewerx_mesh`.

## License

MIT
