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
| `packages/interaction.yaml` | runtime entities, touch zones and command publishing |

`packages/ha-direct-state.yaml` is an optional adapter for downstream custom
builds that want to import one compile-time light's state directly. The public
firmware omits it and uses the same runtime state entities as the generic UI.

## Compile-time substitutions

Shared defaults, pins, and fonts live in `packages/defaults.yaml`. The public
firmware contains no Home Assistant entity id. A custom downstream build can
include the optional fixed-state adapter and define its required substitution:

```yaml
substitutions:
  default_light_target: light.deskside_lamp

packages:
  dashboard: !include e1003-base.yaml
  fixed_light_state: !include packages/ha-direct-state.yaml
```

Command-line overrides still work:

```bash
uv run python scripts/build.py compile \
  -s device_name panel-kitchen \
  -s friendly_name "Kitchen Panel"
```

Geometry and refresh policy come from `layout/ui_layout.yaml`; edit that source
instead of overriding its generated substitutions.

The setup AP uses the final MAC-suffixed device name, such as
`reterminal-e1003-a1b2c3`. The screen reads the same runtime name, so the setup
instructions always match the network that the device broadcasts.

## Runtime entities

`packages/interaction.yaml` exposes one read-only command sensor and four
runtime `text` entities:

Text settings are normally flushed to flash every 60 seconds. Allow at least
65 seconds after a change before removing power or performing a hard reset.
A live API readback confirms the current value, not completion of that flash
write.

| Entity suffix | Type/default | Purpose |
|---|---|---|
| `main_light_command` | read-only sensor | unique command emitted by every light touch |
| `main_light_state` | text, empty | display state pushed by HA |
| `main_light_value` | text, empty | display brightness, `0`–`100` |
| `zone_script_hook` | text, empty | optional advanced HA action replacing command publishing |
| `reachy_script_hook` | text, empty | optional HA action called by the six Reachy scene zones |

The command and displayed state are deliberately separate. The firmware reports
user intent through `main_light_command`; the supplied blueprint selects the
real light, performs the service call inside Home Assistant, and mirrors the
real state/value back. The firmware therefore contains no light entity id and
does not need device action permission.

For a display-only preview, edit `main_light_state` and `main_light_value` from
the Home Assistant device page. ON/OFF, presets and the slider also update the
card locally and trigger one partial refresh. They change a real light only
when a blueprint automation consumes `main_light_command`.

## Command mode

With `zone_script_hook` empty:

- ON and OFF publish `state|on` or `state|off`;
- 25/50/75/100 percent zones publish `brightness_pct|<value>`;
- the brightness slider maps a tap or drag to `0`–`100`, then publishes one
  command when the finger is released.

The actual sensor state includes a sequence prefix, for example
`17|brightness_pct|50`. This guarantees that tapping 50% twice still produces
two Home Assistant state changes. The sequence number is an implementation
detail; automations should use the supplied blueprint instead of parsing it
again.

Each control first updates the card optimistically. The imported blueprint
performs the light action, then mirrors the real state back to the same
state/value entities.

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

The slider uses `zone: light_slider` and sends its exact release value in
`data_value`.

Hook mode replaces command mode, so one touch cannot produce both actions. Clear
the hook to return to command mode. Because hook mode asks the ESPHome device to
call an HA action directly, it is an advanced path and requires enabling
**Allow the device to perform Home Assistant actions**. The recommended
blueprint path does not.

Reachy uses the separate `reachy_script_hook`. Each of its six existing scene
tiles beeps and calls that action with `zone` plus one of these `action` values:
`retail_intro`, `space_intro`, `rescue_intro`, `stop`, `wake`, or `language`.
The display is not refreshed for a Reachy touch.

## Recommended Home Assistant setup

[Import the light-sync blueprint from the Home Assistant UI](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml),
then select:

1. the light to control;
2. the panel's command sensor;
3. the panel's state text entity;
4. the panel's value text entity.

The automation consumes panel commands and mirrors every real light
state/brightness change to the e-paper card. Re-targeting therefore needs no
firmware rebuild or ESPHome permission change.

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
