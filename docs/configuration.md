# Configuration: three tiers, and what can change without reflashing

This is the document to read before you edit a single YAML file.

## The short answer

**Yes — re-targeting the panel can be done entirely from Home Assistant.** The
firmware exposes every device-specific decision as a plain HA `text` entity, so
"make this button control a different light" is a service call, not a rebuild.

What *cannot* be changed at runtime is the **design**: how many cards there are,
where they sit, and how many buttons the bitmap has. That is geometry baked into
the e-paper artwork, and it is a deliberate trade — the panel is a design, not a
widget toolkit.

```
              runtime (no reflash)                  compile-time (reflash)
   ┌─────────────────────────────────────┐  ┌────────────────────────────────┐
   │ which entity a button controls      │  │ number / position of buttons   │
   │ which action it calls               │  │ card geometry and fonts        │
   │ what text a card displays           │  │ hardware pins, panel model     │
   │ whether HA or the panel does logic  │  │ default fallback bindings      │
   └─────────────────────────────────────┘  └────────────────────────────────┘
```

## Tier 1 — build flags (no YAML editing, but a recompile)

Every value in the `substitutions:` block of the shared `e1003-base.yaml` can be
overridden from the command line. Useful for CI, for flashing several panels
from one checkout, or for changing a pin without touching git:

```bash
scripts/build.sh compile \
  -s device_name panel-kitchen \
  -s friendly_name "Kitchen Panel" \
  -s ha_light_entity light.kitchen_ceiling \
  -s timezone Europe/Berlin
```

Layout-derived values (`canvas_width`, `refresh_*`) are generated into
`layout/generated/policy.yaml` and cannot be overridden this way — edit
`layout/ui_layout.yaml` instead, which is the point.

`e1003-dashboard.yaml` adds developer credentials to those shared defaults.
The [release prototype](provisioning.md) overrides the device name and uses a
MAC suffix. Its target starts empty, so buttons do nothing until configured;
the unused fallback entity is `light.e1003_unconfigured`. Display state/value
overrides keep the same empty-value fallback behavior. Serial Wi-Fi and API-key
setup do not require a user secrets file. `firmware_version` defaults to `0.1.0`
in the release profile and is build-time project metadata, not a runtime setting.

## Tier 2 — runtime text entities (no recompile, no reboot)

`packages/ha-bridge.yaml` declares these. They are normal Home Assistant
entities; `restore_value: true` means your settings survive reboots and OTA
updates.

Text settings are normally flushed to flash every 60 seconds. Allow at least
65 seconds after a change before removing power or performing a hard reset.
A live API readback confirms the current value, not completion of that flash
write. Wi-Fi and runtime API key provisioning synchronize their own writes
immediately; see [the provisioning proof](provisioning-verification.md).

| Entity (suffix) | Default | Purpose |
|-----------------|---------|---------|
| `zone_script_hook` | *(empty)* | HA action called on **every** tap. Empty = built-in direct mode. |
| `clock_message` | *(empty)* | Overrides the clock card message. Empty = local greeting. |
| `main_light_target` | `light.deskside_lamp` | entity_id the light card controls. |
| `main_light_action` | `light.turn_on` | Action used by the 25/50/75/100% buttons. |
| `main_light_state` | *(empty)* | Card state override (`on`/`off`). Empty = compile-time binding. |
| `main_light_value` | *(empty)* | Card value override (`0`..`100`). Empty = compile-time binding. |

Find the real entity ids in **Developer Tools → States**, searching for the
device name; Home Assistant composes them from the ESPHome device name, so they
look like `text.e1003_smart_workspace_main_light_target`.

### Recipe: point a button at a different light

```yaml
action: text.set_value
target:
  entity_id: text.e1003_smart_workspace_main_light_target
data:
  value: light.office_strip
```

That is it. The next tap calls `homeassistant.toggle` on `light.office_strip`,
and the 25/50/75/100% buttons call `light.turn_on` with `brightness_pct` on the
same entity. No reflash, no reboot.

### Recipe: drive a switch, fan or input_boolean instead of a light

```yaml
# two service calls, once
action: text.set_value
target: { entity_id: text.e1003_smart_workspace_main_light_target }
data: { value: switch.desk_fan }

action: text.set_value
target: { entity_id: text.e1003_smart_workspace_main_light_action }
data: { value: fan.turn_on }      # used by the % buttons
```

The toggle button works with any domain because it calls domain-agnostic
`homeassistant.toggle`. The percentage buttons pass `brightness_pct`, which is
the right key for `light.turn_on`; for a fan you would switch those zones to the
hook (below) or adapt the `call` branch in `packages/touch.yaml`. That one
branch is the only light-specific line left in the firmware, and it is marked.

### Recipe: show something else in the clock card

```yaml
action: text.set_value
target: { entity_id: text.e1003_smart_workspace_clock_message }
data: { value: "晴 24°C · 无风" }
```

