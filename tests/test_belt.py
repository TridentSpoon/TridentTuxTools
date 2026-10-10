import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from tuxtools import gaming, powershell


class BeltTests(unittest.TestCase):
    def test_powershell_asset_architecture_and_digest(self):
        asset = {"name": "powershell-7.6.6-linux-x64.tar.gz", "browser_download_url": "https://github.com/PowerShell/PowerShell/releases/download/v7.6.6/powershell-7.6.6-linux-x64.tar.gz", "digest": "sha256:" + "a" * 64}
        self.assertEqual(powershell.select_asset({"assets": [asset]}, "x86_64"), (asset, "a" * 64))
        with self.assertRaises(ValueError):
            powershell.select_asset({"assets": [asset]}, "aarch64")
        asset["digest"] = None
        with self.assertRaises(ValueError):
            powershell.select_asset({"assets": [asset]}, "x86_64")

    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / "unsafe.tar.gz"
            with tarfile.open(archive, "w:gz") as stream:
                member = tarfile.TarInfo("../escaped")
                member.size = 4
                stream.addfile(member, io.BytesIO(b"data"))
            with self.assertRaises(ValueError):
                powershell.extract(archive, root / "runtime")
            self.assertFalse((root / "escaped").exists())

    def test_gaming_status_never_registers_app_as_game(self):
        library = Mock()
        for result, expected in [(0, False), (1, True), (2, True), (-1, None)]:
            library.real_gamemode_query_status.return_value = result
            with patch.object(gaming.ctypes, "CDLL", return_value=library):
                self.assertEqual(gaming.active(), expected)
        library.real_gamemode_request_start.assert_not_called()

    def test_missing_gamemode_is_normal(self):
        with patch.object(gaming.ctypes, "CDLL", side_effect=OSError):
            self.assertIsNone(gaming.active())
