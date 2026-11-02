# Build and flash

## Public first-install image

Tagged releases are built from `e1003-factory.yaml`. The factory image contains:

- no station Wi-Fi SSID or password;
- no AP password;
- no pre-shared ESPHome API key;
- an open MAC-suffixed setup AP;
- a captive portal at `192.168.4.1`;
- Improv Serial as an additional USB setup path;
- a 24-hour provisioning window that reopens after reboot;
- no persistent ESPHome native OTA service.

Use the browser installer with a USB-C data cable, or flash
`firmware.factory.bin` at offset 0 with esptool. After flashing, join the open
hotspot whose name starts with `reterminal-e1003-`, then open `192.168.4.1`
and enter the destination Wi-Fi credentials. The credentials are saved in NVS
and reused after reboot.

Home Assistant provisions a unique API encryption key when the device is added
for the first time. Import the supplied light-sync blueprint afterward to
select the user's light and keep the card synchronized.

ESPHome's captive portal automatically includes a web updater. In this profile
its HTTP listener is available during setup. The release also carries
`firmware.ota.bin`; use the captive-portal updater or USB for later updates.

## Build the open-source default

No `secrets.yaml` is required:

```bash
uv sync
uv run python scripts/build.py run
```

`e1003-dashboard.yaml` starts the open `E1003-Setup` AP. Join it and open
`192.168.4.1`. Override `setup_ap_ssid` only when a downstream build needs a
different setup name.

## Keyless USB reference profile

`e1003-release.yaml` is the reference flow documented in
[Serial provisioning](provisioning.md). It contains no station credentials,
uses Improv Serial, exposes a plaintext-only ESPHome API, and has no OTA
service. Build it with:

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
uv run python scripts/build.py upload    # upload when the active profile supports it
uv run python scripts/build.py logs
uv run python scripts/build.py config

uv run python scripts/build.py compile \
  -s default_light_target light.other
```

Set `CONFIG=e1003-factory.yaml` to run the build driver against the factory
entry point. Raw ESPHome commands also work.

## Release assembly

```bash
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

- Default profile: join `E1003-Setup` and open `192.168.4.1`.
- Factory profile: join the open MAC-suffixed AP. If the provisioning window
  expired, reboot to reopen it. USB Improv Serial remains available.
- Saved Wi-Fi no longer available: reboot and wait for the fallback setup AP,
  then save the replacement network through the captive portal.
- mDNS discovery unavailable: read the station IP from the panel's network card
  and add the ESPHome integration manually with that address.
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
