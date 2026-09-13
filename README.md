# Cattle Sprayer Mesh — Home Assistant

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bluey78532&repository=cattle-sprayer-mesh-ha&category=integration)
[![Add integration to my Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=cattle_sprayer_mesh)

Public Home Assistant integration for **Sinewerx Automatic Cattle Sprayer** units on a private MeshCore channel.

Firmware and product docs stay in the private product repo. This repository is only the HACS-installable integration.

## Install

1. HACS → Custom repositories → add `https://github.com/Bluey78532/cattle-sprayer-mesh-ha` as **Integration** (or use the badge above).
2. Download **Cattle Sprayer Mesh**, restart Home Assistant.
3. Plug a MeshCore USB companion into the HA box.
4. SoftAP on a sprayer → **Add to Home Assistant**, or: **Settings → Devices & services → Add integration → Cattle Sprayer Mesh**.
5. Paste the SoftAP pairing card and select the USB port.

## License

MIT — see product branding; integration code may be used with Sinewerx sprayers.
