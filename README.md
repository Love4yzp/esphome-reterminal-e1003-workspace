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

**Behaviour is configuration, not firmware.** Which light a button controls and
what the cards display are Home Assistant `text` entities. Re-targeting the
panel is a service call — no rebuild, no OTA.

[简体中文说明](README.zh-CN.md)

## Features

- Full-screen static UI compiled from a design PNG into a 4bpp PackBits-RLE bitmap, painted with `GC16` at boot.
- Partial dynamic updates using `DU` waveform with `ui_refresh` debouncing to merge burst events.
- Data-driven touch zones declared in YAML rather than written as code branches.
- Build-time validation for geometry boundaries, fonts, and entity IDs.
- Onboard SHT4x temperature/humidity sensor and PCF8563 RTC with Home Assistant time sync.
- Runtime retargeting of controls and card text via Home Assistant `text` entities without reflashing.
- `uv`-managed, lockfile-pinned toolchain; one cross-platform build driver
- Fonts vendored in `assets/fonts/` (SIL OFL 1.1): no host font required, and
  identical glyph metrics on Linux, Windows and macOS

## Project structure

```
e1003-dashboard.yaml            # personal profile: private Wi-Fi/API/OTA
e1003-release.yaml              # keyless USB reference profile
e1003-factory.yaml              # public browser-install profile
e1003-base.yaml                 # shared package assembly
├── layout/
│   ├── ui_layout.yaml          # ← single source of truth: zones, cards, fonts, palette
│   └── generated/              # ← generated: ui_layout.h, fonts.yaml, policy.yaml
├── packages/
│   ├── core.yaml               # identity and ESP32-S3 platform
│   ├── hardware.yaml           # SPI/I2C, buzzer, SHT4x, PCF8563
│   ├── ui.yaml                 # boot, dirty flags, refresh and rendering
│   ├── interaction.yaml        # runtime config, GT911 and HA actions
│   ├── ha-direct-state.yaml    # optional personal-profile state adapter
│   └── ha-pull.yaml            # optional: device polls HA for JSON
├── src/e1003_render.h          # C++ helpers (bitmap decoder)
├── assets/                     # design PNG, generated bitmap header, vendored fonts
├── tools/                      # png_to_h.py, layout_to_h.py
├── ha/e1003_dashboard.yaml     # Home Assistant package: routing script + examples
├── docs/                       # architecture, configuration, layout, HA, build
└── scripts/                    # build.py (one entry point for Linux/Windows/macOS)
```

See [docs/architecture.md](docs/architecture.md) for the detailed firmware architecture and package breakdown.

The [reference setup](docs/provisioning.md) uses one maintainer-built USB image
and runtime Wi-Fi/light configuration. The reference API uses no key and has no encryption
option. The developer profile keeps its separate encrypted configuration. App users do not edit YAML or compile firmware.
The developer quick start below is for building firmware from source.

## Developer quick start

First, install dependencies and prepare your local configuration file:

```bash
uv sync
cp secrets.example.yaml secrets.yaml
```

Edit `secrets.yaml` to fill in your Wi-Fi credentials, fallback hotspot password, and ESPHome API encryption key.

Then compile and flash the firmware:

```bash
uv run python scripts/build.py run
```

The build driver regenerates layout headers before compiling and runs identically
on Linux, Windows, and macOS. See [docs/build-and-flash.md](docs/build-and-flash.md)
for detailed build and flashing instructions.

After flashing, add the device in Home Assistant
(**Settings → Devices & Services → ESPHome**) and point a control at your
target entity:

```yaml
action: text.set_value
target:
  entity_id: text.e1003_smart_workspace_main_light_target
data:
  value: light.desk_lamp
```

Changes take effect immediately without recompilation. See [docs/configuration.md](docs/configuration.md) for available runtime settings.

## Ready-made factory image

Every tagged release ships ready-made images and a browser installer on GitHub
Pages — plug in USB-C and flash from the page. See
[public first-install image](docs/build-and-flash.md#public-first-install-image).

Then add the device in Home Assistant and import
`ha/blueprints/automation/e1003_light_sync.yaml`. The blueprint asks for the
panel's target/state/value text entities and the light to control.

## What can be changed without reflashing

| | without reflashing | how |
|---|---|---|
| which entity a button controls | ✅ | `text..._main_light_target` |
| what a card displays | ✅ | `text..._main_light_state` / `_value` |
| clock/banner text (weather, calendar) | ✅ | `text..._clock_message` |
| what every button does, in general | ✅ | `zone_script_hook` → an HA script |
| number/position of buttons, cards, fonts | ❌ | `layout/ui_layout.yaml` + design PNG |
| pins, board, panel model, personal default target | ❌ | `packages/defaults.yaml` + `-s key value` |

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

Pin assignments are substitutions in `packages/defaults.yaml`.

## License

MIT — see [LICENSE](LICENSE).
