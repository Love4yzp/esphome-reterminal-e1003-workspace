# Reference firmware setup

Maintainers build one USB firmware image. Users configure its Wi-Fi and light
entity from the SenseCraft Solution desktop App without compiling or editing
`secrets.yaml`. The reference release uses plaintext-only API access without a key.

## Build and install

```bash
uv sync --frozen
CONFIG=e1003-release.yaml scripts/build.sh config
CONFIG=e1003-release.yaml scripts/build.sh compile
```

If the shell exports an unrelated ESP-IDF installation, unset `IDF_PATH` for
these commands so ESPHome uses its managed toolchain. The release image uses
the same pins, artwork and layout as the developer profile. Its MAC-suffixed
name is unique; its initial light target is empty.

Release `0.2.1` keeps serial Improv and removes API encryption support entirely.
External clients cannot set an encryption key on this image. It also removes
the API provisioning timeout. A keyless device remains accessible
after ten minutes and does not reboot while waiting for HA. OTA stays disabled.
The developer profile retains its existing credentials and encrypted OTA.

## Desktop setup

Use the single **Deploy E1003** entry. Select USB, enter the target `light.*`
entity, and enter Wi-Fi credentials if the device needs a network. Saved Wi-Fi
can be reused even when this computer has no prior device record.

The App checks firmware project, version, hardware and name. A matching release
skips installation; otherwise the App verifies and installs the precompiled
image without full-chip erase, then checks its identity again. It writes the
settings, waits 65 seconds, resets the panel and reads the saved target back.

Add the device address to HA's ESPHome integration without a key. There is no
encryption option or key-copy step. Enable **Allow the device to
perform Home Assistant actions** in that integration's options.

The target must exist in HA. Saving an entity ID does not add the device to HA
or grant action permission. Display state and brightness synchronization remain
a separate HA-side step; see [Home Assistant integration](ha-integration.md).

## Maintainer client

The CLI exercises the same protocol for development; it is not required by App
users. It prompts for the Wi-Fi password without printing or storing it.

```bash
uv run python tools/provision_device.py provision \
  --port /dev/cu.usbserial-EXAMPLE --reset \
  --ssid "Your Wi-Fi" --target light.office
```

The client verifies USB and API identity before changing settings. It does not
generate or send an API key for the reference image.

Records are private files under `.esphome/provisioning/` with POSIX mode
`0600`. They contain identity, address and target, with no Wi-Fi password or
API key for this reference image. Normal installation preserves NVS. Stored
keys from older experiments are ignored by plaintext-only firmware; no key
record or full-chip erase is required to install it.

Wait 65 seconds after editing runtime text settings before power removal, then
verify persistence:

```bash
uv run python tools/provision_device.py verify \
  --state-file .esphome/provisioning/reterminal-e1003-<mac-suffix>.json
```

Verification uses keyless access. The legacy `show-key` helper is unnecessary
for this image. A USB update and a factory reset are different:
normal installation preserves NVS; a full erase deletes Wi-Fi and settings.

## Troubleshooting

- Close other serial monitors before setup. The tested WCH bridge requires an
  explicit reset on reopen; `--reset` does not erase preferences.
- Keyless setup requires firmware `0.2.1` or later. Older prototypes can
  close their setup window or accept an encryption key from a client; update
  them before using this fixed reference mode.
- Wi-Fi failure: enter the correct network settings and retry.
- A recognized touch logs `Touch x=... y=...`; a button hit also logs its zone.
  Zone hits beep and request an HA action. They do not confirm that HA executed
  the action. The bitmap has no pressed-state animation.
- No touch log: check GT911 initialization and wiring. Touch logs without a
  zone hit: check the hit box on real hardware before changing coordinates.
- Zone hit without light response: check the actual target, HA integration,
  and action permission. An App setup connection is not an HA integration.

## Offline checks

```bash
uv run python -m unittest discover -s tests -v
```

These checks cover Improv framing, identity, keyless operation, optional key
provisioning, interrupted setup and the local legacy script adapter. They do
not prove physical touch accuracy or real HA light control.
