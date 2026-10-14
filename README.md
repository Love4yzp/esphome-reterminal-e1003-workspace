# reTerminal E1003 e-paper dashboard for Home Assistant

An Espressif/ESPHome firmware template for the **reTerminal E1003** e-paper panel (1872×1404, 16-level grayscale, IT8951) on a **Seeed XIAO ESP32-S3**: a full-screen design bitmap painted as the static UI, dynamic cards refreshed individually, and touch zones that communicate with Home Assistant.

[简体中文说明](README.zh-CN.md)

## Features

- Full-screen static UI compiled from a design PNG into a 4bpp PackBits-RLE bitmap, painted with `GC16` at boot.
- Partial dynamic updates using `DU` waveform with `ui_refresh` debouncing to merge burst events.
- Data-driven touch zones declared in YAML rather than written as code branches.
- Build-time validation for geometry boundaries, fonts, and entity IDs.
- Onboard SHT4x temperature/humidity sensor and PCF8563 RTC with Home Assistant time sync.
- Runtime retargeting of controls and card text via Home Assistant `text` entities without reflashing.

## Project structure

```
e1003-dashboard.yaml            # Main firmware entry point (the only file to flash)
layout/                         # UI layout, coordinates, touch zones, and fonts
packages/                       # ESPHome packages (core, hardware, display, touch, ha-bridge)
src/                            # C++ helpers such as bitmap decoding
assets/                         # Design PNG and generated headers
tools/                          # Layout compiler and bitmap conversion scripts
ha/                             # Home Assistant package, routing script, and automations
docs/                           # Detailed documentation
scripts/                        # Build scripts for Linux, macOS, and Windows
```

See [docs/architecture.md](docs/architecture.md) for the detailed firmware architecture and package breakdown.

## Quick start

First, install dependencies and prepare your local configuration file:

```bash
uv sync
cp secrets.example.yaml secrets.yaml
```

Edit `secrets.yaml` to fill in your Wi-Fi credentials, fallback hotspot password, and ESPHome API encryption key.

Then compile and flash the firmware:

```bash
scripts/build.sh run
```

`scripts/build.sh` automatically runs `tools/layout_to_h.py` to generate layout headers before compiling, so there is no need to run the layout tool manually.

The commands above are for Linux and macOS. On Windows, run `scripts/build.bat run`. See [docs/build-and-flash.md](docs/build-and-flash.md) for detailed build and flashing instructions.

After flashing, add the device in Home Assistant (**Settings → Devices & Services → ESPHome**) and point a control at your target entity:

```yaml
action: text.set_value
target:
  entity_id: text.e1003_smart_workspace_main_light_target
data:
  value: light.desk_lamp
```

Changes take effect immediately without recompilation. See [docs/configuration.md](docs/configuration.md) for available runtime settings.

## What can be changed without reflashing

| Target change | Without reflashing | Mechanism |
|---|:---:|---|
| Which entity a button controls | ✅ | `text..._main_light_target` |
| Which action percentage buttons call | ✅ | `text..._main_light_action` |
| What a card displays | ✅ | `text..._main_light_state` / `_value` |
| Clock / banner text (weather, calendar) | ✅ | `text..._clock_message` |
| What every button does in general | ✅ | `zone_script_hook` → HA script |
| Number or position of buttons, cards, fonts | ❌ | `layout/ui_layout.yaml` + design PNG |
| Pins, board model, panel model, fallback bindings | ❌ | `e1003-dashboard.yaml` + `-s key value` |

## Documentation

| Goal | Docs |
|---|---|
| Re-target controls and drive the panel from HA | [docs/configuration.md](docs/configuration.md) |
| Move a button, add a card, or change artwork | [docs/ui-layout.md](docs/ui-layout.md) |
| Layers, dirty-flag contract, and refresh protocol | [docs/architecture.md](docs/architecture.md) |
| Home Assistant setup, routing script, and push/pull recipes | [docs/ha-integration.md](docs/ha-integration.md) |
| Build, flash, troubleshooting, and toolchain setup | [docs/build-and-flash.md](docs/build-and-flash.md) |
| Agent guidelines and repository conventions | [AGENTS.md](AGENTS.md) |

## Hardware

| Component | Specification |
|---|---|
| Panel | reTerminal E1003, IT8951, 1872×1404, 16 gray levels, SPI |
| MCU | Seeed XIAO ESP32-S3, octal PSRAM, Arduino framework |
| Touch | GT911 (I²C), buzzer on LEDC for feedback |
| Sensors | SHT4x (temperature/humidity), PCF8563 (RTC + battery backup) |

Pin assignments are substitutions in `e1003-dashboard.yaml`.
