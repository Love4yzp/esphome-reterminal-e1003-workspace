# Home Assistant integration

## First connection

For the open-source default:

1. Flash `firmware.factory.bin` through the browser installer or USB.
2. Join the open setup hotspot. The default source build uses `E1003-Setup`;
   the tagged factory image uses a name starting with `reterminal-e1003-`.
3. Open `192.168.4.1` and save the destination Wi-Fi credentials.
4. Add the discovered ESPHome device in Home Assistant. The first connection
   provisions a unique API encryption key.

The keyless reference profile uses a MAC-suffixed device name and
plaintext-only API access. Follow [the reference provisioning flow](provisioning.md),
then add the discovered device without an encryption key.

For every profile, enable **Allow the device to perform Home Assistant actions**
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

This is the normal factory-profile setup. The firmware remains generic and no
user Wi-Fi, API key or entity id is published in the release image.

## Direct and hook routing

Direct mode is active when `zone_script_hook` is empty. ON and OFF call
`light.turn_on` and `light.turn_off`; percentage zones use `light.turn_on`.

For custom behavior, set the hook to an HA action such as
`script.e1003_zone`. The panel passes `{zone, control, data_name, data_value}`
and skips all built-in routing. `ha/e1003_dashboard.yaml` contains an editable
example package.

Reachy routing is intentionally separate. Set `reachy_script_hook` to an HA
action such as `script.e1003_reachy`. Each touch passes:

- `zone`: the full zone id, such as `reachy_retail_intro`;
- `action`: `retail_intro`, `space_intro`, `rescue_intro`, `stop`, `wake`, or
  `language`.

Reachy touches always beep. They do not redraw the e-paper display.

## Network card and Last Update

The right-side status card is event driven:

| State | Network role/name | Detail |
|---|---|---|
| `READY` | Home Assistant connected/waiting + station SSID | current device IP |
| `CONNECTING` | saved Wi-Fi search | setup AP will start |
| `SETUP WI-FI` | active AP SSID | open `192.168.4.1` |
| `SETUP WI-FI` on release profile | USB setup | use Improv over USB |

When the setup AP is active it takes display priority, so the shown SSID is
the network the user must join. `Last Update` in the footer is repainted only
when the panel really renders another card.

## IP address and mDNS

The connected network card shows the current station IP as `IP <address>`.
Use that address to add the ESPHome integration manually when Home Assistant
cannot discover the panel through mDNS.

If the card already says `HA CONNECTED`, the native API session is established;
mDNS discovery is no longer needed for that connection. A DHCP reservation in
the router keeps the displayed address stable without embedding a
network-specific static IP in public firmware.

## Changing Wi-Fi

If the saved Wi-Fi is unavailable, the firmware starts its fallback setup AP.
Join `E1003-Setup` for the default profile, or the MAC-suffixed AP for the
factory profile, then open `192.168.4.1` and save the new network.

If the old Wi-Fi is still reachable, the panel continues to use it. Temporarily
make that network unavailable and reboot the panel to enter the fallback flow,
or configure the new network over USB Improv Serial. The firmware intentionally
does not expose a one-touch factory-reset control: factory reset also removes
the API key, runtime target, display state, and action hooks.

## Troubleshooting

| Symptom | Check |
|---|---|
| no ON/OFF segment is selected | `main_light_target` or mirrored state is empty; create the blueprint automation or set it manually |
| touch beeps but no HA action occurs | target is empty, or the configured hook script failed |
| action works but card is stale | state/value text entities are not being mirrored; check the blueprint automation trace |
| Home Assistant does not discover the panel | read the IP from the network card and add the ESPHome integration manually |
| a different Wi-Fi is required | make the saved network unavailable, reboot, then use the fallback setup AP |
| setup hotspot is unavailable | the 24-hour provisioning window may have closed; reboot the panel |
| touch area is offset | verify the zone on hardware; do not remove the documented mirror conversion |
