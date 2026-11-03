# Home Assistant integration

## First connection

1. Flash `firmware.factory.bin` through the browser installer or USB.
2. Join the open setup hotspot whose name starts with `reterminal-e1003-`.
3. Open `192.168.4.1` and save the destination Wi-Fi credentials.
4. Add the discovered ESPHome device in Home Assistant. The first connection
   provisions a unique API encryption key.

Enable **Allow the device to perform Home Assistant actions**
in the ESPHome integration options so touches can control the configured target.

## Panel entities

Home Assistant creates names based on the device name. Look them up in
**Developer Tools → States** rather than copying the examples literally.

| Entity suffix | Direction | Purpose |
|---|---|---|
| `temperature`, `humidity` | panel → HA | onboard SHT4x |
| `zone_script_hook` | HA → panel | empty for direct light mode; action for custom light routing |
| `reachy_script_hook` | HA → panel | action for the six Reachy scene tiles |
| `main_light_target` | HA → panel | runtime target entity id |
| `main_light_state` | HA → panel | card state |
| `main_light_value` | HA → panel | card brightness, `0`–`100` |
| `repaint`, `beep` actions | HA → panel | diagnostic actions |

## Recommended: import the light-sync blueprint

Import `ha/blueprints/automation/e1003_light_sync.yaml` and create an
automation. Select one HA light and the panel's target/state/value text
entities. The blueprint:

- writes the selected light's entity id into the runtime target;
- mirrors its state;
- converts HA brightness `0`–`255` to panel brightness `0`–`100`;
- refreshes the values when Home Assistant starts.

This is the normal setup. The firmware remains generic and no
user Wi-Fi, API key or entity id is published in the release image.

If no physical light is available, copy `ha/e1003_demo.yaml` into Home
Assistant's `config/packages/` directory. It creates
`light.e1003_demo_light`, which behaves like a dimmable light in the Home
Assistant UI. Select it in the same blueprint to test panel state and controls.
See `ha/README.md` for the short setup sequence.

## Direct and hook routing

Direct mode is active when `zone_script_hook` is empty. ON and OFF call
`light.turn_on` and `light.turn_off`; percentage zones use `light.turn_on`.

For custom behavior, set the hook to an HA action such as
`script.e1003_zone`. The panel passes `{zone, control, data_name, data_value}`
and skips all built-in routing. Hook scripts are an advanced extension; the
demo package intentionally leaves them empty so the direct light path remains
easy to understand.

Reachy routing is intentionally separate. Set `reachy_script_hook` to an HA
action such as `script.e1003_reachy`. Each touch passes:

- `zone`: the full zone id, such as `reachy_retail_intro`;
- `action`: `retail_intro`, `space_intro`, `rescue_intro`, `stop`, `wake`, or
  `language`.

Reachy touches always beep. They do not redraw the e-paper display.

## Network card and Last Update

The right-side network card is event driven and uses three centered rows:

| State | Top SSID row | Middle IP row | Bottom HA row |
|---|---|---|---|
| station connected | current Wi-Fi SSID | current station IP | `HA CONNECTED` or `HA WAITING` |
| searching | `FINDING WI-FI` | `IP PENDING` | `HA OFFLINE` |
| setup AP active | MAC-suffixed setup AP name | `IP 192.168.4.1` | `HA OFFLINE` |

When the setup AP is active it takes display priority, so the shown SSID is
the network the user must join. `Last Update` in the footer is repainted only
when the panel really renders another card.

The icon above the SSID reflects the current network mode. A station connection
shows one to four filled RSSI bars: four at `-55 dBm` or better, three down to
`-67 dBm`, two down to `-78 dBm`, and one below that. RSSI is sampled every
30 seconds, but the e-paper is refreshed only when the reading crosses into a
different bar level. Searching shows four empty bar outlines; setup mode shows
an `AP` badge instead of a signal-strength reading.

## IP address and mDNS

The connected network card shows the current station IP as `IP <address>`.
Use that address to add the ESPHome integration manually when Home Assistant
cannot discover the panel through mDNS.

If the card already says `HA CONNECTED`, the native API session is established;
mDNS discovery is no longer needed for that connection. A DHCP reservation in
the router keeps the displayed address stable without embedding a
network-specific static IP in public firmware.

## Changing Wi-Fi

Tap the large SSID row at the top of the network card. It temporarily inverts
and shows `CHANGE WI-FI?` plus `TAP AGAIN TO CONFIRM`. Tap the same row again
within eight seconds; three short beeps play, then the firmware removes only
the saved Wi-Fi credentials and restarts. Join the MAC-suffixed setup AP, open
`192.168.4.1`, and save the replacement network.

The panel deliberately does not implement its own Wi-Fi scanner or on-screen
password keyboard. ESPHome's captive portal already owns network discovery,
credential entry, and error handling; duplicating that flow on a slow-refresh
e-paper screen would add substantial code and refresh cost for little benefit.
The action is named “change Wi-Fi,” not “disconnect,” because disconnecting
without removing the saved credentials would simply reconnect to the same
network.

This is not a factory reset. The Home Assistant API key, runtime target, display
state, and action hooks remain stored. USB Improv Serial remains an alternative
setup path.

## Troubleshooting

| Symptom | Check |
|---|---|
| no ON/OFF segment is selected | `main_light_target` or mirrored state is empty; create the blueprint automation or set it manually |
| touch beeps but no HA action occurs | target is empty, or the configured hook script failed |
| action works but card is stale | state/value text entities are not being mirrored; check the blueprint automation trace |
| Home Assistant does not discover the panel | read the IP from the network card and add the ESPHome integration manually |
| a different Wi-Fi is required | tap the SSID row twice, then use the setup AP |
| setup hotspot is unavailable | the 24-hour provisioning window may have closed; reboot the panel |
| touch area is offset | verify the zone on hardware; do not remove the documented mirror conversion |
