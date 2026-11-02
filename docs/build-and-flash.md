# Build and flash

## Public first-install image

Tagged releases are built from `e1003-factory.yaml`. The factory image contains:

- no station Wi-Fi SSID or password;
- no pre-shared ESPHome API key;
- Improv Serial provisioning over USB;
- a captive-portal fallback hotspot;
- a 15-minute provisioning window;
- no persistent ESPHome native OTA service.

Use the browser installer with a USB-C data cable, or flash
`firmware.factory.bin` at offset 0 with esptool. After flashing, enter Wi-Fi in
the Improv dialog. If that is unavailable, join the hotspot whose name starts
with `reterminal-e1003-ha-` using the public password shown on the installer
page, then open `192.168.4.1`.

Home Assistant provisions a unique API encryption key when the device is added
for the first time. Import the supplied light-sync blueprint afterward to
select the user's light and keep the card synchronized.

ESPHome's captive portal automatically includes a web updater. In this profile
its HTTP listener stops when the provisioning window closes, together with the
fallback hotspot. The release carries `firmware.ota.bin` for that temporary
recovery path and for developers, but routine updates should use USB or a
personal profile with encrypted native OTA.

## Personal development profile

Create `secrets.yaml` from `secrets.example.yaml`:

```bash
cp secrets.example.yaml secrets.yaml
```

Set:

- `wifi_ssid`
- `wifi_password`
- `ap_password`
- `api_encryption_key`

Then:

```bash
uv sync
uv run python scripts/build.py run
```

`e1003-dashboard.yaml` enables encrypted network OTA and loads
`packages/ha-direct-state.yaml` for its fixed `default_light_target`.

## Keyless USB reference profile

`e1003-release.yaml` is the reference flow documented in
[Serial provisioning](provisioning.md). It contains no personal Wi-Fi
credentials, uses Improv Serial, exposes a plaintext-only ESPHome API, and has
no OTA service. Build it with:

```bash
CONFIG=e1003-release.yaml uv run python scripts/build.py compile
```

## Minimal validation commands

Regenerate and validate the layout:

```bash
uv run python tools/layout_to_h.py
uv run python tools/layout_to_h.py --check
```

Validate each ESPHome profile without compiling firmware:

```bash
uv run esphome config e1003-dashboard.yaml
uv run esphome config e1003-release.yaml
uv run esphome config e1003-factory.yaml
```

Full compilation is reserved for release work or changes that affect C++,
dependencies, board settings or generated firmware:

```bash
uv run python scripts/build.py compile
CONFIG=e1003-factory.yaml uv run python scripts/build.py compile
```

## Everyday commands

```bash
uv run python scripts/build.py run       # compile + USB/OTA upload + logs
uv run python scripts/build.py upload    # personal profile network OTA
uv run python scripts/build.py logs
uv run python scripts/build.py config

uv run python scripts/build.py compile \
  -s default_light_target light.other
```

Set `CONFIG=e1003-factory.yaml` to run the build driver against the factory
entry point. Raw ESPHome commands also work.

## Release assembly

CI supplies only the public fallback-hotspot password:

```bash
cp ci/secrets.placeholder.yaml secrets.yaml
CONFIG=e1003-factory.yaml uv run python scripts/build.py compile
uv run python scripts/make_release.py \
  --config e1003-factory.yaml \
  --version v0.1.0 \
  --out dist \
  --pages-out dist-pages
```

The output contains the factory image, the ESPHome application image, an ESP Web
Tools manifest, metadata and checksums. The browser installer publishes only
the factory image.

## Recovery

- Personal profile: join `E1003-Recovery` and use its captive portal, or flash
  over USB.
- Factory profile: USB Improv Serial remains available after provisioning. If
  the initial unprovisioned window merely timed out, reboot and use Improv or
  the fallback hotspot.
- If firmware is unbootable, hold BOOT and flash the factory image over USB.

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

## Toolchain

ESPHome is pinned by `pyproject.toml` and `uv.lock`. Use `uv run`; do not install
a second global ESPHome version for this repository. Fonts are vendored under
`assets/fonts/`, so builds do not depend on host fonts.
