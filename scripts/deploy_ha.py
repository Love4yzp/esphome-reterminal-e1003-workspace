#!/usr/bin/env python3
"""Deploy the E1003 blueprint and light automation over the Home Assistant API.

This path needs no SSH access and no writable ``/config`` directory. It uses
the same interfaces as the Home Assistant frontend:

* ``POST /auth/login_flow`` and ``POST /auth/token`` for a short-lived token;
* the WebSocket ``blueprint/save`` command to install the blueprint;
* ``POST /api/config/automation/config/<id>`` to create the automation.

The operation is idempotent. An existing automation is updated only when it
was created from the same blueprint and either keeps the same alias or carries
this script's marker; anything else is reported as a conflict and left
untouched.

    export HA_URL=http://homeassistant.local:8123
    export HA_USERNAME=your-user
    export HA_PASSWORD=your-password
    uv run python scripts/deploy_ha.py --list
    uv run python scripts/deploy_ha.py --light light.desk_lamp --trigger

``HA_TOKEN`` can be used instead of a username and password. Credentials are
never written to disk.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
BLUEPRINT_FILE = REPO / "ha" / "blueprints" / "automation" / "e1003_light_sync.yaml"
BLUEPRINT_NAME = "E1003: connect one light to the panel"
DEFAULT_BLUEPRINT_PATH = "e1003/e1003_light_sync.yaml"
DEFAULT_AUTOMATION_ID = "e1003_light_sync_001"
DEFAULT_ALIAS = "E1003 panel light sync"
MANAGED_MARKER = "scripts/deploy_ha.py"
DEFAULT_URL = "http://homeassistant.local:8123"

ENTITY_SPECS = {
    "command": ("sensor", "_main_light_command"),
    "state": ("text", "_main_light_state"),
    "value": ("text", "_main_light_value"),
}


class HaError(RuntimeError):
    """A Home Assistant request failed in a user-actionable way."""


class HaHttpError(HaError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


class HaClient:
    def __init__(self, base_url: str, token: str, timeout: float, insecure: bool) -> None:
        self.token = token
        self.timeout = timeout
        parsed = urllib.parse.urlsplit(base_url.rstrip("/"))
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise HaError(f"Invalid Home Assistant URL: {base_url}")
        self.scheme = parsed.scheme
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == "https" else 8123)
        self.path_prefix = parsed.path.rstrip("/")
        self.origin = f"{parsed.scheme}://{parsed.netloc}"
        self.base_url = self.origin + self.path_prefix
        self.insecure = insecure

        handlers: list[urllib.request.BaseHandler] = []
        if insecure:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=context))
        self.opener = urllib.request.build_opener(*handlers)

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        form: bool = False,
        token: str | None = None,
    ) -> Any:
        url = f"{self.origin}{self.path_prefix}{path}"
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            if form:
                data = urllib.parse.urlencode(payload).encode()
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                data = json.dumps(payload).encode()
                headers["Content-Type"] = "application/json"
        auth_token = self.token if token is None else token
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        request = urllib.request.Request(
            url, data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read().decode()
        except urllib.error.HTTPError as err:
            body = err.read().decode(errors="replace")
            raise HaHttpError(err.code, body) from err
        except urllib.error.URLError as err:
            raise HaError(f"Cannot reach {url}: {err.reason}") from err

        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as err:
            raise HaError(f"Expected JSON from {url}, got: {body[:200]}") from err

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("POST", path, payload)


def login(client: HaClient, username: str, password: str) -> str:
    """Run the browser login flow and return a short-lived access token."""
    client_id = client.base_url + "/"
    flow = client.request(
        "POST",
        "/auth/login_flow",
        {
            "client_id": client_id,
            "handler": ["homeassistant", None],
            "redirect_uri": client_id,
        },
        token="",
    )
    if not isinstance(flow, dict) or "flow_id" not in flow:
        raise HaError(f"Unexpected login flow response: {flow}")

    result = client.request(
        "POST",
        f"/auth/login_flow/{flow['flow_id']}",
        {"client_id": client_id, "username": username, "password": password},
        token="",
    )
    if not isinstance(result, dict) or "result" not in result:
        raise HaError(
            "Login failed. Check HA_USERNAME/HA_PASSWORD; "
            f"Home Assistant answered: {result}"
        )

    token_response = client.request(
        "POST",
        "/auth/token",
        {
            "grant_type": "authorization_code",
            "code": result["result"],
            "client_id": client_id,
        },
        form=True,
        token="",
    )
    if not isinstance(token_response, dict) or "access_token" not in token_response:
        raise HaError(f"Token exchange failed: {token_response}")
    return str(token_response["access_token"])


class HaWebSocket:
    """Minimal WebSocket client for the blueprint commands."""

    def __init__(self, client: HaClient, token: str) -> None:
        self.client = client
        self.token = token
        self.sock: socket.socket | None = None
        self._next_id = 1

    def __enter__(self) -> "HaWebSocket":
        self._connect()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._close()

    def _connect(self) -> None:
        raw = socket.create_connection(
            (self.client.host, self.client.port), timeout=self.client.timeout
        )
        if self.client.scheme == "https":
            context = ssl.create_default_context()
            if self.client.insecure:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            raw = context.wrap_socket(raw, server_hostname=self.client.host)
        raw.settimeout(self.client.timeout)
        self.sock = raw

        key = base64.b64encode(secrets.token_bytes(16)).decode()
        ws_path = f"{self.client.path_prefix}/api/websocket"
        host_header = self.client.host
        if (self.client.scheme == "http" and self.client.port != 80) or (
            self.client.scheme == "https" and self.client.port != 443
        ):
            host_header = f"{host_header}:{self.client.port}"
        request = (
            f"GET {ws_path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Origin: {self.client.base_url}\r\n"
            "\r\n"
        )
        raw.sendall(request.encode())

        response = bytearray()
        while not response.endswith(b"\r\n\r\n"):
            chunk = raw.recv(1)
            if not chunk:
                raise HaError("Home Assistant closed the WebSocket handshake")
            response.extend(chunk)
        status_line = bytes(response).split(b"\r\n", 1)[0].decode(errors="replace")
        if " 101 " not in status_line:
            raise HaError(f"WebSocket upgrade failed: {status_line}")

        hello = self._recv_json()
        if hello.get("type") != "auth_required":
            raise HaError(f"Unexpected WebSocket greeting: {hello}")
        self._send_json({"type": "auth", "access_token": self.token})
        auth = self._recv_json()
        if auth.get("type") != "auth_ok":
            raise HaError(f"WebSocket authentication failed: {auth}")

    def _close(self) -> None:
        if self.sock is None:
            return
        try:
            self._send_frame(0x8, b"")
        except OSError:
            pass
        self.sock.close()
        self.sock = None

    def _recv_exact(self, size: int) -> bytes:
        assert self.sock is not None
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.sock.recv(size - len(chunks))
            if not chunk:
                raise HaError("WebSocket closed unexpectedly")
            chunks.extend(chunk)
        return bytes(chunks)

    def _recv_frame(self) -> tuple[bool, int, bytes]:
        first, second = self._recv_exact(2)
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return fin, opcode, payload

    def _recv_message(self) -> str | None:
        fragments = bytearray()
        while True:
            fin, opcode, payload = self._recv_frame()
            if opcode == 0x8:
                return None
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x0, 0x1, 0x2):
                fragments.extend(payload)
                if fin:
                    return fragments.decode()
            else:
                raise HaError(f"Unsupported WebSocket opcode: {opcode}")

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        assert self.sock is not None
        mask = secrets.token_bytes(4)
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def _send_json(self, payload: dict[str, Any]) -> None:
        self._send_frame(0x1, json.dumps(payload).encode())

    def _recv_json(self) -> dict[str, Any]:
        message = self._recv_message()
        if message is None:
            raise HaError("WebSocket closed before a response arrived")
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError as err:
            raise HaError(f"Unexpected WebSocket payload: {message[:200]}") from err
        if not isinstance(parsed, dict):
            raise HaError(f"Unexpected WebSocket payload: {message[:200]}")
        return parsed

    def command(self, command_type: str, **kwargs: Any) -> Any:
        command_id = self._next_id
        self._next_id += 1
        self._send_json({"id": command_id, "type": command_type, **kwargs})
        while True:
            message = self._recv_json()
            if message.get("id") != command_id:
                continue
            if message.get("type") == "result" and message.get("success"):
                return message.get("result")
            raise HaError(
                f"WebSocket command {command_type} failed: {message.get('error')}"
            )


def find_entities(
    states: list[dict[str, Any]], panel_filter: str | None
) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for role, (domain, suffix) in ENTITY_SPECS.items():
        candidates = [
            state
            for state in states
            if state["entity_id"].endswith(suffix)
            and state["entity_id"].startswith(f"{domain}.")
        ]
        if panel_filter:
            needle = panel_filter.lower()
            candidates = [
                state
                for state in candidates
                if needle in state["entity_id"].lower()
                or needle
                in str(state.get("attributes", {}).get("friendly_name", "")).lower()
            ]
        if not candidates:
            raise HaError(
                f"No {role} {domain} entity ending in {suffix} was found. "
                "Check that the E1003 is connected and use --panel to select a device."
            )
        if len(candidates) > 1:
            names = ", ".join(state["entity_id"] for state in candidates)
            raise HaError(
                f"Multiple {role} entities matched: {names}. "
                "Use --panel with part of the device or entity name."
            )
        found[role] = candidates[0]

    device_stems = {
        state["entity_id"].split(".", 1)[1][: -len(ENTITY_SPECS[role][1])]
        for role, state in found.items()
    }
    if len(device_stems) != 1:
        raise HaError(
            "The three panel entities do not belong to the same device: "
            + ", ".join(state["entity_id"] for state in found.values())
        )
    return found


def automation_entity_id(
    states: list[dict[str, Any]], automation_id: str
) -> str | None:
    for state in states:
        if state["entity_id"].startswith("automation.") and state.get(
            "attributes", {}
        ).get("id") == automation_id:
            return state["entity_id"]
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy the E1003 blueprint and light automation over the HA API."
    )
    parser.add_argument("--url", default=os.getenv("HA_URL", DEFAULT_URL))
    parser.add_argument("--token", default=os.getenv("HA_TOKEN"))
    parser.add_argument("--username", default=os.getenv("HA_USERNAME"))
    parser.add_argument("--password", default=os.getenv("HA_PASSWORD"))
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification (self-signed Home Assistant certificates).",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument(
        "--light",
        help="Home Assistant light entity id to bind to the panel.",
    )
    parser.add_argument(
        "--panel",
        help="Part of the panel/device name when several E1003 panels are present.",
    )
    parser.add_argument("--automation-id", default=DEFAULT_AUTOMATION_ID)
    parser.add_argument("--alias", default=DEFAULT_ALIAS)
    parser.add_argument("--blueprint-path", default=DEFAULT_BLUEPRINT_PATH)
    parser.add_argument(
        "--update-blueprint",
        action="store_true",
        help="Overwrite the blueprint at the resolved path with the repository copy.",
    )
    parser.add_argument(
        "--trigger",
        action="store_true",
        help="Run the automation once after deploying so the card updates immediately.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and print the plan without changing Home Assistant.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List panel text entities, lights, blueprints, and automations, then exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = HaClient(args.url, args.token or "", args.timeout, args.insecure)

    token = args.token
    if not token:
        if not args.username or not args.password:
            print(
                "Set HA_TOKEN, or HA_USERNAME and HA_PASSWORD, or pass --token/--username/--password.",
                file=sys.stderr,
            )
            return 1
        try:
            token = login(client, args.username, args.password)
        except HaError as err:
            print(f"Login failed: {err}", file=sys.stderr)
            return 1
    client.token = token

    try:
        config = client.get("/api/config")
        states = client.get("/api/states")
        if not isinstance(config, dict) or not isinstance(states, list):
            raise HaError("Unexpected response from /api/config or /api/states")
        print(f"Home Assistant {config.get('version')} at {args.url}")

        blueprint_yaml = BLUEPRINT_FILE.read_text()
        with HaWebSocket(client, token) as websocket:
            blueprints = websocket.command("blueprint/list", domain="automation")
            if not isinstance(blueprints, dict):
                raise HaError("Unexpected blueprint/list response")

            matching_paths = [
                path
                for path, item in blueprints.items()
                if item.get("metadata", {}).get("name") == BLUEPRINT_NAME
            ]
            if args.blueprint_path in blueprints:
                blueprint_path = args.blueprint_path
            elif len(matching_paths) == 1:
                blueprint_path = matching_paths[0]
            elif len(matching_paths) > 1:
                raise HaError(
                    "Several blueprints use the E1003 name: "
                    + ", ".join(sorted(matching_paths))
                )
            else:
                blueprint_path = args.blueprint_path

            panel_entities = find_entities(states, args.panel)
            existing_automation = None
            try:
                existing_automation = client.get(
                    f"/api/config/automation/config/{urllib.parse.quote(args.automation_id)}"
                )
            except HaHttpError as err:
                if err.status != 404:
                    raise

            if args.list:
                print("\nPanel entities:")
                for role, state in panel_entities.items():
                    print(f"  {role:6} {state['entity_id']}")

                lights = sorted(
                    state["entity_id"]
                    for state in states
                    if state["entity_id"].startswith("light.")
                    and "buzzer" not in state["entity_id"]
                )
                print("\nLights:")
                for entity_id in lights:
                    print(f"  {entity_id}")

                print("\nE1003 blueprints:")
                for path in sorted(
                    set(matching_paths)
                    | ({args.blueprint_path} if args.blueprint_path in blueprints else set())
                ):
                    print(f"  {path}")

                automations = [
                    state
                    for state in states
                    if state["entity_id"].startswith("automation.")
                ]
                print("\nAutomations:")
                for state in automations:
                    print(
                        f"  {state['attributes'].get('id')} -> "
                        f"{state['entity_id']} ({state['attributes'].get('friendly_name')})"
                    )
                return 0

            if not args.light:
                raise HaError(
                    "--light is required. Run with --list to see available lights."
                )
            if not any(state["entity_id"] == args.light for state in states):
                raise HaError(f"Light entity not found in Home Assistant: {args.light}")

            if blueprint_path in blueprints and not args.update_blueprint:
                print(f"Blueprint already present: {blueprint_path}")
            else:
                print(f"Saving blueprint: {blueprint_path}")
                if not args.dry_run:
                    result = websocket.command(
                        "blueprint/save",
                        domain="automation",
                        path=blueprint_path,
                        yaml=blueprint_yaml,
                        # Required by HA to replace an installed copy.
                        allow_override=blueprint_path in blueprints,
                    )
                    print(f"  overrides_existing={result.get('overrides_existing')}")

        if existing_automation is not None:
            existing_path = (
                existing_automation.get("use_blueprint", {}).get("path")
                if isinstance(existing_automation, dict)
                else None
            )
            existing_description = ""
            if isinstance(existing_automation, dict):
                existing_description = existing_automation.get("description") or ""
            managed_by_script = MANAGED_MARKER in existing_description
            if (
                existing_path != blueprint_path
                or not (
                    managed_by_script or existing_automation.get("alias") == args.alias
                )
            ):
                raise HaError(
                    f"Automation id {args.automation_id!r} already exists and does not "
                    "look like this deployer's automation. Choose another "
                    "--automation-id instead of overwriting it."
                )
            print(
                f"Updating existing automation: {args.automation_id} "
                f"({existing_automation.get('alias')})"
            )
        else:
            for state in states:
                if (
                    state["entity_id"].startswith("automation.")
                    and state.get("attributes", {}).get("friendly_name") == args.alias
                ):
                    raise HaError(
                        f"Automation alias {args.alias!r} is already used by "
                        f"{state['entity_id']}. Choose another --alias or --automation-id."
                    )
            print(f"Creating automation: {args.automation_id}")

        automation_config = {
            "id": args.automation_id,
            "alias": args.alias,
            "description": (
                "E1003 panel light card sync, instantiated from "
                f"{blueprint_path} by {MANAGED_MARKER}"
            ),
            "use_blueprint": {
                "path": blueprint_path,
                "input": {
                    "light_entity": args.light,
                    "panel_command": panel_entities["command"]["entity_id"],
                    "panel_state": panel_entities["state"]["entity_id"],
                    "panel_value": panel_entities["value"]["entity_id"],
                },
            },
        }

        if args.dry_run:
            print("\nDry run; automation payload:")
            print(json.dumps(automation_config, indent=2, ensure_ascii=False))
            return 0

        client.post(
            f"/api/config/automation/config/{urllib.parse.quote(args.automation_id)}",
            automation_config,
        )
        print(f"Automation saved: {args.automation_id}")

        if args.trigger:
            entity_id = None
            for _ in range(10):
                states = client.get("/api/states")
                entity_id = automation_entity_id(states, args.automation_id)
                if entity_id:
                    break
                time.sleep(0.5)
            if not entity_id:
                print(
                    "Automation was saved but its entity has not loaded yet; "
                    "reload automations or trigger it later.",
                    file=sys.stderr,
                )
                return 0
            client.post("/api/services/automation/trigger", {"entity_id": entity_id})
            print(f"Triggered {entity_id}")

        print(
            "Done. Panel entities: "
            + ", ".join(
                f"{role}={state['entity_id']}" for role, state in panel_entities.items()
            )
        )
        return 0
    except HaError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2 if "already exists" in str(err) else 1


if __name__ == "__main__":
    raise SystemExit(main())
