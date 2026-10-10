import unittest
from tuxtools.appimage import resolve_url


class AppImageTests(unittest.TestCase):
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
