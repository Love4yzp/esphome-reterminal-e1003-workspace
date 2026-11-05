# Home Assistant setup

The firmware does not require any file from this directory. Home Assistant
users can complete the normal setup from the web interface without opening the
Container filesystem or editing `configuration.yaml`.

The normal light path does not require **Allow the device to perform Home
Assistant actions**. The panel publishes a command sensor; the imported
blueprint performs the service call inside Home Assistant.

## Import the blueprint from the Home Assistant UI

[Import the E1003 light blueprint into Home Assistant](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml)

If the redirect is unavailable, open **Settings → Automations & scenes →
Blueprints → Import blueprint** and paste:

```text
https://github.com/Love4yzp/esphome-reterminal-e1003-workspace/blob/main/ha/blueprints/automation/e1003_light_sync.yaml
```

Create an automation from the imported blueprint and select:

1. the Home Assistant light to control;
2. the panel sensor ending in `Main light command`;
3. the panel text entity ending in `Main light state`;
4. the panel text entity ending in `Main light value`.

The light is selected in this Home Assistant automation. The ESPHome device
page exposes the panel entities but does not have a target-light selector. The
panel controls the selected light, and changes made in Home Assistant are
mirrored to the e-paper card. Setting the panel's `Main light state` (`on` /
`off`) or `Main light value` (0-100) in Home Assistant also drives the light;
the automation's own mirror writes are ignored, so the two directions do not
loop.

If the panel is the only controller and state mirroring is not needed, skip the
automation: set the panel's `Light target` text entity to the light id and the
device calls `light.turn_on` / `light.turn_off` itself. That path needs
**Allow the device to perform Home Assistant actions** on the ESPHome
integration; see [direct light mode](../docs/configuration.md#direct-light-mode).

## Deploy from a terminal (API)

The blueprint import above is the shortest path for a browser user. For a
repeatable or headless setup, `scripts/deploy_ha.py` performs the same steps
through the Home Assistant API. It needs no SSH access and never writes to
`/config`:

```bash
export HA_URL=http://homeassistant.local:8123
export HA_USERNAME=your-user
export HA_PASSWORD=your-password

uv run python scripts/deploy_ha.py --list
uv run python scripts/deploy_ha.py --light light.desk_lamp --trigger
```

`--list` shows the panel text entities, lights, blueprints and automation ids.
The deploy command:

1. logs in through the normal Home Assistant login flow and keeps the
   short-lived token in memory;
2. saves the repository blueprint as `e1003/e1003_light_sync.yaml` using the
   WebSocket `blueprint/save` command;
3. creates or updates automation `e1003_light_sync_001` through
   `POST /api/config/automation/config/<id>`;
4. optionally triggers the automation once so the card is populated immediately.

The panel entities are discovered by their `_main_light_command`,
`_main_light_state` and `_main_light_value` suffixes. If more than one panel is
connected, pass part of its name with `--panel`.

The deployer is idempotent and conflict-aware: an existing automation id is
updated only when it uses the same blueprint and alias. It refuses to overwrite
an automation that was created by something else. Use `--automation-id` and
`--alias` to choose different names, `--dry-run` to inspect the payload, and
`--update-blueprint` to replace an already installed copy with the repository
version.

Use `HA_TOKEN` instead of `HA_USERNAME`/`HA_PASSWORD` when a long-lived token
is already available.

## Edit the panel entities directly

A real light and the blueprint are optional. The panel exposes editable Home
Assistant `text` entities, so its card can also be driven manually or by any
automation:

| Entity suffix | Type | Effect |
|---|---|---|
| `main_light_command` | read-only sensor | unique command published by every panel touch |
| `main_light_state` | editable text | `on`, `off`, or empty; selected ON/OFF segment |
| `main_light_value` | editable text | `0`–`100`, or empty; displayed brightness |

For a display-only preview, edit state/value from the device page. Panel
controls update the card locally and still beep. A Home Assistant light changes
only when a blueprint automation consumes the command sensor.
