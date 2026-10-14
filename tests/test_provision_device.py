"""Offline protocol and interrupted-setup regression checks (not panel proof)."""

import asyncio
import base64
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from aioesphomeapi import TextInfo, TextState
from aioesphomeapi.core import APIConnectionError, ZERO_NOISE_PSK
from tools import provision_device as setup


def response_packet(kind, payload):
    frame = b"IMPROV" + bytes([1, kind, len(payload)]) + payload
    return frame + bytes([sum(frame) & 255])


class ProtocolTests(unittest.TestCase):
    def test_consecutive_requests_leave_a_boundary_for_the_device_parser(self):
        class Port:
            def __init__(self):
                self.ready = True
                self.incoming = bytearray()

            @property
            def in_waiting(self):
                return len(self.incoming)

            def write(self, packet):
                if self.ready:
                    self.incoming.extend(response_packet(4, b"\x03\x02\x01x"))
                # ESPHome retains a complete request until a non-frame byte or timeout.
                self.ready = packet.endswith(b"\n")

            def flush(self):
                pass

            def read(self, count):
                data = bytes(self.incoming[:count])
                del self.incoming[:count]
                return data

        client = setup.ImprovClient(Port())
        self.assertEqual(client.request(3, timeout=0.01), ["x"])
        self.assertEqual(client.request(3, timeout=0.01), ["x"])

    def test_device_info_request_matches_wire_protocol(self):
        self.assertEqual(setup.rpc_frame(3), bytes.fromhex("494d50524f560103020300e6"))

    def test_fragmented_frames_survive_interleaved_logger_bytes(self):
        reader = setup.FrameReader()
        frame = response_packet(1, b"\x04")
        self.assertEqual(reader.feed(b"[I] boot\r\n" + frame[:4]), [])
        self.assertEqual(reader.feed(frame[4:9]), [])
        self.assertEqual(reader.feed(frame[9:] + b"[I] online\n"), [(1, b"\x04")])

    def test_bad_checksum_and_version_do_not_hide_the_next_valid_frame(self):
        frame = response_packet(1, b"\x04")
        damaged = frame[:-1] + b"\x00"
        wrong_version = frame[:6] + b"\x02" + frame[7:]
        self.assertEqual(setup.FrameReader().feed(damaged + wrong_version + frame), [(1, b"\x04")])

    def test_utf8_string_lengths_are_byte_lengths(self):
        # A UTF-8 SSID occupies three bytes; the empty password adds one length byte.
        self.assertEqual(setup.rpc_frame(1, "灯", "")[9:-1], b"\x01\x05\x03\xe7\x81\xaf\x00")
        self.assertEqual(setup.rpc_strings(b"\x03\x04\x03\xe7\x81\xaf"), (3, ["灯"]))

    def test_real_device_info_allows_the_library_zero_footer(self):
        # Captured from the flashed 2026.9.1 device; the outer checksum is valid.
        payload = bytes.fromhex(
            "0340186c6f766534797a702e65313030332d64617368626f61726405302e312e30"
            "0845535033322d53331772657465726d696e616c2d65313030332d63303061333800"
        )
        self.assertEqual(setup.rpc_strings(payload), (3, [
            setup.PROJECT, "0.1.0", "ESP32-S3", "reterminal-e1003-c00a38",
        ]))
        for tail in (b"\x01", b"\x00\x00"):
            with self.subTest(tail=tail), self.assertRaises(setup.SetupError):
                setup.rpc_strings(payload[:-1] + tail)

    def test_truncated_response_and_oversized_request_are_rejected(self):
        with self.assertRaises(setup.SetupError):
            setup.rpc_strings(b"\x03\x02\x05x")
        with self.assertRaises(setup.SetupError):
            setup.rpc_frame(1, "x" * 253)

    def test_other_control_domains_are_outside_this_setup_workflow(self):
        self.assertEqual(setup.validate_target("light.office"), "light.office")
        for target in ["switch.office", "light.office\n", "light." + "x" * 60]:
            with self.subTest(target=target), self.assertRaises(setup.SetupError):
                setup.validate_target(target)


class SetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_key_activation_delay_is_handled_before_reporting_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "panel.json"
            state = {
                "project": setup.PROJECT, "name": "reterminal-e1003-aabbcc",
                "api_key": base64.b64encode(b"b" * 32).decode(),
            }
            peer = {"assigned": False, "new_key_attempts": 0}

            class Client:
                def __init__(self, key):
                    self.key = key

                async def connect(self, **kwargs):
                    if self.key == ZERO_NOISE_PSK and not peer["assigned"]:
                        return
                    if self.key == state["api_key"] and peer["assigned"]:
                        peer["new_key_attempts"] += 1
                        if peer["new_key_attempts"] > 1:
                            return
                    raise APIConnectionError("Key activation pending")

                async def disconnect(self):
                    pass

                async def device_info(self):
                    return SimpleNamespace(
                        name=state["name"], project_name=setup.PROJECT,
                        mac_address="00:11:22:aa:bb:cc",
                        api_encryption_provisionable=not peer["assigned"],
                    )

                async def noise_encryption_set_key(self, key):
                    peer["assigned"] = True
                    return True

            with patch.object(setup, "api_client", side_effect=lambda host, record, key: Client(key)):
                await setup.configure_api("192.0.2.1", path, state, verify=False)
            self.assertEqual(setup.load_state(path)["status"], "verified")
            self.assertGreater(peer["new_key_attempts"], 1)

    async def test_interrupted_key_response_can_resume_using_the_saved_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "panel.json"
            state = {
                "project": setup.PROJECT, "name": "reterminal-e1003-aabbcc",
                "api_key": base64.b64encode(b"a" * 32).decode(), "target": "light.office",
            }
            device = {"key": None, "target": "", "drop_response": True}

            class Client:
                def __init__(self, key):
                    self.key = key
                    self.callback = None

                async def connect(self, **kwargs):
                    accepted = device["key"] or ZERO_NOISE_PSK
                    if self.key != accepted:
                        raise APIConnectionError("Wrong key")

                async def disconnect(self):
                    pass

                async def device_info(self):
                    return SimpleNamespace(
                        name=state["name"], project_name=setup.PROJECT,
                        mac_address="00:11:22:aa:bb:cc",
                        api_encryption_provisionable=device["key"] is None,
                    )

                async def noise_encryption_set_key(self, key):
                    # The local recovery record must already exist if this reply is lost.
                    self_test.assertEqual(setup.load_state(path)["api_key"], key.decode())
                    device["key"] = key.decode()
                    if device["drop_response"]:
                        device["drop_response"] = False
                        raise APIConnectionError("Disconnected after saving")
                    return True

                async def list_entities_services(self):
                    return [TextInfo(key=1, name="Main light target")], []

                def subscribe_states(self, callback):
                    self.callback = callback
                    callback(TextState(key=1, state=device["target"]))

                def text_command(self, key, target):
                    device["target"] = target
                    self.callback(TextState(key=key, state=target))

            self_test = self
            with patch.object(setup, "api_client", side_effect=lambda host, record, key: Client(key)):
                with self.assertRaises(APIConnectionError):
                    await setup.configure_api("192.0.2.1", path, state, verify=False)
                recovered = setup.load_state(path, state["name"])
                self.assertEqual(recovered["status"], "key_pending")
                await setup.configure_api("192.0.2.1", path, recovered, verify=False)
                self.assertEqual(device["target"], "light.office")
                await setup.configure_api("192.0.2.1", path, recovered, verify=True)
                self.assertEqual(setup.load_state(path)["status"], "verified")
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    async def test_wrong_device_identity_is_rejected(self):
        info = SimpleNamespace(name="reterminal-e1003-112233", project_name=setup.PROJECT)
        with self.assertRaises(setup.SetupError):
            setup.check_identity(info, "reterminal-e1003-aabbcc")
        info = SimpleNamespace(name="reterminal-e1003-aabbcc", project_name=setup.PROJECT,
                               mac_address="00:11:22:11:22:33")
        with self.assertRaises(setup.SetupError):
            setup.check_identity(info, info.name, "00:11:22:aa:bb:cc")


if __name__ == "__main__":
    unittest.main()
