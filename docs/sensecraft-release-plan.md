# SenseCraft precompiled firmware deployment plan

Current reference default (2026-10-15): firmware 0.2.0 uses keyless API access,
with optional encryption and no initial API setup timeout. See
[the current setup guide](provisioning.md). Mandatory-key and timed-window
steps below describe the earlier 0.1.0 prototype and its historical evidence.

## Go / No-Go

**Go for HA and App integration proof.** The USB-only release prototype now
passes flashing, Wi-Fi/key/target setup, and two reset-persistence checks on
one E1003. Same-image USB flashing also preserves this configuration. The
maintainer client passes software checks. Distribution is not ready
until panel provisioning, Home Assistant synchronization, and real App
deployment pass. See [the verification record](provisioning-verification.md).

## Target outcome

Maintainers compile and publish one firmware per supported hardware/layout
version. Users deploy it through SenseCraft Solution App, enter Wi-Fi settings
and a target light entity, and confirm the device in Home Assistant (HA).
Users never edit YAML, install a compiler, or build firmware.

## Goal definition

- **Type:** delivery and product.
- **Boundary:** E1003 with XIAO ESP32-S3, the existing layout, one dimmable HA
  light, and App computer, panel, and HA on the same reachable LAN.
- **Non-goals:** MQTT, an on-device web server, cloud compilation, end-user
  compiler packages, layout editing, and additional control types.
- **Deferred:** automatic HA login/entity enumeration and automatic confirmation
  of HA integration setup. First release accepts a pasted entity ID and guides
  users through HA confirmation and action permission.
- **Verification rule:** the same firmware SHA-256 must serve two devices with
  different identities, API keys, and light targets. Switching a target must
  update both control and display without rebuilding.
- **Evidence:** build logs, artifact hashes, provisioning-client results, HA
  traces, and observations on actual panels.
- **Pass criteria:** configuration survives reboot and a supported update;
  closing App does not interrupt operation; no user configuration-file editing.
- **Confidence:** upstream code supports the proposed primitives; end-to-end
  behavior remains untested. Compilation cannot prove touch or display accuracy.
- **Judgment owner:** maintainer acceptance of recorded end-to-end results.

## Current state

- [The developer profile](../e1003-dashboard.yaml) keeps the existing local
  credentials and captive portal. [The release prototype](../e1003-release.yaml)
  enables serial Improv and unique names without station credentials or a
  static API key. Both reuse [shared defaults](../e1003-base.yaml) and
  [core.yaml](../packages/core.yaml).
- [ha-bridge.yaml](../packages/ha-bridge.yaml) already exposes persistent target,
  action, and display text settings. Its fallback state imports remain fixed
  at compile time.
- [touch.yaml](../packages/touch.yaml) reads the runtime target for HA calls.
- [HA integration guide](ha-integration.md) describes state push recipes.
  [The HA package](../ha/e1003_dashboard.yaml) is an unsupported example; its
  hardcoded trigger is insufficient for arbitrary runtime targets.
- [Build tooling](build-and-flash.md) locks ESPHome to 2026.9.1. Both profiles
  compile. The release prototype uses 112,687 bytes RAM and 1,312,867 bytes
  application flash; these are compiler measurements, not panel behavior.
- The installed OTA schema refuses inheriting a runtime-provisioned API key in
  `ota.encryption`. The release prototype disables OTA. Requiring authenticated
  OTA remains a production release dependency; do not enable plaintext OTA as
  a workaround.
- SenseCraft content has an `esp32_usb` deployer configuration for artifact
  download and flashing. Its reviewed schema does not establish an Improv or
  ESPHome API setup handler. Engine capability must be verified separately;
  adding solution inputs alone does not implement their configuration writes.

## Priority rationale

Prove post-flash provisioning before building App screens or publishing an
artifact. Then prove the target light follows configuration even with App shut
down. Only integrate the proven operations into the deployment UI.

## Assumptions and open decisions

