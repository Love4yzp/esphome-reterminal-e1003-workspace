# Home Assistant integration

## First connection

1. Flash `firmware.factory.bin` through the browser installer or USB.
2. Join the open setup hotspot whose name starts with `reterminal-e1003-`.
3. Open `192.168.4.1` and save the destination Wi-Fi credentials.
4. Add the discovered ESPHome device in Home Assistant. The first connection
   provisions a unique API encryption key.
5. Import the supplied light-sync blueprint and create an automation.

No **Allow the device to perform Home Assistant actions** setting is required
for the normal light path. The device publishes a sensor state, and the
blueprint performs light services inside Home Assistant.

## Panel entities

Home Assistant creates names based on the device name. Look them up in
**Developer Tools → States** rather than copying the examples literally.

| Entity suffix | Direction | Purpose |
|---|---|---|
| `temperature`, `humidity` | panel → HA | onboard SHT4x |
| `main_light_command` | panel → HA | unique ON/OFF/brightness command |
| `zone_script_hook` | HA → panel | empty for command mode; advanced direct action hook |
| `reachy_script_hook` | HA → panel | action for the six Reachy scene tiles |
| `light_target` | HA → panel | optional light entity for blueprint-free control |
| `main_light_state` | HA → panel | card state |
| `main_light_value` | HA → panel | card brightness, `0`–`100` |
| `repaint`, `beep` actions | HA → panel | diagnostic actions |

## Why the light is selected in the blueprint, not on the device page

ESPHome cannot offer an entity picker. Its device page renders only the entity
types its firmware declares, and a `select` entity needs its option list at
compile time, so Home Assistant lights cannot be listed at runtime. The device
side knob is therefore a text input, not a dropdown.

Reading a light's state has the same restriction: the `homeassistant` sensor and
text_sensor components take a compile-time `entity_id`. A runtime value can
drive an action, but the stock components cannot follow a runtime-chosen
entity. That
is why `packages/ha-direct-state.yaml` exists for fixed targets and why the
blueprint owns the picker for the general case — it is the only place where a
real entity selector can live.

If you do not need state mirroring, set `Light target` on the device page to the
light entity id and skip the blueprint entirely. See
[direct light mode](configuration.md#direct-light-mode).

## Recommended: import the light-sync blueprint

[Import the blueprint from the Home Assistant UI](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml),
then create an automation. Select one HA light and the panel's
command/state/value entities. The blueprint:

- listens for every panel light command;
- calls `light.turn_on` or `light.turn_off` inside Home Assistant;
- mirrors its state;
- converts HA brightness `0`–`255` to panel brightness `0`–`100`;
- refreshes the values when Home Assistant starts.

This is the normal setup. The light selector lives in the Home Assistant
blueprint automation, not on the ESPHome device page. The ESPHome integration
exposes the panel's command and display entities; it does not provide a UI for
choosing which HA light a device should control. Keeping that choice in HA lets
the firmware remain generic and keeps entity ids out of public release images.

## Faster setup from the command line

If you prefer not to create the automation in the HA UI, the deploy script can
list the connected panel entities and available lights, then create or update
the same blueprint automation with one selected light. This does not require
SSH access or a writable `/config`; it uses the Home Assistant API.

```bash
export HA_URL=http://homeassistant.local:8123
export HA_USERNAME=your-user
export HA_PASSWORD=your-password

uv run python scripts/deploy_ha.py --list
uv run python scripts/deploy_ha.py --light light.desk_lamp --trigger
```

The script:

1. obtains a short-lived token with `POST /auth/login_flow` and
   `POST /auth/token`;
2. installs the blueprint with the WebSocket `blueprint/save` command;
3. creates or updates an automation through
   `POST /api/config/automation/config/<automation_id>`;
4. discovers the panel's command/state/value entities by suffix and
   rejects ambiguous matches unless `--panel` is supplied.

Re-running the command is safe. It updates only an automation with the same id,
blueprint and alias, and stops with a conflict message when the id or alias
belongs to another automation. `--dry-run` prints the resolved plan,
`--update-blueprint` refreshes the installed blueprint, and `HA_TOKEN` can
replace the username/password pair.

No light or blueprint is required to preview the card. Open the E1003 device in
Home Assistant and edit its `Main light state` and `Main light value` text
entities directly. Touches update the local card and beep, but no real light
changes unless an automation consumes `Main light command`. Any HA automation
can write the state/value entities with `text.set_value`.

## Command and hook routing

Light touches dispatch in this order: `light_target` set calls that entity
directly; otherwise `zone_script_hook` set calls that action; otherwise command
mode publishes a unique `Main light command` sensor state. The two direct paths
need the ESPHome action permission, command mode does not.

Command mode is active when `zone_script_hook` is empty. ON/OFF, preset buttons,
and the slider publish a unique `Main light command` sensor state. The
brightness slider sends one exact `0`–`100` value on release, with zero treated
as off by the blueprint. Light controls update the card immediately; the
blueprint subsequently writes back the real light state.

For custom behavior, set the hook to an HA action such as
`script.e1003_zone`. The panel passes `{zone, control, data_name, data_value}`
and skips command publishing. Hook scripts are an advanced extension that
requires **Allow the device to perform Home Assistant actions**; the normal
blueprint path intentionally leaves the hook empty and needs no such permission.

Reachy routing is intentionally separate. Set `reachy_script_hook` to an HA
action such as `script.e1003_reachy`. Each touch passes:

- `zone`: the full zone id, such as `reachy_retail_intro`;
- `action`: `retail_intro`, `space_intro`, `rescue_intro`, `stop`, `wake`, or
  `language`.

Reachy touches always beep. They do not redraw the e-paper display.
The Reachy hook is also a direct device action and therefore requires the same
advanced ESPHome permission when configured.

## Upgrading an older panel automation

Firmware versions before this command-channel design exposed
`Main light target`. After updating:

1. re-import or update the blueprint;
2. edit the existing automation;
3. replace the old target input with the new `Main light command` sensor.

The target text entity disappears because the selected light now lives only in
the Home Assistant automation.

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

This is not a factory reset. The Home Assistant API key, display state, and
action hooks remain stored. USB Improv Serial remains an alternative setup path.

## Troubleshooting

| Symptom | Check |
|---|---|
| no ON/OFF segment is selected | `main_light_state` is empty or not `on`/`off`; create the blueprint automation or edit it manually |
| touch beeps but no light changes | the blueprint automation is missing/disabled, its command input is wrong, or an advanced hook failed |
| action works but card is stale | state/value text entities are not being mirrored; check the blueprint automation trace |
| Home Assistant does not discover the panel | read the IP from the network card and add the ESPHome integration manually |
| a different Wi-Fi is required | tap the SSID row twice, then use the setup AP |
| setup hotspot is unavailable | the 24-hour provisioning window may have closed; reboot the panel |
| touch area is offset | verify the zone on hardware; do not remove the documented mirror conversion |
