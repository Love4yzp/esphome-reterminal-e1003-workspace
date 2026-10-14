# Editing the layout

`layout/ui_layout.yaml` is the only place screen geometry is allowed to exist.
Nothing in `packages/` contains a pixel number.

```bash
uv run python tools/layout_to_h.py            # validate + regenerate
uv run python tools/layout_to_h.py --check    # validate only (CI friendly)
uv run python tools/layout_to_h.py --print    # print the zone / entity map
```

The generator writes three files under `layout/generated/` (committed, so a
plain `esphome compile` works without Python):

| File | Contents | Consumed by |
|------|----------|-------------|
| `ui_layout.h` | `Rect`/`Point` constants, palette, zone table | the display lambda, the touch lambda |
| `fonts.yaml` | the ESPHome `font:` block | `packages/display.yaml` |
| `policy.yaml` | canvas size and refresh policy as substitutions | `e1003-dashboard.yaml` |

## Validation

The generator fails the build on the mistakes that actually happen:

* a hit box or card that extends past the canvas,
* a font that is referenced but not declared (or declared but never used — each
  font bakes its whole glyph set into flash),
* a field missing a font, alignment or anchor (gauges excepted),
* a `sensor:`, `text:` or `control:` id that does not exist under `packages/`,
* duplicate zone or field ids,
* an unknown `op`, `align` or `source`.

The last two checks are what stop the layout and the firmware from drifting
apart: rename a text entity in `packages/ha-bridge.yaml` and the generator tells
you immediately instead of the compiler failing 40 seconds later.

## Anatomy

```yaml
zones:                                   # touch hit boxes
  - id: light_50
    label: "Main light 50%"              # documentation only
    control: main_light                  # must exist in runtime.controls
    area: { x1: 1359, y1: 711, x2: 1478, y2: 784 }
    op: call                             # toggle | call | script
    data: { brightness_pct: "50" }       # passed to the HA hook, and to `call`

cards:                                   # dynamic regions
  light:
    control: main_light
    fields:
      - id: light_value
        source: light_value              # clock | rtc | sensor | text | light_state | light_value
        clear: { x: 1387, y: 673, w: 100, h: 36 }   # erased to white before redraw
        anchor: { x: 1395, y: 673 }
        align: top_left
        font: font_medium
        format: "%d%%"
```

`clear` is not cosmetic: the partial refresh only repaints the union of the
regions the lambda touches, so a card that forgets to clear keeps the previous
value's pixels around the new glyphs.

## Adding a touch button

1. Draw it into the design PNG.
2. Regenerate the bitmap:
   `uv run python tools/png_to_h.py assets/original.png assets/dashboard_static_v4.h`
3. Add a `zones:` entry with its hit box.
4. `uv run python tools/layout_to_h.py`
5. Rebuild and flash. The touch code needs no change — the zone table is data.

If the new button belongs to a **new** control, add that control to
`runtime.controls` first (with its four text entity ids), declare those entities
in `packages/ha-bridge.yaml`, and add one row to the `BINDINGS` table in
`packages/touch.yaml`. That row is the only code change, and it exists because
`id()` in ESPHome is resolved at compile time.

## Adding a dynamic card

1. Add the card and its fields to `cards:`.
2. Add a `ui_<card>_dirty` global (and a `draw_<card>` function) — see
   `docs/architecture.md` for the three-step dirty-flag protocol.
3. If the source is a new sensor, declare it in `packages/hardware.yaml` and
   reference it from the layout so the generator can check it exists.

## Finding coordinates

The generator's `--print` output and the design file are the tools; there is no
GUI editor. A quick way to read a rectangle off the design is any image viewer
that shows a cursor position. Remember the two coordinate spaces:

* card `clear`/`anchor` are in **design canvas** coordinates,
* zone `area` is in **`<canvas width> - touch.x`** coordinates.

## Changing the artwork resolution

`png_to_h.py` scales whatever you give it to 1872x1404 and quantizes to 16 gray
levels (`WHITE_CLIP = 220` forces near-white pixels to pure white, which keeps
the RLE small). If you change the canvas size, update `meta.canvas` in the layout
file and the `display:` model/spi setup in `packages/display.yaml`, then re-check
every zone area on the real panel.