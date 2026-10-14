# Serial provisioning prototype

This is Phase 1 of [the SenseCraft release plan](sensecraft-release-plan.md).
Maintainers build the image; users of the planned App workflow will only enter
settings. The script below is a maintainer proof client, not an App integration.

## Build without user credentials

```bash
uv sync --frozen
CONFIG=e1003-release.yaml scripts/build.sh config
CONFIG=e1003-release.yaml scripts/build.sh compile
```

The release profile includes shared defaults from `e1003-base.yaml`, enables a
unique MAC-suffixed name and serial Improv, and compiles no station Wi-Fi or API
key. It does not need `secrets.yaml`. First flash uses the generated
`firmware.factory.bin`; maintainer USB flashing is also available with
`CONFIG=e1003-release.yaml scripts/build.sh run`.

The current release prototype is **USB-only**. ESPHome 2026.9.1's installed OTA
schema refuses a bare `ota.encryption` block when the API key is provisioned
at runtime. OTA is removed from this profile until requiring the provisioned
key has been implemented and verified. The developer profile retains its
existing encrypted OTA behavior. This prototype is not a production release.

The logger remains on the existing UART0. Improv shares that port. A physical
USB connection must expose that UART to the computer for this proof to work.
Changing to the ESP32-S3 native USB interface is not a safe assumption: the
current board configuration also uses GPIO19/20 for I2C. Validate the actual
carrier USB wiring before changing pins or logger transport.

## Configure a panel

Close ESPHome logs and other serial monitors first. They must not hold the port.
Allow the panel to finish booting, then run:

```bash
uv run python tools/provision_device.py provision \
  --port /dev/cu.usbserial-EXAMPLE \
  --reset \
  --ssid "Your Wi-Fi" \
  --target light.office
```

The script prompts for the Wi-Fi password without echoing it. It checks the
USB device's project and unique name, submits Wi-Fi credentials through Improv,
and extracts the device address from its response. The response URL is address
metadata for the setup client; there is no device web server to visit.

`--reset` restarts the E1003 through the carrier's UART reset line and allows
ten seconds for startup. This was required for reliable reopen/setup on the
tested WCH bridge (`1a86:7522`); keep serial monitors closed. It also reopens
the initial API setup window. It does not erase saved configuration.

After Wi-Fi connects, the client uses ESPHome's initial Noise provisioning
handshake to install a random 32-byte API key. It checks project/name identity
before sending the key and verifies an encrypted reconnect afterward. The
client retries the brief transition while ESPHome activates the new key.
target text entity is discovered through native API entity metadata; no HA
entity ID guessing is required. `--target` sets control only: state/brightness
push still needs the HA setup described in [HA integration](ha-integration.md).

The private record is written to
`.esphome/provisioning/reterminal-e1003-<mac-suffix>.json`. It stores the device
identity, API key, target, and last address, but no Wi-Fi password. On POSIX the
file is created with mode `0600`. Keep it in a private user-owned directory;
Windows permissions need verification during App integration.

The record is saved before the key request is sent. If setup is interrupted,
reuse the same record instead of generating another key. Rerun `provision` with
the same USB device; `--state-file` can explicitly select the saved record.
If DHCP changed the address, use `--host` with the panel's current IP.

## Add to Home Assistant and check persistence

In HA, confirm the discovered ESPHome device. Explicitly display the saved key
for the integration's key field with:

```bash
uv run python tools/provision_device.py show-key \
  --state-file .esphome/provisioning/reterminal-e1003-<mac-suffix>.json
```

Allow the device to perform HA actions in its integration options. Wait at least
65 seconds after changing text settings before removing power or using a hard
reset: ESPHome's default preference flush interval is 60 seconds. Wi-Fi and
the API key are synchronized immediately by their provisioning handlers;
the text readback only confirms the live value. Restart the panel, then use
the read-only device check:

```bash
uv run python tools/provision_device.py verify \
  --state-file .esphome/provisioning/reterminal-e1003-<mac-suffix>.json
```

This verifies the encrypted connection and saved target readback. It does not
prove the light responds to touches or that the display is synchronized; both
require a panel and HA test.

## Retry and reset

- Wi-Fi failure: correct the credentials and rerun setup over USB.
- Initial setup window expired: reconnect power and retry within ten minutes.
  Serial Improv remains available after the window expires, but initial API
  key provisioning requires a reopened window.
- Lost key record on an already provisioned device: a power cycle does not
  erase the key. A deliberate factory reset of MCU flash followed by flashing
  the same factory image is the recovery path for this prototype. It deletes
  saved Wi-Fi and runtime settings. No automatic erase or key replacement is
  performed by the setup script.

## Local App configuration adapter

`tools/app_configure_device.py` lets an App `script` step configure the device
using the existing maintainer environment. It takes the USB port, light target,
optional Wi-Fi name/password, and optional key-copy selection through environment
variables. The shell command is fixed; user values are not interpolated into
command text or stored in a generated configuration file.

The variable names are `E1003_USB_PORT`, `E1003_TARGET`, `E1003_WIFI_SSID`,
`E1003_WIFI_PASSWORD`, and `E1003_COPY_KEY`. Empty Wi-Fi fields preserve the
current network and require an existing private device record. New Wi-Fi
settings use the same Improv/key provisioning path as the maintainer client.
Restored credentials do not prove connectivity: the adapter waits for Improv's
network-online flag before selecting the device address.

After target readback, the adapter waits 65 seconds, hard-resets the panel,
and verifies encrypted reconnect and target persistence. Only then does it print
the `E1003_CONFIGURATION_SAVED` health marker. An explicit key-copy selection
copies the device key to the macOS clipboard without printing it.

This is a **local test adapter**, not a redistributable dependency bundle. The
tested App source frontend/backend submits script inputs correctly; the installed
0.7.3 build on this machine omitted them. Its local solution therefore opens
the working source-preview configuration page. The source preview has isolated
application data and a separate runtime pointer; it does not replace the
installed App. Packaging the runtime for other computers remains pending.
- Normal USB update: configuration retention depends on the image and erase
  policy. It is not yet verified; do not treat factory reset and update as the
  same operation.

## Offline checks

```bash
uv run python -m unittest discover -s tests -v
```

These tests cover the wire-format fixture, log/frame fragmentation, malformed
packets, UTF-8 lengths, identity checks, and recovery from a lost key response.
The network peer is simulated; passing them is not hardware proof.
