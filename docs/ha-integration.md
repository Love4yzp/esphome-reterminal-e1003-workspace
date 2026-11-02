# Home Assistant integration

## First connection

For a factory image:

1. Flash `firmware.factory.bin` through the browser installer or USB.
2. Keep USB connected and use the Improv Serial Wi-Fi dialog.
3. If Improv is unavailable, join the fallback hotspot whose name starts with
   `reterminal-e1003-ha-`, then open `192.168.4.1`.
4. Add the discovered ESPHome device in Home Assistant. The first connection
   provisions a unique API encryption key.

The personal profile already contains the owner's Wi-Fi and API key from
`secrets.yaml`, so it can be added by hostname or IP after boot.

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
| `zone_script_hook` | HA → panel | empty for direct mode; script/action for hook mode |
| `clock_message` | HA → panel | optional banner |
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

Direct mode is active when `zone_script_hook` is empty. The toggle zone uses
`homeassistant.toggle`; percentage zones use `light.turn_on`.

For custom behavior, set the hook to an HA action such as
`script.e1003_zone`. The panel passes `{zone, control, data_name, data_value}`
and skips all built-in routing. `ha/e1003_dashboard.yaml` contains an editable
example package.

## Push arbitrary display content

The banner and light display values are normal `text` entities:

```yaml
automation:
  - alias: "E1003 banner"
    triggers:
      - trigger: time_pattern
        minutes: "/10"
    actions:
      - action: text.set_value
        target:
          entity_id: text.<panel>_clock_message
        data:
          value: >-
            {{ state_attr('weather.home', 'temperature') }}°C ·
            {{ states('weather.home') }}
```

Use PUSH unless polling is required. To enable the optional PULL channel, add
`ha_pull: !include packages/ha-pull.yaml` to the personal profile, rebuild, and
configure its action/template text entities.

## Troubleshooting

| Symptom | Check |
|---|---|
| card says `Setup` | `main_light_target` is empty; create the blueprint automation or set it manually |
| touch beeps but no HA action occurs | target is empty, or the configured hook script failed |
| action works but card is stale | state/value text entities are not being mirrored; check the blueprint automation trace |
| fallback hotspot is unavailable | the 15-minute provisioning window may have closed; reboot the panel |
| touch area is offset | verify the zone on hardware; do not remove the documented mirror conversion |
