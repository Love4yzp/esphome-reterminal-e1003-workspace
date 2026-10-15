# Keyless reference verification history

Date: 2026-10-15. This records the reference default requested after the
[earlier encrypted prototype](provisioning-verification.md).

## Current 0.2.1 build

Configuration and compilation pass. The generated firmware defines
`USE_API_PLAINTEXT`; `USE_API_NOISE` and `USE_PROVISIONING` are absent. API
client-wait rebooting remains disabled. The App has no key-selection or key-copy
control, and `encrypt_api=true` is rejected before hardware access.

- Factory image: 1,337,072 bytes (41,440 fewer than 0.1.0).
- SHA-256: `23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528`.
- Application flash: 1,271,415 bytes (69.3%); RAM: 112,583 bytes (32.9%).
- 19 tool checks, 53 focused App checks plus five subtests, and 955 frontend
  checks pass. PyInstaller/Rust/Tauri debug builds pass. No new compiler
  warnings; existing pin warnings are unchanged.
- Upload was not started: the WCH USB serial port disappeared before selection.
  Actual device identity, `api_encryption_supported == false`, persistence and
  touch on 0.2.1 still need a reconnected device. The prior 0.2.0 image must not
  be reported as this final image's hardware proof.

## Subsequent correction

The 0.2.0 keyless reconnect passed at 610 seconds, but a later connection
required encryption again. The initiating client has not been identified.
Retaining runtime encryption support therefore does not establish fixed
keyless behavior. The final reference profile is 0.2.1, with API encryption
compiled out. The developer profile retains separate encryption support.
The 0.2.0 results below are historical and do not certify the final image.

## 0.2.0 experiment

Release `0.2.0` defaults to API access without a key. Optional runtime encryption
is retained. Removing the initial provisioning timer keeps keyless API access
available after ten minutes. API client-wait rebooting is disabled. USB Improv,
Wi-Fi preferences, NVS layout, display transforms and touch hit boxes are
unchanged. Touch coordinates and zone hits now log at INFO for diagnosis.

The maintainer client and App default to no key. An existing encrypted record
can explicitly clear its key; the recovery key is kept until keyless reconnect
succeeds. Keyless setup on a device with saved Wi-Fi needs no prior local record.
Older firmware is rejected for this mode instead of leaving timed API access.

## Checks

- Release `scripts/build.sh config` passed: `Configuration is valid!`.
- Release `scripts/build.sh compile` passed: `Successfully compiled program.`.
- The first build inherited a separate `IDF_PATH` and failed to import
  `esp_idf_monitor`. Running with `IDF_PATH` unset selected ESPHome's managed
  toolchain and passed. No dependency or lockfile changes were needed.
- 19 maintainer-tool checks passed, including optional encryption, interrupted
  key setup, keyless readback, switching off encryption and saved-Wi-Fi reuse
  without a local record.
- Layout validation and local documentation links passed. Only existing
  GPIO19/20 and GPIO45 configuration warnings remain; no new compiler warnings.

| Artifact | 0.1.0 | 0.2.0 |
| --- | --- | --- |
| Factory image | 1,378,512 bytes | 1,377,472 bytes |
| Application flash | 1,312,867 bytes | 1,311,819 bytes |
| RAM | 112,687 bytes | 112,639 bytes |

Factory SHA-256:
`45cbf1ec46d5a00e8362e6d920cd9318841c58f2a081cfae809d9e38e64ccebb`.

## Real device upgrade

The local packaged App backend and shared desktop frontend used one deploy
form. Task `56899ea5f4c441aab0bf1ea227c50473` detected `0.1.0`, installed and
verified the pinned `0.2.0` image, then completed settings save and readback.
This was an actual version upgrade, without identity fault injection.

Wi-Fi fields were empty; the device reused its saved network. The prior private
API record authorized clearing its key without full-chip erase. The same target
was written, followed by a 65-second save wait, reset and keyless target readback.
Completion reported `encrypted: false`. The resulting private record contains
no API key. A separate plaintext connection and target readback passed at least
610 seconds after the completed reset verification, beyond the old ten-minute
window. Desktop and 375x812 form screenshots confirmed the optional checkbox
starts unchecked, key copying stays hidden, and the form has no horizontal
overflow. This proves the shared frontend/backend flow, not a new native-window
form submission.

## Touch boundary

The firmware's static button artwork has no pressed-state animation. A hit
should beep and request an HA action. Local log observation without a confirmed
user tap is not evidence that touch works or fails. Physical touch/zone accuracy,
real HA control and dynamic screen state remain unverified in this test.
The current light target is a test placeholder, not an accepted real HA light.
