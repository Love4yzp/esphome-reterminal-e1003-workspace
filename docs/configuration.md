# Configuration

The project has three entry points and four shared firmware modules. Choose the
entry point based on who will receive the panel; do not copy Wi-Fi or API
credentials into shared packages.

## Firmware profiles

| Profile | Intended use | Wi-Fi and API behavior | OTA |
|---|---|---|---|
| `e1003-factory.yaml` | public image / first delivery | no station credentials or API key; Wi-Fi is provisioned through Improv Serial or the captive portal; Home Assistant sets the API key on first connection | no persistent native OTA; captive portal has a temporary web updater while provisioning is open |
| `e1003-release.yaml` | keyless USB reference flow | no station credentials; Improv Serial; plaintext-only API with MAC-suffixed identity | none |
| `e1003-dashboard.yaml` | personal development | reads Wi-Fi, fallback AP password and API key from `secrets.yaml` | enabled with API encryption |

The shared modules are:

| Module | Owns |
|---|---|
| `packages/core.yaml` | identity and ESP32 platform |
| `packages/hardware.yaml` | buses, buzzer, sensors and RTC |
| `packages/ui.yaml` | boot paint, dirty flags, refresh and rendering |
| `packages/interaction.yaml` | runtime text entities, touch zones and HA calls |

`packages/ha-direct-state.yaml` is an optional adapter loaded only by the
personal profile. It mirrors the personal profile's fixed default light into
the same runtime state entities used by the UI.

## Compile-time substitutions

Shared defaults, pins and fonts live in `packages/defaults.yaml`. The personal
profile overrides only its default target:

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

The [keyless reference profile](provisioning.md) overrides the device name,
adds a MAC suffix, starts with an empty target, and uses plaintext-only API
access. It requires no user secrets file. Its `firmware_version` is build-time
project metadata, not a runtime setting.

## Runtime entities

`packages/interaction.yaml` exposes these Home Assistant `text` entities:

Text settings are normally flushed to flash every 60 seconds. Allow at least
65 seconds after a change before removing power or performing a hard reset.
A live API readback confirms the current value, not completion of that flash
write. The App waits before restarting and verifying the saved target; see
[reference setup](provisioning.md).

| Entity suffix | Empty/default behavior | Purpose |
|---|---|---|
| `zone_script_hook` | empty: use direct mode | optional HA action called for every zone |
| `clock_message` | empty: local time-of-day greeting | clock card banner |
| `main_light_target` | factory: empty; personal: `default_light_target` | entity controlled by the light zones |
| `main_light_state` | empty: shown as off when a target exists | display state pushed by HA |
| `main_light_value` | empty: `0` | display brightness, `0`–`100` |

The target and its displayed state are deliberately separate. ESPHome can call
an entity id stored in text at runtime, but a `platform: homeassistant` state
subscription requires a compile-time literal entity id. Use the supplied
blueprint to keep target, state and value synchronized in the factory profile.

## Direct mode

With `zone_script_hook` empty:

- the main button calls `homeassistant.toggle` on `main_light_target`;
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

Every touch then calls that action with:

| Field | Example |
|---|---|
| `zone` | `light_50` |
| `control` | `main_light` |
| `data_name` | `brightness_pct` |
| `data_value` | `50` |

Hook mode replaces direct mode, so one touch cannot produce both actions. Clear
the hook to return to direct mode.

## Recommended Home Assistant setup

Import `ha/blueprints/automation/e1003_light_sync.yaml`, then select:

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
| controlled light, displayed state/value, banner or hook | no |
| Wi-Fi credentials on an already provisioned factory device | no, use USB Improv Serial |
| card/button count, geometry, fonts or artwork | yes |
| pins, board or display model | yes |
| adding/removing an ESPHome module | yes |
