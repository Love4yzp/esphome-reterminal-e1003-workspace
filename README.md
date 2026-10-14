# reTerminal E1003 e-paper dashboard for Home Assistant

An Espressif/ESPHome firmware template for the **reTerminal E1003** e-paper
panel (1872×1404, 16-level grayscale, IT8951) on a **Seeed XIAO ESP32-S3**:
a design bitmap painted as the static UI, a few dynamic cards refreshed
individually, and touch zones that talk to Home Assistant.

Two ideas shape the whole repository:

**The design is a source file, not code.** Screen geometry, fonts and touch hit
boxes live in [`layout/ui_layout.yaml`](layout/ui_layout.yaml) and are compiled
into a C++ header by `tools/layout_to_h.py`. No pixel number is allowed to appear
in the ESPHome packages.

**Behaviour is configuration, not firmware.** Which light a button controls,
what action it calls, and what the cards display are plain Home Assistant `text`
entities. Re-targeting the panel is a service call — no rebuild, no OTA.

[简体中文说明](README.zh-CN.md)

## Features

- Static UI from a single design PNG → 4bpp PackBits-RLE bitmap (≈250 KB)
- Dirty-flag partial refresh: one `GC16` full paint at boot, local `DU` repaints
  afterwards, debounced so bursts collapse into one panel update
- Touch zones as a **data table**: add a button by editing YAML, not an `if` chain
- All geometry validated at build time (bounds, missing fonts, undeclared ids)
- Onboard SHT4x temperature/humidity and PCF8563 RTC, time synced from HA
- Runtime re-targetable controls, card overrides, and an optional HA hook script
- Optional push/pull channels so the panel can display state of entities the
  firmware has never heard of
- `uv`-managed, lockfile-pinned toolchain; one build script for Linux/macOS/Windows

## Project structure

```
e1003-dashboard.yaml            # ← the only file you flash (thin package assembly)
├── layout/
│   ├── ui_layout.yaml          # ← single source of truth: zones, cards, fonts, palette
│   └── generated/              # ← generated: ui_layout.h, fonts.yaml, policy.yaml
├── packages/
│   ├── core.yaml               # ESP32-S3, Wi-Fi, API, OTA, boot sequence
│   ├── hardware.yaml           # SPI/I2C, buzzer, SHT4x, PCF8563
│   ├── display.yaml            # IT8951 panel + the render pass
│   ├── ui-state.yaml           # dirty flags + ui_refresh / ui_beep / ui_repaint
│   ├── touch.yaml              # GT911 + generic zone dispatch
│   ├── ha-bridge.yaml          # ← the runtime (no-recompile) configuration layer
│   └── ha-pull.yaml            # optional: device polls HA for JSON
├── src/e1003_render.h          # C++ helpers (bitmap decoder)
├── assets/                     # design PNG + generated bitmap header
├── tools/                      # png_to_h.py, layout_to_h.py
├── ha/e1003_dashboard.yaml     # Home Assistant package: routing script + examples
├── docs/                       # architecture, configuration, layout, HA, build
└── scripts/                    # build.sh / build.bat / run_esphome.bat
```

## Quick start

```bash
uv sync                                            # toolchain from uv.lock
cp secrets.example.yaml secrets.yaml               # Wi-Fi, AP hotspot, API key

uv run python tools/layout_to_h.py                 # regenerate geometry header
scripts/build.sh run                               # compile + flash + logs
```

Then add the device in Home Assistant (**Settings → Devices & Services → ESPHome**)
and point the card at one of your lights:

```yaml
action: text.set_value
target: { entity_id: text.e1003_smart_workspace_main_light_target }
data: { value: light.desk_lamp }
```

Nothing was recompiled. See **[docs/configuration.md](docs/configuration.md)** for
everything that can be changed this way.

## What can be changed without reflashing

| | without reflashing | how |
|---|---|---|
| which entity a button controls | ✅ | `text..._main_light_target` |
| which action the % buttons call | ✅ | `text..._main_light_action` |
| what a card displays | ✅ | `text..._main_light_state` / `_value` |
| clock/banner text (weather, calendar) | ✅ | `text..._clock_message` |
| what every button does, in general | ✅ | `zone_script_hook` → an HA script |
| number/position of buttons, cards, fonts | ❌ | `layout/ui_layout.yaml` + design PNG |
| pins, board, panel model, fallback bindings | ❌ | `e1003-dashboard.yaml` + `-s key value` |

The dividing line is deliberate: **behaviour is runtime, design is compile-time.**
On e-paper the artwork *is* the firmware.

## Adapting this template

| Goal | Docs |
|------|------|
| Re-target controls, drive the panel from HA | [docs/configuration.md](docs/configuration.md) |
| Move a button, add a card, swap the artwork | [docs/ui-layout.md](docs/ui-layout.md) |
| Understand the layers and the refresh protocol | [docs/architecture.md](docs/architecture.md) |
| Home Assistant setup, hook script, push/pull recipes | [docs/ha-integration.md](docs/ha-integration.md) |
| Build, flash, recover, tune the toolchain | [docs/build-and-flash.md](docs/build-and-flash.md) |
| Hand the repo to an AI agent | [CLAUDE.md](CLAUDE.md) |

## Hardware

| | |
|---|---|
| Panel | reTerminal E1003, IT8951, 1872×1404, 16 gray levels, SPI |
| MCU | Seeed XIAO ESP32-S3, octal PSRAM, Arduino framework |
| Touch | GT911 (I²C), buzzer on LEDC for feedback |
| Sensors | SHT4x (temperature/humidity), PCF8563 (RTC + battery backup) |

Pin assignments are substitutions in `e1003-dashboard.yaml`.

## License

MIT — see [LICENSE](LICENSE).