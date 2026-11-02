# Architecture

## What this device is

A **dashboard terminal**, not a smart-home hub. The firmware knows how to:

1. paint a static design bitmap,
2. paint a handful of dynamic cards on top of it,
3. turn touches into Home Assistant calls.

The public factory image deliberately knows nothing about *which* light those
calls target. Home Assistant supplies the target and its display state at
runtime. The personal profile may add one fixed state adapter for convenience.

```
                         Home Assistant
       target/state/value text       optional script hook
                 │                           ▲
                 ▼                           │
   ┌─────────────────────────────────────────────────────────┐
   │ INTERACTION  runtime text + GT911 zones + HA actions     │
   │              packages/interaction.yaml                  │
   ├─────────────────────────────────────────────────────────┤
   │ UI           boot + dirty flags + refresh + rendering   │
   │              packages/ui.yaml                           │
   ├─────────────────────────────────────────────────────────┤
   │ HARDWARE     SPI/I2C + buzzer + SHT4x + PCF8563         │
   │              packages/hardware.yaml                     │
   ├─────────────────────────────────────────────────────────┤
   │ CORE         identity + ESP32-S3 platform               │
   │              packages/core.yaml                         │
   └─────────────────────────────────────────────────────────┘

   Entry-point profile owns Wi-Fi, API security and OTA:
   e1003-dashboard.yaml, e1003-release.yaml, or e1003-factory.yaml
```

## Three sources of truth, no overlap

| Concern | Source | Consumed by |
|---------|--------|-------------|
| Screen geometry, fonts, touch hit boxes | `layout/ui_layout.yaml` | `tools/layout_to_h.py` → `layout/generated/{ui_layout.h,fonts.yaml,policy.yaml}` |
| Shared identity and wiring | `packages/defaults.yaml` substitutions | every package |
| Profile network/security/default target | entry-point YAML | ESPHome merge |
| Runtime target and card text/state | Home Assistant `text` entities | `packages/interaction.yaml`, `packages/ui.yaml` |

If a number appears in two places, one of them is a bug. `tools/layout_to_h.py
--check` enforces this for the layout file: it verifies that every font, sensor
and runtime text entity referenced by the layout exists under `packages/`.

ESPHome does not require rendering and touch hit boxes to be separate. They are
separate generated data here because a painted rectangle and its usable finger
target are not always identical. Both still come from one layout file, so there
is no duplicated coordinate source.

`e1003-dashboard.yaml` is the developer entry point with private Wi-Fi,
encrypted API and OTA. `e1003-release.yaml` is the keyless USB reference
profile: it adds serial Improv, per-device identity, and plaintext-only API
access without OTA. `e1003-factory.yaml` is the public browser-install profile
with temporary captive-portal provisioning. All three share the same package
assembly and runtime interaction model. See [the provisioning guide](provisioning.md)
for the reference profile's current limitations.

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
three. Network connectivity is sampled every five seconds, but it marks the
network card dirty only when its visible state changes.

Never call `it8951.update` directly from a data source. If you add a card:

* add its geometry to `layout/ui_layout.yaml`,
* add a `ui_<card>_dirty` global in `packages/ui.yaml`,
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
| `DU` | local bounding box, fast, 2 levels | network status, environment numbers, light card, footer |

`update_interval: never` on the display component is intentional: the render
pass only runs when the firmware asks for it. The SHT4x is sampled every ten
minutes; there is no minute clock refresh. The footer time is painted during a
real render and therefore means **Last Update**, not current wall-clock time.

## Build pipeline

```
layout/ui_layout.yaml ──layout_to_h.py──┬─> layout/generated/ui_layout.h    (C++ geometry + zone table)
                                        ├─> layout/generated/fonts.yaml     (ESPHome font block)
                                        └─> layout/generated/policy.yaml    (substitutions)

assets/original.png ────png_to_h.py─────> assets/dashboard_static_v4.h      (PackBits RLE bitmap)

                        src/e1003_render.h                                  (hand-written C++ helpers)

e1003-dashboard.yaml (+ packages/) ─────> personal firmware (network OTA enabled)
e1003-release.yaml   (+ packages/) ─────> keyless USB reference firmware
e1003-factory.yaml   (+ packages/) ─────> first-install factory image
```

Both generators are idempotent and safe to run on every build; `scripts/build.py`
does exactly that.
