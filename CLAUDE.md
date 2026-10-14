# CLAUDE.md — AI adaptation guide

Read this before changing anything. It encodes the rules that keep this project
from rotting back into a pile of hardcoded numbers.

## 1. What this project is

ESPHome firmware for the reTerminal E1003 e-paper panel (1872×1404, IT8951,
16 gray levels) on a XIAO ESP32-S3:

- **static UI** = one design PNG → 4bpp PackBits-RLE bitmap
- **dynamic parts** = a few cards (clock, environment, light, footer) with dirty
  flags and partial `DU` refresh
- **interaction** = GT911 touch → a *data-driven* zone table → Home Assistant
  call, plus a buzzer beep

It is a **dashboard terminal**. It must never learn which light it controls at
compile time if that can be decided at runtime instead.

## 2. Iron rules

1. **No pixel number, font size or hit box inside `packages/`.** They live in
   `layout/ui_layout.yaml` and reach the code through
   `layout/generated/ui_layout.h`. If you need a new coordinate, add a field to
   the layout and re-run `tools/layout_to_h.py`.
2. **No device-specific hardcoding.** Entity ids, action names and display text
   are either substitutions in `e1003-dashboard.yaml` or runtime `text` entities
   in `packages/ha-bridge.yaml`. There is no third option.
3. **Never call `it8951.update` from a data source.** Set `ui_<card>_dirty` and
   call `script.execute: ui_refresh` (it debounces; the sensors fire in bursts).
4. **Every dynamic card follows the three-step contract**: source sets the dirty
   flag → `ui_refresh` issues the partial update → the display lambda repaints
   and clears the flag. Missing any step = a card that silently never updates.
5. **`layout/generated/` is generated.** Never hand-edit it; it will be
   overwritten. Commit it (so `esphome compile` works without Python) but always
   change the source layout file.
6. **Do not touch mirroring.** `x = <canvas width> - touch.x` plus
   `transform.mirror_x: true` on both display and touchscreen is the combination
   verified on real hardware. The zone areas are expressed in that converted
   space.

## 3. Layout of the code

| File | Owns | Change it when |
|------|------|----------------|
| `e1003-dashboard.yaml` | identity, pins, fonts, timezone, compile-time HA defaults | new board, new default target |
| `packages/core.yaml` | ESP32, Wi-Fi, API, OTA, boot paint | boot sequence, network |
| `packages/hardware.yaml` | SPI/I2C, buzzer, SHT4x, PCF8563 | new sensor or pin |
| `packages/display.yaml` | IT8951 + the render pass | drawing new content |
| `packages/ui-state.yaml` | globals, `ui_refresh`/`ui_beep`/`ui_repaint` | new dirty flag |
| `packages/touch.yaml` | GT911 + zone dispatch + control bindings | new control (not new button!) |
| `packages/ha-bridge.yaml` | runtime `text` knobs, HA state import, API actions | new runtime knob |
| `packages/ha-pull.yaml` | optional HA→JSON pull channel | rarely |
| `layout/ui_layout.yaml` | **all geometry, fonts, zones, controls** | any visual change |
| `tools/layout_to_h.py` | layout → C++/YAML | new layout feature |
| `tools/png_to_h.py` | design PNG → RLE bitmap | new artwork |
| `src/e1003_render.h` | hand-written C++ helpers | new reusable drawing primitive |
| `ha/e1003_dashboard.yaml` | HA-side routing, examples | HA-facing recipes |
| `docs/*` | everything a human needs | behaviour change |

## 4. Recipes

### Add a touch button (no code change)

Add a `zones:` entry to `layout/ui_layout.yaml` with its `area` and `op`, then
`uv run python tools/layout_to_h.py`. The dispatch loop picks it up. If the
button belongs to a new control, also:

1. add the control to `runtime.controls` (four text entity ids),
2. declare those `text:` entities in `packages/ha-bridge.yaml`,
3. add **one row** to the `BINDINGS` table in `packages/touch.yaml`.

Step 3 is unavoidable: ESPHome's `id()` is resolved at compile time, so the
control-id → text-entity mapping cannot be data.

### Add a dynamic card

1. `cards:` entry in the layout (clear rect, anchor, align, font, format).
2. `ui_<card>_dirty` global in `packages/ui-state.yaml`.
3. `draw_<card>()` in the `display.yaml` lambda, using only
   `e1003::<CONSTANT>` names.
4. Call it from both the full-redraw and the partial path, and clear the flag.

### Make something runtime-configurable

1. Add a `text:` entity in `packages/ha-bridge.yaml` (id `cfg_<thing>`,
   `optimistic: true`, `restore_value: true`, sane `initial_value`).
2. Reference it from `layout/ui_layout.yaml` (`runtime:` section) so the
   generator validates that it exists.
3. Consume it in the lambda with a **fallback**: empty override = previous
   compile-time behaviour. Never make an empty entity mean "show nothing".
4. Document it in `docs/configuration.md`'s entity table.

### Swap the artwork

`uv run python tools/png_to_h.py assets/original.png assets/dashboard_static_v4.h`
then re-check every zone area on the panel — the numbers are not derivable from
the PNG.

## 5. Build and verify

```bash
uv sync
scripts/build.sh compile     # regenerates the layout, then compiles
scripts/build.sh config      # dump the merged config, catches schema damage
```

Checklist before claiming a change works:

- [ ] `uv run python tools/layout_to_h.py --check` passes
- [ ] `scripts/build.sh config` reports `Configuration is valid!`
- [ ] `scripts/build.sh compile` ends with `Successfully compiled program.`
- [ ] no new compiler warnings
- [ ] flash/RAM did not regress for no reason (baseline: RAM ≈ 33 %, Flash ≈ 74 %)
- [ ] every new runtime knob is documented, with its default and its fallback

Hardware behaviour (touch hits the right button, no ghosting) can only be
verified on a real panel. Say so instead of guessing.

## 6. Style

- Comments explain *why*, in the imperative, and stay short. The generated
  header and the dirty-flag protocol are the only things that need long
  explanations, and those belong in `docs/architecture.md`.
- English in code and docs; `README.zh-CN.md` is the Chinese entry point.
- Keep `packages/*.yaml` declarative. When logic exceeds a screenful, it
  belongs in `src/*.h` or in a script, not in a lambda.

## 7. Out of scope

- The Home Assistant side is a *sample package*, not a supported integration.
- No design tooling: the PNG is the design.
- No MQTT, no web server, no LVGL — the panel is a picture with a few fields.