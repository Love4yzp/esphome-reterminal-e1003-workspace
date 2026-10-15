#!/usr/bin/env python3
"""Maintainer proof of serial Wi-Fi setup and native API key provisioning.

This does not flash firmware or install HA automations. Run through `uv run`.
Wi-Fi passwords are prompted and never stored. API keys stay in a private file.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import time
from urllib.parse import urlparse

from aioesphomeapi import APIClient, TextInfo, TextState
from aioesphomeapi.core import APIConnectionError, ZERO_NOISE_PSK
import serial

PROJECT = "love4yzp.e1003-dashboard"
HEADER = b"IMPROV"
RPC_COMMAND = 3
RPC_RESULT = 4


class SetupError(Exception):
    """A setup failure that can be shown without exposing credentials."""


def rpc_frame(command: int, *values: str) -> bytes:
    data = bytearray()
    for value in values:
        encoded = value.encode("utf-8")
        if len(encoded) > 255:
            raise SetupError("Improv string exceeds the protocol length limit")
        data.extend(bytes([len(encoded)]) + encoded)
    if len(data) > 253:
        raise SetupError("Improv request exceeds the protocol length limit")
    payload = bytes([command, len(data)]) + data
    frame = HEADER + bytes([1, RPC_COMMAND, len(payload)]) + payload
    return frame + bytes([sum(frame) & 255])


class FrameReader:
    """Separate checksum-verified Improv frames from a fragmented log stream."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        self.buffer.extend(data)
        frames = []
        while True:
            start = self.buffer.find(HEADER)
            if start < 0:
                # Preserve a possible partial header across serial reads.
                self.buffer = self.buffer[-5:]
                break
            del self.buffer[:start]
            if len(self.buffer) < 9:
                break
            if self.buffer[6] != 1:
                del self.buffer[0]
                continue
            size = 10 + self.buffer[8]
            if len(self.buffer) < size:
                break
            frame = self.buffer[:size]
            if sum(frame[:-1]) & 255 != frame[-1]:
                del self.buffer[0]
                continue
            frames.append((frame[7], bytes(frame[9:-1])))
            del self.buffer[:size]
        return frames


