# Architecture

## What this device is

A **dashboard terminal**, not a smart-home hub. The firmware knows how to:

1. paint a static design bitmap,
2. paint a handful of dynamic cards on top of it,
3. turn touches into Home Assistant calls.

It deliberately knows nothing about *which* light, switch or script those calls
target. That knowledge lives in Home Assistant and can be changed at runtime.

```
                        Home Assistant
   ┌───────────────────────────┴─────────────────────────────┐
   │  text.* knobs        event hook        state bindings   │
   └──────┬──────────────────────┬───────────────────┬───────┘
          │ Native API (set)     │ script call       │ (fallback)
          ▼                      ▲                   ▼
   ┌──────────────────────────────┴──────────────────────────┐
   │  HA BRIDGE      packages/ha-bridge.yaml                 │
   │  runtime text entities + compile-time state import      │
   ├─────────────────────────────────────────────────────────┤
   │  UI STATE       packages/ui-state.yaml                  │
   │  dirty flags + ui_refresh / ui_beep scripts             │
   ├─────────────────────────────────────────────────────────┤
   │  RENDER         packages/display.yaml                   │
   │  IT8951 lambda -- geometry from layout/generated/       │
   ├─────────────────────────────────────────────────────────┤
   │  TOUCH          packages/touch.yaml                     │
   │  GT911 -> zone table -> zone_dispatch script            │
   ├─────────────────────────────────────────────────────────┤
   │  HARDWARE       packages/hardware.yaml                  │
   │  SPI / I2C / buzzer / SHT4x / PCF8563                   │
   ├─────────────────────────────────────────────────────────┤
   │  CORE           packages/core.yaml                      │
   │  ESP32-S3 / Wi-Fi / API / OTA / boot sequence           │
   └─────────────────────────────────────────────────────────┘
```

## Three sources of truth, no overlap

| Concern | Source | Consumed by |
|---------|--------|-------------|
| Screen geometry, fonts, touch hit boxes | `layout/ui_layout.yaml` | `tools/layout_to_h.py` → `layout/generated/{ui_layout.h,fonts.yaml,policy.yaml}` |
| Device identity, wiring, compile-time HA defaults | `e1003-dashboard.yaml` substitutions | every package |
| Behaviour at runtime (targets, actions, card text) | Home Assistant `text` entities | `packages/ha-bridge.yaml`, `packages/touch.yaml` |

If a number appears in two places, one of them is a bug. `tools/layout_to_h.py
--check` enforces this for the layout file: it verifies that every font, sensor
and runtime text entity referenced by the layout actually exists under
`packages/`.

## The dirty-flag contract

Partial refresh on e-paper is expensive (a DU refresh takes hundreds of ms and
leaves ghosting if abused), so every dynamic value follows the same three-step
protocol:

```
1. source        id(ui_<card>_dirty) = true;   +   script.execute: ui_refresh
2. coalescer     ui_refresh debounces (mode: restart), then it8951.update(DU)
3. renderer      the display lambda repaints the dirty cards and clears the flag
```

`ui_refresh` exists for a reason: the SHT4x publishes temperature and humidity a
few milliseconds apart, and a Home Assistant state burst can arrive as several
API messages. `mode: restart` collapses them into one panel refresh instead of
three.

Never call `it8951.update` directly from a data source. If you add a card:

* add its geometry to `layout/ui_layout.yaml`,
* add a `ui_<card>_dirty` global in `packages/ui-state.yaml`,
* draw it in the lambda behind that flag and clear the flag.

## Coordinate spaces

Three coordinate spaces meet in this project. Mixing them up is the single most
common source of "my button is in the wrong place".

| Space | Origin | Where |
|-------|--------|-------|
| Design canvas | top-left, 1872x1404 | `layout/ui_layout.yaml` card rects and anchors |
| Touch input | as reported by GT911 with `transform.mirror_x: true` | raw `touch.x` inside the lambda |
| Zone hit box | `<canvas width> - touch.x`, i.e. already de-mirrored | `zones.*.area` |

The zone areas are the numbers that were **verified on real hardware**. If you
move a button in the design, update the zone area and re-check it on the panel;
do not "fix" the mirroring formula.

## Refresh modes

| Mode | Cost | Used for |
|------|------|----------|
| `GC16` | full panel, slow, 16 gray levels | boot paint, and every `full_update_every` refreshes to clear ghosting |
| `DU` | local bounding box, fast, 2 levels | clock, environment numbers, light card, footer |

`update_interval: never` on the display component is intentional: the render
pass only runs when the firmware asks for it. Nothing repaints on a timer.

## Build pipeline

```
layout/ui_layout.yaml ──layout_to_h.py──┬─> layout/generated/ui_layout.h    (C++ geometry + zone table)
                                        ├─> layout/generated/fonts.yaml     (ESPHome font block)
                                        └─> layout/generated/policy.yaml    (substitutions)

assets/original.png ────png_to_h.py─────> assets/dashboard_static_v4.h      (PackBits RLE bitmap)

                        src/e1003_render.h                                  (hand-written C++ helpers)

e1003-dashboard.yaml (+ packages/) ─────> esphome compile ──> firmware.ota.bin
```

Both generators are idempotent and safe to run on every build; `scripts/build.sh`
does exactly that.