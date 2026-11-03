# Home Assistant setup

The firmware does not require any file from this directory. Home Assistant
users can complete the normal setup from the web interface without opening the
Container filesystem or editing `configuration.yaml`.

## Import the blueprint from the Home Assistant UI

[Import the E1003 light blueprint into Home Assistant](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml)

If the redirect is unavailable, open **Settings → Automations & scenes →
Blueprints → Import blueprint** and paste:

```text
https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/blob/main/ha/blueprints/automation/e1003_light_sync.yaml
```

Create an automation from the imported blueprint and select:

1. the Home Assistant light to control;
2. the panel text entity ending in `Main light target`;
3. the panel text entity ending in `Main light state`;
4. the panel text entity ending in `Main light value`.

The panel controls the selected light, and changes made in Home Assistant are
mirrored to the e-paper card.

## Edit the panel entities directly

A real light and the blueprint are optional. The panel exposes editable Home
Assistant `text` entities, so its card can also be driven manually or by any
automation:

| Entity suffix | Accepted value | Effect |
|---|---|---|
| `main_light_target` | an entity id such as `light.desk_lamp`, or empty | destination for panel touches |
| `main_light_state` | `on`, `off`, or empty | selected ON/OFF segment |
| `main_light_value` | `0`–`100`, or empty | displayed brightness |

For a display-only preview, leave the target empty and edit state/value from
the device page. Touches still beep, but no Home Assistant light action is sent
until a target or custom hook is configured.
