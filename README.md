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

**Behaviour is configuration, not firmware.** The supplied Home Assistant
blueprint maps the panel command entity to any light and mirrors state back to
the card. Re-targeting the panel means editing one automation — no rebuild, no
OTA, and no device action permission.

[简体中文说明](README.zh-CN.md)

## Features

- Full-screen static UI compiled from a design PNG into a 4bpp PackBits-RLE bitmap, painted with `GC16` at boot.
- Partial dynamic updates using `DU` waveform with `ui_refresh` debouncing to merge burst events.
- Data-driven touch zones declared in YAML rather than written as code branches.
- Tap-or-drag light slider with one brightness action on release.
- Build-time validation for geometry boundaries, fonts, and entity IDs.
- Onboard SHT4x temperature/humidity sensor and PCF8563 RTC with Home Assistant time sync.
- A screen-level physical button for full repaint and safe restart.
- Touch-driven Wi-Fi reconfiguration with an explicit two-step confirmation.
- Runtime retargeting through a Home Assistant blueprint and runtime card text
  entities without reflashing.
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
│   ├── interaction.yaml        # runtime config, GT911 and command publishing
│   ├── ha-direct-state.yaml    # optional fixed-state adapter for custom builds
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
│   └── e1003_system.h          # selective Wi-Fi reset helper
├── tools/
│   ├── layout_to_h.py          # validate and generate layout files
│   └── png_to_h.py             # convert the design PNG to a C++ header
├── scripts/
│   ├── build.py                # cross-platform build, flash, and log driver
│   ├── deploy_ha.py            # API-only HA blueprint and automation deployer
│   └── make_release.py         # assemble release and browser-install artifacts
├── ha/
│   ├── README.md               # UI-first Home Assistant setup
│   └── blueprints/automation/
│       └── e1003_light_sync.yaml
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
credentials. Add the device in Home Assistant
(**Settings → Devices & Services → ESPHome**), import the supplied blueprint,
and select:

1. the light;
2. the panel's `Main light command` sensor;
3. the panel's `Main light state` text entity;
4. the panel's `Main light value` text entity.

The blueprint performs light actions inside Home Assistant, so a replicated
device does not need **Allow the device to perform Home Assistant actions**.
See [docs/configuration.md](docs/configuration.md) for the complete runtime
interface.

## Ready-made firmware image

Every tagged release ships ready-made images and a browser installer on GitHub
Pages — plug in USB-C and flash from the page. See
[public first-install image](docs/build-and-flash.md#public-first-install-image).

Then add the device in Home Assistant and
[import the light-sync blueprint from the Home Assistant UI](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml).
The blueprint asks for the light plus the panel's command/state/value entities.
That is the complete normal-user setup; no ESPHome action permission is
required. Without a light, edit the panel's state/value text entities directly
to preview the card; no package or virtual entity is required.

## What can be changed without reflashing

| | without reflashing | how |
|---|---|---|
| which light the panel controls | ✅ | edit the imported blueprint automation |
| what a card displays | ✅ | `text..._main_light_state` / `_value` |
| advanced custom light routing | ✅ | `zone_script_hook` → an HA script |
| advanced Reachy scene actions | ✅ | `reachy_script_hook` → an HA script |
| number/position of buttons, cards, fonts | ❌ | `layout/ui_layout.yaml` + design PNG |
| pins, board, panel model | ❌ | `packages/defaults.yaml` + `-s key value` |

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

## License

MIT — see [LICENSE](LICENSE).
