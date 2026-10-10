import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tuxtools import updates


class UpdateTests(unittest.TestCase):
    def test_version_comparison_and_source_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            installed, source = root / "installed", root / "source"
            for path, version in ((installed, "0.9.0"), (source, "0.10.0")):
                (path / "tuxtools").mkdir(parents=True)
                (path / "tuxtools/__init__.py").write_text(f'__version__ = "{version}"\n')
            (source / "install.sh").write_text("exit 0")
            (installed / "install-source.json").write_text(json.dumps({"source": str(source)}))
            result = updates.check(installed)
            self.assertTrue(result.newer)
            (source / "tuxtools/__init__.py").write_text('__version__ = "0.8.0"')
            self.assertFalse(updates.check(installed).newer)

    def test_no_version_code_is_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tuxtools").mkdir()
            (root / "tuxtools/__init__.py").write_text('raise RuntimeError("must not run")\n__version__ = "1.2.3"')
            self.assertEqual(updates.read_version(root), "1.2.3")

    def test_missing_original_source_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "install-source.json").write_text(json.dumps({"source": str(root)}))
            with self.assertRaises(ValueError):
                updates.check(root)

    def test_changed_source_cannot_be_applied(self):
        result = updates.Update("0.4.0", "0.5.0", Path("/tmp/source"), True)
        changed = updates.Update("0.4.0", "0.6.0", Path("/tmp/source"), True)
        with patch.object(updates, "check", return_value=changed), patch.object(updates.subprocess, "Popen") as runner:
            with self.assertRaises(ValueError):
                updates.apply(result, lambda _: None)
            runner.assert_not_called()
