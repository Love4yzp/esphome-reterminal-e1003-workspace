# Provisioning prototype verification

Current reference default (2026-10-15): firmware 0.2.0 uses keyless API access,
with optional encryption and no initial API setup timeout. See
[the current setup guide](provisioning.md) and
[0.2.0 verification](keyless-reference-verification.md). Mandatory-key and timed-window
steps below describe the earlier 0.1.0 prototype and its historical evidence.

Verified on 2026-10-14 on macOS with ESPHome 2026.9.1 from the project lockfile.
Software checks, USB flashing, Wi-Fi/key/target provisioning, two resets, and
same-image USB update persistence pass on one E1003. This is not a production
release pass.

## Implemented

- Shared defaults/package assembly in `e1003-base.yaml`; developer credentials
  remain in `e1003-dashboard.yaml`.
- `e1003-release.yaml` builds without `secrets.yaml`, with a MAC-suffixed name,
  serial Improv, a ten-minute initial setup window, and a runtime API key.
- `tools/provision_device.py` implements serial Wi-Fi setup, device identity
  checks, private recovery records, key initialization, encrypted reconnect,
  optional target write/readback, and a read-only device persistence check.
- The release target starts empty. Control binding does not establish automatic
  display state synchronization; that remains Phase 2.

## Executed checks

| Check | Result |
|---|---|
| `uv sync --frozen` | Passed; used elevated execution because uv's macOS network-settings lookup crashed inside the sandbox |
| `scripts/build.sh config` (developer profile) | Passed: `Configuration is valid!`; synthetic build-only credentials were removed afterward |
| `scripts/build.sh compile` (developer profile) | Passed: `Successfully compiled program.` |
| `CONFIG=e1003-release.yaml scripts/build.sh config` | Passed: `Configuration is valid!`, with no secrets file present |
| `CONFIG=e1003-release.yaml scripts/build.sh compile` | Passed: `Successfully compiled program.`, with no secrets file present |
| Developer merged configuration versus pre-change baseline | Exactly equal, including credentials, component settings, and defaults |
| Release configuration inspection | No station credentials or static API key; unchanged UART0 and display/touch transforms |
| `python -m unittest discover -s tests -v` | Eleven tests passed; covers interrupted key setup, activation delay, captured Improv footer, and consecutive request boundaries |
| `python tools/layout_to_h.py --check` | Passed: five zones, four fonts, ten fields |
| Python bytecode compilation and `bash -n scripts/build.sh` | Passed |
| Local Markdown links and `git diff --check` | Passed |

The first eight helper tests were added after implementation for this spike.
The activation-delay, zero-footer, and consecutive-request regressions were
added before their fixes and each failed first. The API failure peers are
simulated. The identity fixture was captured from the flashed panel.

## Build measurements

| Measurement | Developer baseline | USB release prototype | Change |
|---|---|---|---|
| RAM | 112,895 / 341,760 bytes (33.0%) | 112,687 / 341,760 bytes (33.0%) | -208 bytes |
| Application flash | 1,360,463 / 1,835,008 bytes (74.1%) | 1,312,867 / 1,835,008 bytes (71.5%) | -47,596 bytes |
| Successful build wall time | 159.94 seconds | 80.75 seconds | Different cache states; not a controlled speed comparison |
| Compiler diagnostics containing `warning:` | None | None | No new compiler warnings |

Both configurations retain existing validation warnings about GPIO19/20 and
USB-Serial-JTAG, and GPIO45 as a strapping pin. No wiring, touch coordinates, or
display transforms were changed. UART0 has now been verified through the
carrier's WCH USB serial bridge.

The footprint reduction is explained by removing OTA and the captive portal
from the release prototype, partly offset by Improv/provisioning support.

Toolchain preparation preceded these timings. The first build attempt selected
an inherited ESP-IDF 5.4.3 installation and failed on a missing
`esp_idf_monitor`. Removing `IDF_PATH` selected ESPHome's managed ESP-IDF 5.5.5.
Its framework download was slow; the exact official archive was fetched with
curl, checked against the existing partial bytes and expected size, and resumed
through ESPHome's downloader. These preparation delays are excluded from the
successful build timings. No conclusion about mainland-China network speed is
drawn from this Mac build.

Local footprints after both builds: Python environment approximately 164 MB,
project build cache 638 MB, and managed ESP-IDF cache 1.7 GB. Existing machine
caches were also available; this is not a clean-machine download-size estimate.

## Artifact

Factory image: `.esphome/build/reterminal-e1003/build/firmware.factory.bin`.
Size: 1,378,512 bytes.

SHA-256:

```text
08d616e856cd4d48a0fef0b4e5782e3c4ac1b9efdc1e1647701707bec8bdc540
```

The compiler also emits an application/OTA binary even though this profile has
no OTA listener. Its existence does not mean OTA is enabled or verified.

## Hardware loop

The user confirmed `/dev/cu.wchusbserial2120` (WCH `1a86:7522`) as the E1003 and
authorized flashing and iterative testing. The chip identifies as ESP32-S3
revision 0.2 with 8 MB PSRAM and 32 MB physical flash. The firmware retains the
original 4 MB partition layout; old and new partition offsets/sizes match.

