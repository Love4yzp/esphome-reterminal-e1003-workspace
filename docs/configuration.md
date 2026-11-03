# Configuration

The project has one credential-free firmware entry point and four shared
firmware modules. No user credentials belong in tracked YAML or shared
packages.

## Firmware entry point

`e1003-dashboard.yaml` is the only supported entry point. Source builds, tagged
releases, and the browser installer all compile it. It starts an open
MAC-suffixed setup AP, serves the captive portal at `192.168.4.1`, supports
Improv Serial, and lets Home Assistant provision a unique API encryption key.
There is no persistent native OTA service; the captive portal includes a web
updater.

The shared modules are:

| Module | Owns |
|---|---|
| `packages/core.yaml` | identity and ESP32 platform |
| `packages/hardware.yaml` | buses, buzzer, sensors and RTC |
| `packages/ui.yaml` | boot paint, dirty flags, refresh and rendering |
| `packages/interaction.yaml` | runtime text entities, touch zones and HA calls |

`packages/ha-direct-state.yaml` is an optional adapter for downstream custom
builds with a compile-time light target. The public firmware omits it and uses the
same runtime state entities as the generic UI.

## Compile-time substitutions

Shared defaults, pins, and fonts live in `packages/defaults.yaml`. The public
firmware leaves the control target empty.
A custom downstream build can add a compile-time target:

```yaml
substitutions:
  default_light_target: light.deskside_lamp
```

Command-line overrides still work:

```bash
uv run python scripts/build.py compile \
  -s device_name panel-kitchen \
  -s friendly_name "Kitchen Panel" \
  -s default_light_target light.kitchen_ceiling
```

Geometry and refresh policy come from `layout/ui_layout.yaml`; edit that source
instead of overriding its generated substitutions.

The setup AP uses the final MAC-suffixed device name, such as
`reterminal-e1003-a1b2c3`. The screen reads the same runtime name, so the setup
instructions always match the network that the device broadcasts.

## Runtime entities

`packages/interaction.yaml` exposes these Home Assistant `text` entities:

Text settings are normally flushed to flash every 60 seconds. Allow at least
65 seconds after a change before removing power or performing a hard reset.
A live API readback confirms the current value, not completion of that flash
write.

| Entity suffix | Empty/default behavior | Purpose |
|---|---|---|
| `zone_script_hook` | empty: use direct light mode | optional HA action called for light zones |
| `reachy_script_hook` | empty: beep only | HA action called by the six Reachy scene zones |
| `main_light_target` | empty: touches send no direct light action | entity controlled by the light zones |
| `main_light_state` | empty: no selected ON/OFF segment | display state pushed by HA |
| `main_light_value` | empty: `0` | display brightness, `0`–`100` |

The target and its displayed state are deliberately separate. ESPHome can call
an entity id stored in text at runtime, but a `platform: homeassistant` state
subscription requires a compile-time literal entity id. Use the supplied
blueprint to keep target, state and value synchronized in the public firmware.

The display does not require a target. For a display-only preview, leave
`main_light_target` empty and edit `main_light_state` and
`main_light_value` from the Home Assistant device page. Panel touches still
beep but direct mode sends no action until a target is configured.

## Direct mode

With `zone_script_hook` empty:

- the ON and OFF zones call `light.turn_on` and `light.turn_off`;
- 25/50/75/100 percent zones call `light.turn_on` on the same target with
  `brightness_pct`.

Direct mode is intentionally light-specific. For a switch, fan, scene,
conditions or per-zone custom logic, use hook mode.

## Hook mode

Set the hook entity to an HA script:

```yaml
action: text.set_value
target:
  entity_id: text.<panel>_zone_script_hook
data:
  value: script.e1003_zone
```

Every light touch then calls that action with:

| Field | Example |
|---|---|
| `zone` | `light_50` |
| `control` | `main_light` |
| `data_name` | `brightness_pct` |
| `data_value` | `50` |

Hook mode replaces direct mode, so one touch cannot produce both actions. Clear
the hook to return to direct mode.

Reachy uses the separate `reachy_script_hook`. Each of its six existing scene
tiles beeps and calls that action with `zone` plus one of these `action` values:
`retail_intro`, `space_intro`, `rescue_intro`, `stop`, `wake`, or `language`.
The display is not refreshed for a Reachy touch.

## Recommended Home Assistant setup

[Import the light-sync blueprint from the Home Assistant UI](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml),
then select:

1. the light to control;
2. the panel's target text entity;
3. the panel's state text entity;
4. the panel's value text entity.

The automation writes the target and mirrors every light state/brightness
change to the e-paper card. Re-targeting therefore needs no firmware rebuild.

For arbitrary content, Home Assistant can push values with `text.set_value`.
The optional `packages/ha-pull.yaml` adapter is available when the panel must
request a JSON snapshot instead; PUSH is simpler and should be the default.

## What requires rebuilding

| Change | Rebuild? |
|---|---|
| controlled light, displayed state/value, or hook | no |
| Wi-Fi credentials | no, tap the network card's SSID row twice and use the captive portal, or use USB Improv Serial |
| card/button count, geometry, fonts or artwork | yes |
| pins, board or display model | yes |
| adding/removing an ESPHome module | yes |
