# Build and flash

## Toolchain

Everything is driven by [uv](https://docs.astral.sh/uv). ESPHome is pinned in
`pyproject.toml` and locked in `uv.lock`, so the build is reproducible and no
global `esphome` install is needed.

```bash
uv sync                # create/refresh .venv from uv.lock
uv run esphome version # -> 2026.9.1
```

> Do not `pip install esphome` into this project. `uv run` syncs the environment
> from `uv.lock` first and would uninstall anything that is not declared there.

Python tooling (`pillow`, `pyyaml`) lives in the `dev` dependency group so the
generators run through the same environment:

```bash
uv run python tools/layout_to_h.py
```

## Everyday commands

```bash
scripts/build.sh                 # layout check + compile
scripts/build.sh run             # compile + flash over USB + logs
scripts/build.sh upload          # compile + OTA upload
scripts/build.sh logs            # serial/OTA logs
scripts/build.sh config          # dump the merged configuration
scripts/build.sh compile -s ha_light_entity light.other   # extra build flags
```

`scripts/build.sh` picks a font that exists on this machine automatically
(Liberation Sans on Linux, Arial on Windows/macOS) and regenerates
`layout/generated/` first, so a stale header cannot be compiled by accident.

On Windows use `scripts\build.bat` (it wraps `scripts\run_esphome.bat`, which
scrubs the MSys/Git-Bash environment that breaks the ESP-IDF toolchain).

Raw ESPHome commands work too if you prefer:

```bash
uv run esphome --device /dev/ttyACM0 run e1003-dashboard.yaml
```

## First flash (USB)

These commands build the developer profile. For the maintainer-built,
credential-free release prototype, see [Serial provisioning](provisioning.md).

```bash
cp secrets.example.yaml secrets.yaml
#   wifi_ssid / wifi_password / ap_password
#   api_encryption_key  ->  python -c "import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())"
scripts/build.sh run
```

`secrets.yaml` is git-ignored and never ships. There is no OTA password: OTA
reuses the API encryption key (`encryption:` with no explicit key in
`packages/core.yaml`), which is one credential to rotate instead of two and
saves ~3.5 KB of flash.

## Subsequent updates (OTA)

```bash
scripts/build.sh upload
```

## Recovery

If the panel cannot reach Wi-Fi it starts an access point called
`E1003-Recovery` (password: `ap_password` in `secrets.yaml`, default
`change_me_ap`). Connect to it and use the captive portal to hand over your
credentials, or flash over USB.

If an OTA update ever bricks the panel, hold BOOT and re-flash over USB with
`scripts/build.sh run`.

## Build artifacts

```
.esphome/build/<device>/build/
├── firmware.factory.bin   # full image, for the first USB flash
├── firmware.ota.bin       # OTA update image
└── firmware.elf
```

`.esphome/` is a cache: deleting it costs one full rebuild (the ESP-IDF
toolchain itself is cached in the platform's ESPHome cache directory and is not
re-downloaded: `~/.cache/esphome/idf/` on Linux,
`~/Library/Caches/esphome/idf/` on macOS). An inherited `IDF_PATH` selects a
separate ESP-IDF installation; unset it when using ESPHome's managed toolchain.

## Expected footprint

| | size |
|---|---|
| RAM | ~33 % |
| Flash | ~74 % (1359 KB of 1792 KB) |

The static bitmap dominates. Dropping an unused font or shrinking the RLE
(PackBits compresses flat design areas very well) is the cheapest way to claw
space back.

## Version pins

ESPHome **2026.9.1** is required: this project uses packages, `text`/`event`
platforms, `homeassistant.action` with `capture_response`, and the
`substitutions`-aware font schema. Bump it in `pyproject.toml`, run `uv lock`,
then `uv run esphome compile e1003-dashboard.yaml` and re-check the warnings.
