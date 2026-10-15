# Reference firmware setup

Maintainers build one USB image. Users configure Wi-Fi and a light entity in
SenseCraft Solution without editing YAML or compiling firmware. Release 0.2.1
uses plaintext-only API access, with no encryption selection or key-copy step.
The separate developer profile retains its own encrypted API and OTA settings.

## Maintainer build

```bash
uv sync --frozen
CONFIG=e1003-release.yaml scripts/build.sh config
CONFIG=e1003-release.yaml scripts/build.sh compile
```

Unset an unrelated `IDF_PATH` so ESPHome uses its managed toolchain. Publish the
factory image with its exact version, size and SHA-256 in the solution manifest.
Use a different project version for every different firmware image. Normal USB
installation preserves NVS; full-chip erase deletes saved Wi-Fi and settings.

The provisioning client is maintained in the [desktop App](https://github.com/suharvest/app_collaboration/pull/162).
This repository contains firmware and design tooling, not a second client.

## User setup

1. Open **Configure E1003** in the App and connect the USB data cable.
2. Confirm the USB port and paste the target light's `light.*` entity ID.
3. Open Wi-Fi settings for first setup or a network change. Otherwise leave
   them empty to reuse the saved network.
4. Click **Save settings**. The App checks firmware and installs it if needed,
   saves configuration, waits 65 seconds, restarts and verifies the target.
5. After **Settings saved and verified**, add the displayed address in HA's
   ESPHome integration and allow the device to perform Home Assistant actions.

Keep the computer, panel and HA on a mutually reachable LAN. Saving a light ID
neither adds the device to HA nor grants action permission. Display state and
brightness synchronization need separate HA configuration; see
[Home Assistant integration](ha-integration.md).

## Current verification

| Scope | Status |
| --- | --- |
| Release 0.2.1 configuration and compilation | Passed; plaintext enabled, encryption support removed |
| App installation/configuration software | See App tests and CI; no local Python install is required |
| Final 0.2.1 physical installation and readback | Not verified |
| Physical touch, actual HA control and display synchronization | Not verified |

Further physical tests were excluded by the user. Earlier prototype results
do not establish acceptance of the final image.

## Troubleshooting

- Missing port: check the data cable, refresh, and close other serial tools.
- Wrong network: enter the correct 2.4 GHz Wi-Fi settings and retry.
- Configuration failure: inspect technical details in the App. It preserves
  NVS and does not use keys or local key-recovery records.
- A recognized touch logs `Touch x=... y=...`; a zone hit also beeps and
  requests an HA action. It does not prove the light changed. Only the switch
  and four brightness zones have bindings; other artwork is static.
- No touch log: inspect GT911 initialization and wiring. Correct hit boxes
  only with real-panel testing. For an action without a light response,
  check the target entity and HA action permission.
