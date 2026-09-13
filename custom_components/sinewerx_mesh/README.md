# Sinewerx Mesh (Home Assistant)

Talks to the **Sinewerx house gateway** (Xiao S3 WIO) over HTTP. Devices appear after their first MeshCore uplink.

## Prefer MQTT when possible

If the gateway SoftAP wizard has an MQTT broker set, Home Assistant only needs the built-in **MQTT** integration — no custom component. Use this HACS integration when you do **not** want MQTT.

## Install

1. HACS → Integrations → Custom repository (or My link from the gateway done page).
2. Download **Sinewerx Mesh**, restart Home Assistant.
3. Settings → Devices & services → Add → **Sinewerx Mesh**, or accept the zeroconf discovery for `_swx-gw._tcp`.

Do **not** also connect Home Assistant to the gateway companion TCP 5000 / USB / BLE — the gateway owns the radio.

## Legacy

`cattle_sprayer_mesh` (companion TCP) is deprecated. Migrate to gateway MQTT or this HTTP integration.
