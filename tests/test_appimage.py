import unittest
import sys
import io
from contextlib import redirect_stdout
from unittest.mock import patch
from tuxtools import appimage, powershell
from tuxtools.appimage import resolve_url


class AppImageTests(unittest.TestCase):
    def test_packaged_installers_expose_cli_entrypoints(self):
        for module in (appimage, powershell):
            with patch.object(sys, "argv", ["helper", "--help"]), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    module.main()
                self.assertEqual(result.exception.code, 0)

    def test_tls_uses_system_trust_store(self):
        import os
        from tuxtools import runtime
        with patch.dict(os.environ, {}, clear=True), patch("pathlib.Path.is_file", return_value=True), patch("ssl.create_default_context") as context:
            runtime.tls_context()
            context.assert_called_once_with(cafile="/etc/ssl/certs/ca-certificates.crt")
        with patch.dict(os.environ, {"SSL_CERT_FILE": "/custom/ca.pem"}), patch("ssl.create_default_context") as context:
            runtime.tls_context()
            context.assert_called_once_with()

    def test_cursor_selects_current_architecture(self):
        html = '<a href="https://api2.cursor.sh/arm">Linux AppImage (ARM64)</a><a href="https://api2.cursor.sh/x64">Linux AppImage (x64)</a>'
        self.assertEqual(resolve_url("https://cursor.com/download", "x64", lambda _: html), "https://api2.cursor.sh/x64")
        self.assertEqual(resolve_url("https://cursor.com/download", "arm64", lambda _: html), "https://api2.cursor.sh/arm")

    def test_cursor_missing_download_reports_error(self):
        with self.assertRaises(ValueError):
            resolve_url("https://cursor.com/download", "x64", lambda _: "Maintenance")

    def test_tmog_arm64_download(self):
        source = "https://tmog.org/rtm/downloads/TaskManagerOG-1.0.0-x86_64.AppImage"
        self.assertEqual(resolve_url(source, "arm64", None), source.replace("x86_64", "aarch64"))
