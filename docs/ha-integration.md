# Home Assistant integration

## 1. Add the device

Flash the panel (see `docs/build-and-flash.md`), let it join your Wi-Fi, then
**Settings → Devices & Services → Add Integration → ESPHome** and enter the
device name (`reterminal-e1003-ha` for the developer profile, or its IP).
The reference release uses a MAC-suffixed name and plaintext-only API access
without a key. In the ESPHome
integration options, enable **Allow the device to perform Home Assistant actions**
so touches can control the configured target.

The device appears with these entities:

| Entity | Direction | Notes |
|--------|-----------|-------|
| `sensor.<...>_temperature` / `_humidity` | panel → HA | onboard SHT4x |
| `text.<...>_zone_script_hook` | HA → panel | routing mode switch (below) |
| `text.<...>_clock_message` | HA → panel | clock card banner |
| `text.<...>_main_light_target` | HA → panel | entity_id the buttons control |
| `text.<...>_main_light_action` | HA → panel | action used by the % buttons |
| `text.<...>_main_light_state` | HA → panel | optional card state override |
| `text.<...>_main_light_value` | HA → panel | optional card value override |
| `button.<...>_repaint` … | HA → panel | `esphome.<device>_repaint`, `_beep` actions |

The buzzer is `internal: true` on purpose — an on-board beeper is not an HA
feature and only adds clutter.

## 2. Pick a routing mode

### Direct mode (default, zero HA setup)

`zone_script_hook` is empty. Taps call `homeassistant.toggle` on
`main_light_target`, and the percentage buttons call `main_light_action` with
`brightness_pct`. Nothing to configure; use it as the baseline.

### Hook mode (HA owns the routing)

```yaml
action: text.set_value
target: { entity_id: text.<...>_zone_script_hook }
data: { value: script.e1003_zone }
```

Now every tap calls `script.e1003_zone` with `{zone, control, data_name,
data_value}` and the firmware does nothing else. See
`docs/configuration.md` for the full list of things this unlocks.

## 3. Copy the package

`ha/e1003_dashboard.yaml` is a drop-in Home Assistant package:

```
config/
├── configuration.yaml        # homeassistant: packages: !include_dir_named packages
└── packages/
    └── e1003_dashboard.yaml
```

It contains:

* `input_text.e1003_main_light` — the single place where you name the target,
* `script.e1003_zone` — the routing `choose:` block you edit,
* `script.e1003_snapshot` — the response script used by the PULL package,
* two example automations that mirror state into the panel's card overrides.

## 4. Keep the card in sync when you re-target

The card's *display* falls back to the compile-time binding (`ha_light_entity` in
`e1003-dashboard.yaml`) unless something overrides it. To make the card follow
whatever you point the buttons at — including a target chosen at runtime — push
two strings into the panel:

```yaml
automation:
  - alias: "E1003 light card follows the configured target"
    mode: queued
    triggers:
      - trigger: state
        entity_id: input_text.e1003_main_light
      - trigger: state
        entity_id: light.deskside_lamp
    actions:
      - variables:
          target: "{{ states('input_text.e1003_main_light') }}"
      - action: text.set_value
        target: { entity_id: text.<...>_main_light_state }
        data: { value: "{{ states(target) }}" }
      - action: text.set_value
        target: { entity_id: text.<...>_main_light_value }
        data:
          value: >-
            {{ (state_attr(target, 'brightness') or 0) / 2.55 | round(0) | int }}
```

Notes:

* `brightness` is 0–255 in HA, the card wants 0–100.
* `state_value` accepts anything; the card prints `On` for `on` and `Off`
  otherwise.
* An empty overrides entity means "use the firmware's own binding", so clearing
  these never breaks the display.

## 5. Push anything else onto the screen

The clock card banner is a free text field — weather, calendar, bin day:

```yaml
automation:
  - alias: "E1003 banner"
    triggers:
      - trigger: time_pattern
        minutes: "/10"
    actions:
      - action: text.set_value
        target: { entity_id: text.<...>_clock_message }
        data:
          value: >-
            {{ state_attr('weather.home','temperature') }}°C ·
            {{ states('weather.home') }}
```

There is no compile-time coupling here: the firmware just draws the string.

## 6. Optional: the PULL channel

If you would rather the panel poll than have HA push, add

```yaml
# e1003-dashboard.yaml
packages:
  ha_pull: !include packages/ha-pull.yaml
```

rebuild once, then set:

* `text.<...>_pull_action` = `script.e1003_snapshot`
* `text.<...>_pull_template` = a Jinja template producing JSON, e.g.
  ```jinja
  {"message": "{{ states('sensor.outdoor_temperature') }}°C",
   "state": "{{ states('light.deskside_lamp') }}",
   "value": "{{ (state_attr('light.deskside_lamp','brightness') or 0) / 2.55 | round(0) }}"}
  ```

The firmware sends that template with `capture_response`, HA renders it and
returns the JSON, and each key lands in the matching card override. Requires a
recent Home Assistant (action responses over the ESPHome API).

## 7. Troubleshooting

| Symptom | Check |
|---------|-------|
| Taps do nothing | `scripts/build.sh logs` — zone hits are logged as `zone 'light_50' op=1 target='...'`. An empty target means the runtime text entity is empty. |
| Card shows `Off 0%` while HA says otherwise | the state/value overrides are empty or stale; push them, or clear them to fall back |
| Hook set but nothing happens | the hook must be a callable action string (`script.xxx`), and the script must not error — check HA's logbook for `script.e1003_zone` |
| Ghosting after many partial refreshes | expected: the panel does a full GC16 refresh every `full_update_every` paints. Call `esphome.<device>_repaint` to force one |
| Entity ids in this doc do not match | Home Assistant composes them from the device name; look them up in Developer Tools → States |