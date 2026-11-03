# Home Assistant examples

The firmware does not require files from this directory. These are optional
examples for connecting one Home Assistant light to the E1003.

## Files

| File | Purpose |
|---|---|
| `blueprints/automation/e1003_light_sync.yaml` | Selects a real or demo light, tells the panel which entity to control, and mirrors its state/brightness to the e-paper card. |
| `e1003_demo.yaml` | Creates `light.e1003_demo_light`, a virtual dimmable light for testing when no physical light is available. |

## Five-minute demo

1. Enable Home Assistant packages if needed:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. Copy `e1003_demo.yaml` to Home Assistant's `config/packages/` directory and
   restart Home Assistant.
3. Confirm that `light.e1003_demo_light` appears. You can turn it on, turn it
   off, and move its brightness slider directly in Home Assistant.
4. Import `blueprints/automation/e1003_light_sync.yaml` as an automation
   blueprint.
5. Create an automation from the blueprint and select:
   - `E1003 demo light`;
   - the panel text entity ending in `Main light target`;
   - the panel text entity ending in `Main light state`;
   - the panel text entity ending in `Main light value`.

The E1003 light controls now operate the virtual light. Changes made from
either Home Assistant or the panel are mirrored to the other side.

To use a real light later, edit the automation and replace only the selected
light. The firmware and the other three selections stay unchanged.