Before flashing, the first 4 MB (including NVS and every region touched by this
image) was backed up to the private, ignored directory
`.esphome/verification/hardware-backup/`. Higher baud rates failed; 115200
completed with the stub's digest verification. The remaining physical flash
was not erased or written.

The factory image above was written at offset zero at 115200 baud. Writing
took 72.8 seconds and esptool confirmed the flash hash. A captured hard reset
shows successful application setup and IT8951 panel detection at 1872x1404.
Three consecutive reopen/reset/identity cycles returned the expected project,
version, variant, and unique name.

Two real transport failures were reproduced and corrected in the client:

- The installed Improv library's `finish(false)` appends a zero footer outside
  the inner data length. The client accepts precisely that form after the
  outer frame checksum passes, while retaining strict malformed-frame checks.
- ESPHome retains a completed receive frame until a separator or its 100 ms
  timeout. An immediate next request lost its header. Requests now include a
  newline separator; a regression test reproduced the previous timeout.

The WCH bridge required an explicit reset after port reopen. The maintainer
client exposes `--reset`; it does not erase saved configuration.
Raw diagnostics, backup flash, and temporary network-test credentials are
private local files and must not be committed or published.

The first provided SSID was absent from 26 scanned networks. Once the protocol
boundary was fixed, it produced Improv error 3 rather than a transport timeout.
The user selected a visible network through a local dialog and entered its
password without echoing it. Provisioning then completed successfully:

- Wi-Fi connected and returned an address through Improv.
- A random per-device 32-byte API key was installed; an encrypted connection
  verified the device's project, name, and MAC.
- The runtime target `light.e1003_provisioning_test` was written and read back.
  This is a test value, not a real HA light/control proof.
- The initial zero key was rejected with `InvalidEncryptionKeyAPIError`;
  the saved key still worked before and after that rejection.
- After allowing 65 seconds for the default 60-second text-preference flush,
  two hard resets each retained Wi-Fi, identity, API key, and target.
- The normal setup record has POSIX mode `0600` and contains no Wi-Fi password.

The same factory image was then flashed again with no full-chip erase. Its
SHA-256 remained unchanged and esptool verified the write. After a hard reset,
Improv reported online Wi-Fi and the same private key reconnected with the same
target. This proves retention for this same-image, same-partition USB update;
it does not prove migration across firmware versions or different flasher
erase policies. The temporary local Wi-Fi input file was removed afterward.

Two mDNS probes (named lookup and service browse on the route's local interface)
did not find this panel. The Mac's route source was in `10.8.0.0/24` while the
panel address was in `192.168.101.0/24`. Native API connectivity by IP works;
the absence of multicast discovery on this test path does not establish its
cause. HA auto-discovery remains unverified on the intended shared LAN.

## Blocked and pending checks

- HA discovery and real-light control, touch accuracy, panel mirroring, and
  ghosting require the remaining hardware checks. HA address and a test light
  entity are not yet provided.
- OTA runtime-key inheritance was rejected by the installed schema. This
  prototype is explicitly USB-only; authenticated OTA needs a separate proof.
- HA Blueprint/state synchronization, SenseCraft engine/App integration,
  supported-host installation, mainland-China downloads, two-panel isolation,
  and update/reset persistence are later phases of
  [the release plan](sensecraft-release-plan.md).

Continue with the physical setup and reboot procedure in
[Serial provisioning](provisioning.md) when an E1003 is connected.

## Local App configuration follow-up

The local solution now has both flash-and-configure and configuration-only
presets. The configuration form supplies a USB port, light entity ID, optional
Wi-Fi settings, and optional local key copy to `tools/app_configure_device.py`.
Changing the target does not reflash or rebuild the image.

Actual browser testing exposed two failures before success: `target` conflicts
with the engine's deployment-target selector (the form now uses `light_entity`),
and the installed App 0.7.3 did not submit script inputs. The current App source
at `39aee2da23b2604d2d2cde6bcf3c20c0aecbd16f` already has the input fixes. An
isolated source preview was built and started; the installed App's configuration
entry opens that preview rather than presenting a broken script form.

Restored Improv credentials can report provisioning before Wi-Fi reconnects.
Waiting for actual network-online status corrected the first connection failure.
The new regression failed before this fix. The adapter's four behavior tests
also failed before implementation; the complete suite now has 16 passing tests.
The tests cover network preservation, save-before-reset ordering, secret-free
output, and invalid-target rejection. External transport peers are simulated.

Through the real configuration form, a configuration-only deployment completed
in 88.62 seconds: identity check, original-key reuse, test target
`light.e1003_app_configuration_test` write/readback, normal preference flush,
hard reset, and encrypted reconnect/readback. An independent read-only client
check passed afterward. The firmware was not recompiled or flashed in this test.
The installed App entry was clicked and opened the editable configuration form.

This proves local target configuration with the existing network. New Wi-Fi
input transport has regression coverage and reuses the previously proven Improv
path; changing Wi-Fi through this new form has not been physically tested.
Runtime dependency distribution, real HA light control, and display state
synchronization remain separate acceptance work.