| Item | Status | Next step |
|---|---|---|
| Users have HA on the same LAN and control a dimmable light | Confirmed scope | Keep first release bounded to this workflow |
| Serial Improv is usable over the E1003 USB connection | Verified on WCH bridge/UART0 | Carry reset and frame-boundary handling into App |
| Runtime API key setup works with the pinned versions | Verified on one panel | Preserve private per-device records in App |
| SenseCraft engine can host the setup client | Unverified | Inspect actual engine implementation and define an adapter |
| HA state push can follow target changes without hand-editing YAML | Unverified | Prove a focused Blueprint using runtime target state |
| Factory flashing and OTA preserve the intended configuration | Same-image USB overwrite verified; OTA disabled | Prove cross-version migration and authenticated OTA |

## Progress management

Mark a phase complete only when its exit proof passes. Re-evaluate unresolved
assumptions before each phase; record changes to the route in this document.

- [ ] Phase 1: prove provisioning and build the release profile.
- [ ] Phase 2: prove persistent control and display binding.
- [ ] Phase 3: integrate the SenseCraft deployment flow.
- [ ] Phase 4: validate and publish the release artifacts.

## Phases

### Phase 1: prove provisioning and build the release profile

**Entry:** this scope is stable; a panel and HA instance are available for
hardware proof. Software inspection and compilation can proceed independently.

**Rules:** preserve layout, touch transforms, and refresh policy. Keep the
developer build usable without duplicating hardware/rendering configuration.
Do not assume HA itself provisions the API key.

- [x] Create a release build profile that builds without `secrets.yaml`, using
  shared packages, unique device identity, project/version metadata, and serial
  Improv. Separate developer credentials from shared core configuration if
  necessary. **Surface:** entry-point YAML and core packages. **Proof:** both
  developer and release config/compile checks succeed.
- [x] Use a small maintainer setup client to configure Wi-Fi, identify the
  connected panel, and set an independent API key through the native API.
  Use the supported provisioning handshake; verify success by reconnecting with
  the new key. **Surface:** a setup script and firmware provisioning config.
  **Proof:** key, identity, and Wi-Fi survive a reboot on real hardware.
- [ ] Define retry, expired setup-window, lost-key, and explicit reset behavior.
  **Surface:** setup client and configuration/build guides. **Proof:** failure
  paths are recoverable without rebuilding firmware.

**Exit:** a credential-free artifact can be flashed, configured, rebooted, and
added to HA with its generated key. No personal Wi-Fi or shared API key is
baked into the image.

**Stop:** if the pinned client cannot provision the key or the USB channel is
unusable, revise this phase before App integration. Do not substitute per-user
compilation or a shared key without changing the agreed target.

### Phase 2: prove persistent control and display binding

**Entry:** Phase 1 provisioning passes.

**Rules:** reuse runtime text entities and the existing dirty-flag refresh
contract. Retain documented developer fallback behavior. App is a setup tool,
not a persistent state relay. The existing HA package remains an example.

- [ ] Have the setup client discover the panel's text entities and write/read
  back the target through the native API. Avoid guessing HA-generated entity
  names. **Surface:** setup client and HA bridge. **Proof:** rebooted panel
  controls the configured light.
- [ ] Add a focused HA Blueprint for state/brightness push that follows the
  panel's runtime target, including target changes, initial synchronization,
  HA restart, panel reconnect, and unavailable targets. Users import and select
  entities in HA UI; they do not edit YAML. **Surface:** a new Blueprint
  artifact and HA guide. **Proof:** change A to B; control and display follow B
  and A no longer drives the card. This includes brightness-only changes.
- [ ] Confirm the setup client and App can exit after setup. **Proof:** HA
  continues state push, and touch control remains functional.

**Exit:** both control and display follow a changed target without a firmware
build or a running App.

**Stop:** if the Blueprint cannot synchronize dynamic targets reliably, compare
an explicit alternative before adding polling or custom subscription code.

### Phase 3: integrate the SenseCraft deployment flow

**Entry:** the setup operations from Phases 1 and 2 are proven independently.

**Rules:** reuse `esp32_usb` for flashing; do not add user compiler dependencies.
Changes to SenseCraft engine belong in its repository, not this firmware repo.
Do not treat generic serial-wizard send buttons as an Improv implementation.

- [ ] Add a solution descriptor for the exact chip, artifact, flash offsets,
  checksum, and selected USB port. **Surface:** SenseCraft solution content.
  **Proof:** its content validation passes and it flashes the intended artifact.
- [ ] Integrate serial Improv and native API setup with the actual engine.
  Present Wi-Fi/password/target inputs, staged progress, resumable failures,
  device identity, and a copyable HA key. **Surface:** SenseCraft engine/App.
  **Proof:** deployment works from App without the maintainer setup script.