def rpc_strings(payload: bytes) -> tuple[int, list[str]]:
    # Improv's finish(false) appends a zero footer outside its data length.
    # Accept only that exact library form; the outer frame checksum was verified.
    if len(payload) >= 3 and payload[1] == len(payload) - 3 and payload[-1] == 0:
        payload = payload[:-1]
    if len(payload) < 2 or payload[1] != len(payload) - 2:
        raise SetupError("Malformed Improv response length")
    result = []
    index = 2
    while index < len(payload):
        end = index + 1 + payload[index]
        if end > len(payload):
            raise SetupError("Truncated Improv response string")
        try:
            result.append(payload[index + 1:end].decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise SetupError("Invalid UTF-8 in Improv response") from exc
        index = end
    return payload[0], result


class ImprovClient:
    def __init__(self, port: serial.Serial) -> None:
        self.port = port
        self.reader = FrameReader()

    def request(self, command: int, *values: str, timeout: float = 15) -> list[str]:
        # A separator clears ESPHome's completed receive frame immediately.
        # Without it, a following request inside the 100 ms timeout loses its header.
        self.port.write(rpc_frame(command, *values) + b"\n")
        self.port.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for kind, payload in self.reader.feed(
                self.port.read(min(max(self.port.in_waiting, 1), 4096))
            ):
                if kind == 2 and payload and payload[0]:
                    raise SetupError(f"Improv returned error code {payload[0]}")
                if kind == RPC_RESULT:
                    response_command, strings = rpc_strings(payload)
                    if response_command == command:
                        return strings
        raise SetupError("Improv timed out; check the serial port or reconnect power")


def validate_target(target: str) -> str:
    if not re.fullmatch(r"light\.[a-z0-9_]+", target) or len(target) > 63:
        raise SetupError("Target must be a light entity ID of at most 63 characters")
    return target


def check_identity(info, name: str, mac: str | None = None) -> None:
    if info.name != name or info.project_name != PROJECT:
        raise SetupError("API device identity does not match the USB release firmware")
    if mac and info.mac_address.lower() != mac.lower():
        raise SetupError("API device MAC does not match the saved device")


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".setup-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load_state(path: Path, expected_name: str | None = None) -> dict:
    state = json.loads(path.read_text())
    if state.get("api_key"):
        key = base64.b64decode(state["api_key"], validate=True)
        if len(key) != 32 or not any(key):
            raise SetupError("Saved API key is invalid")
    elif state.get("encrypt_api", False):
        raise SetupError("Encrypted setup needs its saved API key")
    if state.get("project") != PROJECT or not re.fullmatch(
        r"reterminal-e1003-[0-9a-f]{6}", state.get("name", "")
    ):
        raise SetupError("Saved device identity is invalid")
    if expected_name and state["name"] != expected_name:
        raise SetupError("State file belongs to a different USB device")
    return state


def api_client(host: str, state: dict, key: str | None) -> APIClient:
    mac = state.get("mac")
    return APIClient(
        host, 6053, noise_psk=key, expected_name=state["name"],
        expected_mac=mac.lower().replace(":", "") if mac else None,
        client_info="E1003 maintainer setup",
        provide_time=False,
    )


async def read_target(client: APIClient, target: str, write: bool) -> None:
    entities, _ = await client.list_entities_services()
    matches = [
        item for item in entities
        if isinstance(item, TextInfo)
        and (item.name == "Main light target" or item.name.endswith(" Main light target"))
    ]
    if len(matches) != 1:
        raise SetupError("Release target text entity was not uniquely identified")
    key = matches[0].key
    received = asyncio.Event()

    def on_state(state) -> None:
        if isinstance(state, TextState) and state.key == key and state.state == target:
            received.set()

    client.subscribe_states(on_state)
    if write:
        client.text_command(key, target)
    await asyncio.wait_for(received.wait(), timeout=10)


async def configure_api(host: str, path: Path, state: dict, *, verify: bool) -> None:
    if state.get("encrypt_api", bool(state.get("api_key"))):
        await _configure_encrypted_api(host, path, state, verify=verify)
        return
    client = api_client(host, state, None)
    try:
        await client.connect(log_errors=False)
    except APIConnectionError:
        await client.disconnect()
        if verify or not state.get("api_key"):
            raise SetupError("Keyless reconnect failed; check the device or its existing key record")
        # Explicitly switching an existing panel to the reference default.
        # Keep its recovery key until a plaintext reconnect succeeds.
        client = api_client(host, state, state["api_key"])
        try:
            await client.connect(log_errors=False)
            info = await client.device_info()
            check_identity(info, state["name"], state.get("mac"))
            if not await client.noise_encryption_set_key(b""):
                raise SetupError("Device refused to disable API encryption")
        finally:
            await client.disconnect()
        for attempt in range(4):
            await asyncio.sleep(0.2)
            client = api_client(host, state, None)
            try:
                await client.connect(log_errors=False)
                break
            except APIConnectionError:
                await client.disconnect()
                if attempt == 3:
                    raise SetupError("Keyless connection did not become active; retry with the saved record")
    try:
        info = await client.device_info()
        check_identity(info, state["name"], state.get("mac"))
        state["mac"] = info.mac_address
        if state.get("target"):
            await read_target(client, state["target"], write=not verify)
        state.update(status="verified", host=host, encrypt_api=False)
        state.pop("api_key", None)
        save_state(path, state)
    finally:
        await client.disconnect()


async def _configure_encrypted_api(host: str, path: Path, state: dict, *, verify: bool) -> None:
    client = api_client(host, state, state["api_key"])
    try:
        await client.connect(log_errors=False)
    except APIConnectionError:
        await client.disconnect()
        if verify:
            raise SetupError("Encrypted reconnect failed; check address and saved key")
        client = api_client(host, state, ZERO_NOISE_PSK)
        try:
            await client.connect(log_errors=False)
            info = await client.device_info()
            check_identity(info, state["name"], state.get("mac"))
            if not info.api_encryption_provisionable:
                raise SetupError("Device is already configured or its setup window has expired")
            state["mac"] = info.mac_address
            state["status"] = "key_pending"
            # Persist before sending: a disconnect after saving the key must be recoverable.
            save_state(path, state)
            if not await client.noise_encryption_set_key(state["api_key"].encode("ascii")):
                raise SetupError("Device refused the API key")
        finally:
            await client.disconnect()
        # ESPHome activates a provisioned key on a delayed scheduler callback.
        # Retry only this expected transition, never the key-setting request.
        for attempt in range(4):
            await asyncio.sleep(0.2)
            client = api_client(host, state, state["api_key"])
            try:
                await client.connect(log_errors=False)
                break
            except APIConnectionError:
                await client.disconnect()
                if attempt == 3:
                    raise SetupError("Provisioned key did not become active; reuse the saved record")
    try:
        info = await client.device_info()
        check_identity(info, state["name"], state.get("mac"))
        state["mac"] = info.mac_address
        if state.get("target"):
            await read_target(client, state["target"], write=not verify)
        state["status"] = "verified"
        state["host"] = host
        save_state(path, state)
    finally:
        await client.disconnect()


def wait_for_network(improv: ImprovClient, timeout: float = 45) -> list[str]:
    # Improv restores PROVISIONED from saved credentials before Wi-Fi rejoins.
    # General network flags report actual connectivity, rather than saved setup.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        flags = improv.request(7)
        if flags and int(flags[0]) & 1:
            return improv.request(2)
        time.sleep(0.5)
    raise SetupError("Saved Wi-Fi did not reconnect; enter new network settings")


def configure_device(args, *, password: str | None = None, keep_wifi: bool = False) -> tuple[Path, dict]:
    """Configure from CLI or a local App adapter without putting passwords in argv."""
    if not keep_wifi:
        ssid = args.ssid or input("Wi-Fi SSID: ").strip()
        if not 1 <= len(ssid.encode("utf-8")) <= 32:
            raise SetupError("Wi-Fi SSID must contain 1 to 32 UTF-8 bytes")
        if password is None:
            password = getpass.getpass("Wi-Fi password (empty for an open network): ")
        if password and not 8 <= len(password.encode("utf-8")) <= 63:
            raise SetupError("Wi-Fi password must contain 8 to 63 UTF-8 bytes")
    target = validate_target(args.target) if args.target else None
    # Keep reset lines inactive when opening the port.
    port = serial.Serial(port=None, baudrate=115200, timeout=0.1, write_timeout=5)
    port.dtr = False
    port.rts = False
    port.port = args.port
    with port:
        if args.reset:
            # The tested WCH bridge can leave the MCU held after port close.
            # Explicit reset also reopens the initial API provisioning window.
            from esptool.reset import HardReset
            HardReset(port)()
            time.sleep(10)
        improv = ImprovClient(port)
        info = improv.request(3)
        if len(info) < 4 or info[0] != PROJECT or not re.fullmatch(
            r"reterminal-e1003-[0-9a-f]{6}", info[3]
        ):
            raise SetupError("USB device is not the expected E1003 release firmware")
        if not getattr(args, "encrypt_api", False):
            version = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", info[1])
            if not version or tuple(map(int, version.groups())) < (0, 2, 1):
                raise SetupError("Keyless reference setup requires firmware 0.2.1 or later")
        name = info[3]
        directory = getattr(args, "state_dir", Path(".esphome/provisioning"))
        path = args.state_file or directory / f"{name}.json"
        if path.exists():
            state = load_state(path, name)
        else:
            state = {"project": PROJECT, "name": name, "status": "new"}
        state["encrypt_api"] = bool(getattr(args, "encrypt_api", False))
        if state["encrypt_api"] and not state.get("api_key"):
            state["api_key"] = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
        if target:
            state["target"] = target
        urls = wait_for_network(improv) if keep_wifi else improv.request(1, ssid, password, timeout=100)
        host = args.host or next(
            (urlparse(url).hostname for url in urls
             if urlparse(url).hostname and urlparse(url).hostname not in ("0.0.0.0", "::")),
            state.get("host") or f"{name}.local",
        )
        on_address = getattr(args, "on_address", None)
        if on_address:
            on_address(host)
    save_state(path, state)
    asyncio.run(asyncio.wait_for(configure_api(host, path, state, verify=False), timeout=45))
    return path, state


def provision(args) -> None:
    path, state = configure_device(args)
    name, host = state["name"], state["host"]
    print(f"API connection verified for {name} at {host}.")
    print(f"Private setup record: {path}")
    print("Allow 65 seconds for text settings to save before resetting, then run verify.")
    print("HA state sync is a separate step.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("provision", help="USB Wi-Fi setup and runtime target")
    setup.add_argument("--port", required=True)
    setup.add_argument("--reset", action="store_true", help="Reset the E1003 through its UART bridge before setup")
    setup.add_argument("--ssid")
    setup.add_argument("--target")
    setup.add_argument("--host", help="Override the device's reported IP/mDNS address")
    setup.add_argument("--state-file", type=Path)
    verify = commands.add_parser("verify", help="Read-only encrypted reconnect and target readback")
    verify.add_argument("--state-file", type=Path, required=True)
    verify.add_argument("--host")
    show = commands.add_parser("show-key", help="Explicitly display the saved key for HA setup")
    show.add_argument("--state-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "provision":
            provision(args)
        else:
            state = load_state(args.state_file)
            if args.command == "show-key":
                print(state.get("api_key") or "No API key configured.")
            else:
                host = args.host or state.get("host") or f"{state['name']}.local"
                asyncio.run(asyncio.wait_for(
                    configure_api(host, args.state_file, state, verify=True), timeout=45
                ))
                print(f"API reconnect and target readback passed for {state['name']}.")
        return 0
    except (SetupError, APIConnectionError, TimeoutError, serial.SerialException,
            OSError, ValueError, KeyError) as exc:
        # Third-party exception text can contain transport details; keep it out of logs.
        message = str(exc) if isinstance(exc, SetupError) else type(exc).__name__
        print(f"Setup failed: {message}. Reuse the saved state file when retrying.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
