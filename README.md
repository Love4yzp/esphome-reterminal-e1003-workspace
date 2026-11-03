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
- System-level physical buttons for full repaint, safe restart, and Wi-Fi reconfiguration.
- Runtime retargeting of controls and card text via Home Assistant `text` entities without reflashing.
- `uv`-managed, lockfile-pinned toolchain; one cross-platform build driver
- Fonts vendored in `assets/fonts/` (SIL OFL 1.1): no host font required, and
  identical glyph metrics on Linux, Windows and macOS

## Project structure

```
.
├── e1003-dashboard.yaml        # canonical firmware entry point
├── e1003-base.yaml             # shared package assembly
├── packages/
│   ├── defaults.yaml           # identity, pins, fonts, and shared defaults
│   ├── core.yaml               # identity and ESP32-S3 platform
│   ├── hardware.yaml           # SPI/I2C, buzzer, SHT4x, PCF8563
│   ├── ui.yaml                 # boot, dirty flags, refresh and rendering
│   ├── interaction.yaml        # runtime config, GT911 and HA actions
│   ├── ha-direct-state.yaml    # optional fixed-target adapter for custom builds
│   └── ha-pull.yaml            # optional: device polls HA for JSON
├── layout/
│   ├── ui_layout.yaml          # zones, cards, fonts, palette, and refresh policy
│   └── generated/              # generated header, fonts, and policy
├── assets/
│   ├── original.png            # static UI design source
│   ├── dashboard_static_v4.h   # generated PackBits-RLE bitmap
│   └── fonts/                  # vendored Liberation Sans fonts
├── src/
│   ├── e1003_render.h          # bitmap decoder and render helpers
│   └── e1003_system.h          # system-button helpers and selective Wi-Fi reset
├── tools/
│   ├── layout_to_h.py          # validate and generate layout files
│   └── png_to_h.py             # convert the design PNG to a C++ header
├── scripts/
│   ├── build.py                # cross-platform build, flash, and log driver
│   └── make_release.py         # assemble release and browser-install artifacts
├── ha/
│   ├── blueprints/automation/
│   │   └── e1003_light_sync.yaml
│   └── e1003_dashboard.yaml    # sample HA package and pull snapshot
├── web/
│   └── install.html            # browser installer template
├── docs/                       # architecture, configuration, layout, HA, and build guides
├── .github/workflows/ci.yml    # validation, build, release, and Pages deployment
├── pyproject.toml              # pinned Python and ESPHome dependencies
├── uv.lock                     # reproducible toolchain lockfile
└── AGENTS.md                   # repository rules for coding agents
```

See [docs/architecture.md](docs/architecture.md) for the detailed firmware architecture and package breakdown.

The source build and the public browser-install image contain no Wi-Fi
credentials, AP password, API key, or Home Assistant entity ID. On first boot
the panel starts an open setup AP; users join it and open `192.168.4.1`.
Improv Serial remains available as an additional USB setup path in the same
firmware.

## Developer quick start

Install dependencies:

```bash
uv sync
```

Then compile and flash the credential-free default firmware:

```bash
uv run python scripts/build.py run
```

The build driver regenerates layout headers before compiling and runs identically
on Linux, Windows, and macOS. See [docs/build-and-flash.md](docs/build-and-flash.md)
for detailed build and flashing instructions.

After flashing, join the open Wi-Fi network whose name starts with
`reterminal-e1003-`, then open `192.168.4.1` to enter the destination Wi-Fi
credentials. Then add the device in Home Assistant
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

## Ready-made firmware image

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
| custom light-button routing | ✅ | `zone_script_hook` → an HA script |
| Reachy scene actions | ✅ | `reachy_script_hook` → an HA script |
| number/position of buttons, cards, fonts | ❌ | `layout/ui_layout.yaml` + design PNG |
| pins, board, panel model, compile-time default target | ❌ | `packages/defaults.yaml` + `-s key value` |

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

### Physical buttons

| Button | Gesture | Function |
|---|---|---|
| Green button | Press | Fully repaint the Dashboard |
| Green button | Hold for 3 seconds | Safely restart the device |
| Both white buttons | Hold for 5 seconds | Reconfigure Wi-Fi |

## License

MIT — see [LICENSE](LICENSE).