- [ ] Guide HA confirmation, action permission, and Blueprint import/entity
  selection. Show each as incomplete until verified; flashing alone is not
  successful deployment. **Proof:** a new user completes setup without editing
  configuration files.

**Exit:** App drives download, flash, Wi-Fi, key setup, and target binding, with
explicit HA UI completion steps and a working light/display test.

**Stop:** if engine support is missing, implement the bounded adapter before
promising that a content-only solution can perform setup.

### Phase 4: validate and publish release artifacts

**Entry:** Phases 1 through 3 pass.

**Rules:** compile only in maintainer infrastructure. Distribution readiness
requires hardware evidence; publishing is a separate release action.

- [ ] Establish a fixed-version CI build and publishable factory/OTA binaries,
  SHA-256 checksums, version metadata, and change notes. **Surface:** build/CI
  and release metadata. **Proof:** clean release build needs no user secrets.
- [ ] Validate download and App installation on supported Windows/macOS hosts
  without Python, ESPHome, Git, a compiler, or a proxy configured by the user.
  Include a mainland-China network test. **Proof:** recorded results, not an
  assumed guarantee of CDN reachability.
- [ ] Flash the identical binary onto two panels; use different Wi-Fi profiles,
  keys, and targets. Test reboot, HA reconnect, target swap, OTA, intentional
  USB update, and factory reset. **Proof:** hashes and behavior records show
  configuration isolation and the documented persistence/reset policy.

**Exit:** maintainer accepts all evidence and the artifacts are ready for the
release channel.

**Stop:** no release verdict while panel tests, HA tests, or supported-host
installation checks remain incomplete. The USB-only prototype must also gain
verified authenticated OTA before the complete planned release is accepted.

## Dry-run findings

- Serial Wi-Fi provisioning and API key provisioning are different operations.
  Improv does not by itself configure an API key or light target.
- UART0 is verified through the tested WCH bridge. App must handle its reset
  behavior and separate serial log bytes from Improv responses.
- A pasted entity ID avoids HA account authorization in App. Blueprint import
  and HA confirmation still need guided user actions in the first release.
- A universal image needs state push or dynamic subscriptions; changing the
  control target alone leaves the fallback display bound to the old entity.
- Configuration retention depends on the flasher erase policy as well as
  firmware persistence. OTA and USB update must be tested separately.
- Runtime text settings use ESPHome's default 60-second preference flush.
  App must account for durable saving before telling users to unplug the panel;
  live readback alone is insufficient. The maintainer proof waits 65 seconds.
- SenseCraft engine source is separate from the reviewed content repository.
  Its setup support and dependency packaging remain an integration dependency.

## Final validation

For firmware changes, run `scripts/build.sh config` and `scripts/build.sh compile`
for the developer entry point, and the same commands with `CONFIG` set to the
release entry point. Record baseline/new RAM and flash usage; accept no new
compiler warnings or unexplained growth. Inspect build outputs and generated
files. Run the layout checks if layout references change. Check Markdown links
and `git diff --check` for documentation updates.

The end-to-end pass additionally requires physical touch, display, HA, and
supported-host evidence. A compilation success cannot replace these results.

## First execution step

Build a minimal release profile and maintainer setup client, then prove USB
Wi-Fi provisioning, runtime key setup, and encrypted reconnect on one E1003.
Do not begin App UI work before this chain is demonstrated.

## Verified upstream references

- [Serial Improv](https://esphome.io/components/improv_serial/): Wi-Fi setup
  normally shares the logger port.
- [ESPHome 2026.9.1 API server](https://github.com/esphome/esphome/blob/2026.9.1/esphome/components/api/api_server.h): runtime key persistence exists for
  the provisioning path when no key is compiled from YAML.
- [ESPHome 2026.9.1 key request handling](https://github.com/esphome/esphome/blob/2026.9.1/esphome/components/api/api_connection.cpp): validates and saves the
  key and checks the provisioning window.
- [aioesphomeapi 46.3.0 client](https://github.com/esphome/aioesphomeapi/blob/v46.3.0/aioesphomeapi/client.py): provides `noise_encryption_set_key` and documents
  the initial provisioning handshake.
