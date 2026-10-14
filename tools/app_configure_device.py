#!/usr/bin/env python3
"""Local SenseCraft script-step adapter; inputs arrive only through environment.

The existing locked environment supplies the client for local testing. This is
not a redistributable App dependency bundle. No compiler or YAML editing runs.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import serial
from esptool.reset import HardReset

if __package__:
    from . import provision_device as setup
else:
    import provision_device as setup


ROOT = Path(__file__).resolve().parents[1]


def reset_panel(port_name: str) -> None:
    port = serial.Serial(port=None, baudrate=115200, timeout=0.1)
    port.dtr = False
    port.rts = False
    port.port = port_name
    with port:
        HardReset(port)()
        time.sleep(12)


def run(values: dict) -> None:
    target = setup.validate_target(values.get("E1003_TARGET", ""))
    port = values.get("E1003_USB_PORT", "")
    if not port:
        raise setup.SetupError("Choose the E1003 USB serial port")
    ssid = values.get("E1003_WIFI_SSID", "")
    password = values.get("E1003_WIFI_PASSWORD", "")
    if password and not ssid:
        raise setup.SetupError("Enter a Wi-Fi name when changing its password")
    args = SimpleNamespace(
        port=port, reset=True, ssid=ssid, target=target,
        host=None, state_file=None, state_dir=ROOT / ".esphome/provisioning",
        on_address=lambda host: print(f"Device address for Home Assistant: {host}", flush=True),
    )
    print("Checking the USB identity and applying configuration...", flush=True)
    path, state = setup.configure_device(args, password=password, keep_wifi=not bool(ssid))
    print("Target readback passed. Keeping power connected for 65 seconds to save settings...", flush=True)
    time.sleep(65)
    reset_panel(port)
    asyncio.run(asyncio.wait_for(
        setup.configure_api(state["host"], path, state, verify=True), timeout=45,
    ))
    copy_key = str(values.get("E1003_COPY_KEY", "false")).lower() in ("true", "1", "on")
    if copy_key:
        if sys.platform != "darwin":
            raise setup.SetupError("Key copy in this local adapter requires macOS")
        subprocess.run(["pbcopy"], input=state["api_key"].encode(), check=True)
        print("Device encryption key copied locally for Home Assistant setup.", flush=True)
    print("E1003_CONFIGURATION_SAVED: encrypted reconnect and persisted target verified.", flush=True)


def main(values: dict | None = None) -> int:
    try:
        run(dict(os.environ) if values is None else values)
        return 0
    except Exception as exc:
        # Transport/library messages can include secrets. Only our safe errors
        # are shown; never dump input values or the device recovery record.
        message = str(exc) if isinstance(exc, setup.SetupError) else type(exc).__name__
        print(f"Configuration failed: {message}. Saved key records remain available.", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
