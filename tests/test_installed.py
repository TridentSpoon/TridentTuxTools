import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tuxtools import core, installed


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.entry = core.Entry("Portable", "appimage", "https://example.org/app.AppImage")
        self.executable = self.root / "app"
        self.executable.write_text("original")
        self.executable.chmod(0o755)
        self.info = installed.Installation(True, command=[str(self.executable)], files=[self.executable], scope="Test application file")
        self.mock = patch.object(installed, "detect", return_value=self.info)
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        self.temporary.cleanup()

    def test_existing_app_without_baseline_is_unverified(self):
        _, report = installed.check(self.entry, self.root)
        self.assertEqual(report.state, "unverified")
        self.assertFalse(installed.record_path(self.entry, self.root).exists())

    def test_saved_checksum_detects_changed_file(self):
        installed.record_install(self.entry, self.root)
        self.assertEqual(installed.check(self.entry, self.root)[1].state, "verified")
        self.executable.write_text("modified")
        self.assertEqual(installed.check(self.entry, self.root)[1].state, "failed")

    def test_missing_recorded_file_is_reported(self):
        installed.record_install(self.entry, self.root)
        extra = self.root / "module.py"
        extra.write_text("data")
        self.info.files.append(extra)
        installed.record_install(self.entry, self.root)
        extra.unlink()
        _, report = installed.check(self.entry, self.root)
        self.assertEqual(report.state, "failed")
        self.assertIn("Missing:", report.text)

    def test_lost_executable_permission_fails(self):
        installed.record_install(self.entry, self.root)
        self.executable.chmod(0o644)
        self.assertEqual(installed.check(self.entry, self.root)[1].state, "failed")

    def test_new_app_file_detected(self):
        installed.record_install(self.entry, self.root)
        added = self.root / "added.py"
        added.write_text("unexpected")
        self.info.files.append(added)
        self.assertIn("New file:", installed.check(self.entry, self.root)[1].text)

    def test_package_verify_output_is_not_ignored(self):
        import subprocess
        entry = core.Entry("Test", "package", "test")
        with patch.object(core, "package_manager", return_value="apt-get"), patch.object(installed, "query", return_value=subprocess.CompletedProcess([], 0, "changed file", "")):
            self.assertEqual(installed.check(entry, self.root)[1].state, "failed")

    def test_quoted_launcher_paths_and_field_codes(self):
        desktop = self.root / "app.desktop"
        desktop.write_text('[Desktop Entry]\nType=Application\nName=Test\nExec="/path with spaces/app" %F\n')
        info = installed.desktop_installation(desktop)
        self.assertEqual(info.command, ["/path with spaces/app"])
        self.assertTrue(info.found)


class DetectionTests(unittest.TestCase):
    def test_downloaded_repository_is_not_an_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entry = core.DEFAULTS[0]
            (core.checkout(entry, root) / ".git").mkdir(parents=True)
            with patch.object(installed, "desktop_paths", return_value=[root / "applications"]):
                self.assertFalse(installed.detect(entry, root).found)

    def test_external_cursor_desktop_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "external.desktop").write_text('[Desktop Entry]\nName=Cursor\nExec=/usr/bin/true\n')
            entry = next(e for e in core.DEFAULTS if e.name == "Cursor")
            with patch.object(installed, "desktop_paths", return_value=[root]):
                self.assertEqual(installed.detect(entry, root).desktop, root / "external.desktop")
