"""Behavior checks for the local App's environment-based configuration adapter."""

import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import app_configure_device as app


class AppConfigurationTests(unittest.TestCase):
    def test_target_only_preserves_network_and_waits_before_reset_verification(self):
        calls = []
        state = {"host": "192.0.2.1", "api_key": "private-key", "name": "panel"}

        def configure(args, **kwargs):
            self.assertTrue(kwargs["keep_wifi"])
            self.assertEqual(args.target, "light.office")
            calls.append("write")
            return Path("record.json"), state

        async def verify(host, path, record, *, verify):
            self.assertTrue(verify)
            self.assertIs(record, state)
            calls.append("verify")

        with patch.object(app.setup, "configure_device", create=True, side_effect=configure), \
             patch.object(app.time, "sleep", side_effect=lambda seconds: calls.append(seconds)), \
             patch.object(app, "reset_panel", side_effect=lambda port: calls.append("reset")), \
             patch.object(app.setup, "configure_api", side_effect=verify), \
             contextlib.redirect_stdout(io.StringIO()):
            app.run({"E1003_USB_PORT": "COM3", "E1003_TARGET": "light.office"})
        self.assertEqual(calls, ["write", 65, "reset", "verify"])

    def test_wifi_password_is_passed_in_memory_and_not_printed(self):
        password = "sentinel-password-123"
        output = io.StringIO()

        def configure(args, *, password, keep_wifi):
            self.assertFalse(keep_wifi)
            self.assertEqual(args.ssid, "test-network")
            self.assertEqual(password, "sentinel-password-123")
            return Path("record.json"), {"host": "192.0.2.1", "api_key": "sentinel-key"}

        async def verify(*args, **kwargs):
            pass

        with patch.object(app.setup, "configure_device", create=True, side_effect=configure), \
             patch.object(app.time, "sleep"), patch.object(app, "reset_panel"), \
             patch.object(app.setup, "configure_api", side_effect=verify), \
             contextlib.redirect_stdout(output):
            app.run({"E1003_USB_PORT": "COM3", "E1003_TARGET": "light.office",
                     "E1003_WIFI_SSID": "test-network", "E1003_WIFI_PASSWORD": password})
        self.assertNotIn(password, output.getvalue())
        self.assertNotIn("sentinel-key", output.getvalue())
        self.assertIn("E1003_CONFIGURATION_SAVED", output.getvalue())

    def test_invalid_target_is_rejected_before_opening_a_device(self):
        with patch.object(app.setup, "configure_device", create=True) as configure:
            with self.assertRaises(app.setup.SetupError):
                app.run({"E1003_USB_PORT": "COM3", "E1003_TARGET": "light.office;touch /tmp/x"})
            configure.assert_not_called()

    def test_failure_output_does_not_echo_third_party_secrets(self):
        output = io.StringIO()
        with patch.object(app, "run", side_effect=RuntimeError("sentinel-key")), \
             contextlib.redirect_stdout(output):
            self.assertEqual(app.main({}), 1)
        self.assertNotIn("sentinel-key", output.getvalue())


if __name__ == "__main__":
    unittest.main()
