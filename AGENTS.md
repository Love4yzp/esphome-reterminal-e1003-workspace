# Repository instructions

These instructions apply throughout this repository.

## Project and scope

ESPHome firmware for a reTerminal E1003 e-paper dashboard on a Seeed XIAO ESP32-S3. A design PNG provides the static UI; dynamic cards update via partial refreshes; GT911 touch zones call Home Assistant actions.

Keep control targets, actions, and card text configurable at runtime. The Home Assistant package in `ha/` is a sample, not a supported integration. Design tooling, MQTT, a web server, and LVGL are out of scope.

## Where to make changes

| Concern | File |
|---|---|
| Device identity, pins, fonts, timezone, compile-time defaults | `e1003-dashboard.yaml` |
| Screen geometry, font sizes, touch zones, cards, refresh policy | `layout/ui_layout.yaml` |
| Runtime text settings, Home Assistant state imports | `packages/ha-bridge.yaml` |
| Touch dispatch, control bindings | `packages/touch.yaml` |
| Dirty flags, refresh scripts | `packages/ui-state.yaml` |
| Panel rendering, reusable drawing helpers | `packages/display.yaml`, `src/e1003_render.h` |

Read the relevant guide when changing these areas:

- Module boundaries, refresh behavior: [docs/architecture.md](docs/architecture.md)
- Buttons, cards, fonts, artwork: [docs/ui-layout.md](docs/ui-layout.md)
- Runtime settings and defaults: [docs/configuration.md](docs/configuration.md)
- HA routing, hooks, push/pull recipes: [docs/ha-integration.md](docs/ha-integration.md)
- Toolchain, flashing, recovery: [docs/build-and-flash.md](docs/build-and-flash.md)

## Layout and generated files

Define screen coordinates, font sizes, and hit boxes in `layout/ui_layout.yaml`. Use generated `e1003::` constants in rendering code; do not hardcode pixel numbers in `packages/`.

Edit the source layout and regenerate `layout/generated/` with:

```bash
uv run python tools/layout_to_h.py
```

Include the generated C++ and YAML files with the source change so direct ESPHome builds can use them without first running the layout generator. Do not edit generated files by hand.

When changing artwork, regenerate the bitmap header:

```bash
uv run python tools/png_to_h.py assets/original.png assets/dashboard_static_v4.h
```

Verify touch zones on physical hardware after changing artwork or button positions; hit boxes cannot be derived from the PNG alone.

## Rendering and touch

Dynamic card updates must follow this contract:

1. The data source sets `ui_<card>_dirty` and calls `script.execute: ui_refresh`.
2. `ui_refresh` debounces burst updates and triggers the partial panel refresh.
3. The display lambda repaints the dirty card and clears its dirty flag.

Never call `it8951.update` directly from a data source. When adding a dynamic card: define its rectangle in the layout, declare its dirty flag in `packages/ui-state.yaml`, and render it in both full and partial draw paths. Clear the card's bounding box before drawing new text.

Preserve the hardware-verified touch conversion `x = <canvas width> - touch.x` and `transform.mirror_x: true` on the display and touchscreen. Touch zone coordinates use this converted space. Change these only when the task calls for correcting the transform and real-panel testing is available.

Add touch zones to the layout's `zones:` table. A new control also requires its four text entity IDs in `runtime.controls`, declarations in `packages/ha-bridge.yaml`, and one row in the `BINDINGS` table in `packages/touch.yaml` (ESPHome resolves `id()` at compile time).

## Runtime configuration and style

Put compile-time entity IDs, action names, and display defaults in entry-point substitutions. Expose runtime settings as `text` entities in `packages/ha-bridge.yaml` rather than hardcoding them in packages.

For a new runtime setting, use a `cfg_<thing>` ID, `optimistic: true`, `restore_value: true`, and an appropriate `initial_value`. Reference it from the layout's `runtime:` section where applicable so `layout_to_h.py` can validate its ID. Empty overrides must preserve the existing fallback behavior. Document the setting, its default, and its fallback in `docs/configuration.md`.

Keep `packages/*.yaml` declarative; move substantial reusable logic into `src/*.h` or scripts. Use short comments to explain reasons and keep architecture explanations in `docs/architecture.md`. Write code and documentation in English; `README.zh-CN.md` is the Chinese entry point.

## Verification

Install dependencies with `uv sync`. Run checks matching the files changed:

| Change type | Required verification |
|---|---|
| Documentation only | Validate local Markdown links and file references; run `git diff --check`. Firmware compilation is unnecessary. |
| Layout or `tools/layout_to_h.py` | Run `uv run python tools/layout_to_h.py --check`, regenerate outputs, inspect git diff, and run firmware checks below. |
| Firmware YAML, C++ headers, or artwork | Run `scripts/build.sh config` and `scripts/build.sh compile`. |

`layout_to_h.py --check` validates geometry and referenced IDs without checking whether generated files are up to date on disk. `scripts/build.sh` automatically regenerates layout files before running ESPHome. For Windows commands (`scripts/build.bat`), see [docs/build-and-flash.md](docs/build-and-flash.md).

Pass criteria:

- `scripts/build.sh config` must succeed and report `Configuration is valid!`.
- `scripts/build.sh compile` must succeed and report `Successfully compiled program.`.
- No new compiler warnings.
- No unexplained growth in RAM or flash usage compared with the prior build.

Report the checks run and any checks blocked by missing dependencies or local configuration. Touch accuracy, ghosting, and display mirroring require a real panel; compilation alone does not verify them.