Anything HA can template can go here, including a weather summary that is itself
driven by an automation:

```yaml
automation:
  - alias: "E1003 weather summary"
    triggers:
      - trigger: time_pattern
        minutes: "/10"
    actions:
      - action: text.set_value
        target: { entity_id: text.e1003_smart_workspace_clock_message }
        data:
          value: >-
            {{ state_attr('weather.home','temperature') }}°C ·
            {{ states('weather.home') }}
```

## Tier 3 — let Home Assistant own the buttons

Set `zone_script_hook` to an HA script and the firmware stops making decisions
entirely: it calls that script with the zone metadata and does nothing else.

```
zone_script_hook = script.e1003_zone
```

Every tap then calls `script.e1003_zone` with:

| field | example | meaning |
|-------|---------|---------|
| `zone` | `light_50` | the zone id from `layout/ui_layout.yaml` |
| `control` | `main_light` | which control the zone belongs to |
| `data_name` | `brightness_pct` | semantic payload name |
| `data_value` | `50` | payload value |

`ha/e1003_dashboard.yaml` contains a ready-to-paste script with a `choose:` block
you edit. This is the escape hatch for everything the direct mode cannot express:
scenes, conditions, notify calls, different behaviour per time of day.

**Direct mode vs hook mode is exclusive.** With a hook configured, the built-in
`homeassistant.toggle` path is skipped, so you never get double actions. Clear
the hook to go back to direct mode.

## Capability matrix

| I want to change... | Without reflashing? | How |
|---|---|---|
| Which light/switch a button controls | ✅ | `text..._main_light_target` |
| Which action the % buttons call | ✅ | `text..._main_light_action` |
| What the card says (`On`/`Off`, `57%`) | ✅ | `..._state` / `..._value` overrides, or the PULL package |
| Clock/banner text (weather, calendar, anything) | ✅ | `text..._clock_message` |
| What every button does, in general | ✅ | `zone_script_hook` → HA script |
| Show state of an entity the firmware never heard of | ✅ | PUSH (`text.set_value`) or PULL (`packages/ha-pull.yaml`) |
| Room name, greeting wording | ✅ | same text entities |
| Target entity used as the *fallback* | ⚠️ recompile | `-s ha_light_entity=...` |
| Number of buttons / cards | ❌ | design bitmap + `layout/ui_layout.yaml` |
| Button positions, card geometry, fonts | ❌ | `layout/ui_layout.yaml` + `png_to_h.py` |
| Hardware pins, panel model, board | ❌ | shared `e1003-base.yaml` substitutions |

The dividing line is honest: **behaviour is runtime, design is compile-time.**
Adding a sixth button means the artwork has to change anyway, and on e-paper the
artwork *is* the firmware.

## Reading state without recompiling: PUSH vs PULL

`platform: homeassistant` sensors (the compile-time fallback bindings) require a
literal `entity_id` at build time. Two ways around it:

**PUSH — Home Assistant tells the panel.** Recommended. An automation templates
the value and calls `text.set_value` on one of the panel's text entities. Event
driven, no polling, no extra firmware package. Recipe in
`docs/ha-integration.md`.

**PULL — the panel asks Home Assistant.** Enable `packages/ha-pull.yaml`, set the
`Pull action` entity to an HA script and the `Pull template` entity to a Jinja
template. The firmware calls that action with `capture_response`, HA renders the
template and returns JSON like `{"message": "...", "state": "on", "value": "57"}`,
and the panel publishes each key into the matching card override. Both the
action *and* the query are runtime text entities, so even the query is
reconfigurable without a reflash.

PULL needs a Home Assistant that supports ESPHome action responses and costs one
API round trip every few minutes; use PUSH unless the panel genuinely has to
poll.

## Discovering the entity ids

```bash
scripts/build.sh logs          # see the panel boot, confirm it connected
```
Then in Home Assistant: **Settings → Devices & Services → ESPHome → your
panel**. The text entities are listed under the device. Renaming the device in
Home Assistant does not affect the firmware — it only changes the entity ids, so
do that before writing automations.

## One firmware, many personas

Because all behaviour is HA-side, a single firmware can present completely
different personalities depending on Home Assistant state:

```yaml
automation:
  - alias: "E1003: office mode"
    triggers: [{ trigger: state, entity_id: input_select.room_mode }]
    actions:
      - action: text.set_value
        target: { entity_id: text.e1003_smart_workspace_main_light_target }
        data:
          value: >-
            {{ 'light.desk_lamp' if is_state('input_select.room_mode','work')
               else 'light.ambient' }}
      - action: text.set_value
        target: { entity_id: text.e1003_smart_workspace_clock_message }
        data:
          value: "{{ states('input_select.room_mode') }} mode"
```

Same binary, different behaviour, no OTA in the loop.
