import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tuxtools import core


class CoreTests(unittest.TestCase):
    def test_catalogue_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entries = core.load_catalogue(root)
            entries[0].favourite = False
            core.save_catalogue(entries, root)
            self.assertEqual(core.load_catalogue(root), entries)
            self.assertEqual(len(entries), len(core.DEFAULTS))

    def test_reject_options_and_unsafe_paths(self):
        for entry in (core.Entry("Bad", "package", "--help"),
                      core.Entry("Bad", "flatpak", "app;id"),
                      core.Entry("Bad", "git", "file:///tmp/repo"),
                      core.Entry("Bad", "git", "https://example.com/repo", installer="../install.sh")):
            with self.assertRaises(ValueError):
                entry.validate()

    def test_download_never_executes_installer(self):
        with tempfile.TemporaryDirectory() as folder:
            entry = core.DEFAULTS[0]
            command, cwd = core.plan(entry, "download", Path(folder))
            self.assertEqual(command[:3], ["git", "clone", "--"])
            self.assertIsNone(cwd)
            with self.assertRaises(ValueError):
                core.plan(entry, "install", Path(folder))

    def test_symlink_installer_escape_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            outside = root / "outside.sh"
            outside.write_text("exit 0")
            checkout = core.checkout(core.DEFAULTS[0], root)
            checkout.mkdir(parents=True)
            (checkout / "install.sh").symlink_to(outside)
            with self.assertRaises(ValueError):
                core.plan(core.DEFAULTS[0], "install", root)

    def test_package_uses_authentication_and_separate_arguments(self):
        with patch.object(core, "package_manager", return_value="apt-get"), patch.object(core.shutil, "which", return_value="/usr/bin/apt-get"):
            command, cwd = core.plan(core.Entry("Git", "package", "git"), "install")
        self.assertEqual(command, ["pkexec", "/usr/bin/apt-get", "install", "-y", "--", "git"])

    def test_command_failure_is_reported(self):
        lines = []
        with self.assertRaises(RuntimeError):
            core.run_plan(["python3", "-c", "print('failed'); raise SystemExit(2)"], None, lines.append)
        self.assertIn("failed\n", lines)

    def test_old_catalogue_migrates_and_removal_stays_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps([{"name": "Custom", "kind": "package", "source": "git"}]))
            entries = core.load_catalogue(root)
            self.assertEqual(entries[0].category, "Utilities")
            self.assertIn("Gaming", {e.category for e in entries})
            kept = [entry for entry in entries if entry.name != "Steam"]
            core.save_catalogue(kept, root)
            self.assertEqual(core.load_catalogue(root), kept)

    def test_v2_catalogue_adds_public_apps_without_restoring_removed_apps(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = [{"name": "My tool", "kind": "package", "source": "git", "category": "Custom", "favourite": True}]
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 2, "entries": original}))
            entries = core.load_catalogue(root)
            self.assertEqual([e.name for e in entries], ["My tool", "CaramelPopKern", "KamaKiriStudio", *[e.name for e in core.BELT_APPS + core.ADMIN_APPS + core.DEV_APPS + core.EDITOR_APPS + core.CREATIVE_APPS + core.EXTRA_APPS]])
            self.assertTrue(entries[0].favourite)
            self.assertEqual(entries[0].category, "Custom")
            core.save_catalogue(entries[:-1], root)
            self.assertEqual(core.load_catalogue(root), entries[:-1])

    def test_public_apps_use_verified_installers(self):
        for entry in core.PUBLIC_APPS:
            entry.validate()
        caramel, studio = core.PUBLIC_APPS
        self.assertEqual(caramel.installer, "install-gui.sh")
        self.assertFalse(caramel.terminal)
        self.assertEqual(studio.installer, "install.sh")
        self.assertTrue(studio.terminal)

    def test_git_one_click_clones_then_installs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entry = core.DEFAULTS[0]
            steps = core.install_steps(entry, root)
            commands = []

            def fake_run(command, cwd, output):
                commands.append(command)
                if command[:2] == ["git", "clone"]:
                    checkout = Path(command[-1])
                    (checkout / ".git").mkdir(parents=True)
                    (checkout / "install.sh").write_text("exit 0")

            with patch.object(core, "run_plan", side_effect=fake_run):
                core.run_install(entry, steps, lambda _: None, root)
            self.assertEqual([command[0] for command in commands], ["git", "bash"])

    def test_missing_git_installer_fails_after_clone(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            steps = core.install_steps(core.DEFAULTS[0], root)
            with patch.object(core, "run_plan") as runner:
                with self.assertRaises(ValueError):
                    core.run_install(core.DEFAULTS[0], steps, lambda _: None, root)
                self.assertEqual(runner.call_count, 1)

    def test_queue_continues_and_reports_actual_results(self):
        seen = []
        entries = core.DEFAULTS[:3]

        def runner(entry, steps, output):
            seen.append(entry.name)
            if entry == entries[1]:
                raise RuntimeError("installer failed")

        results = core.run_queue([(entry, []) for entry in entries], lambda _: None, lambda *_: None, runner)
        self.assertEqual(seen, [entry.name for entry in entries])
        self.assertEqual([error for _, error in results], [None, "installer failed", None])

    def test_python_install_uses_isolated_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            steps = core.install_steps(core.Entry("Unsloth", "python", "unsloth"), Path(folder))
            self.assertEqual(steps[0].command[1:3], ["-m", "venv"])
            self.assertTrue(steps[1].command[0].startswith(folder))
            self.assertEqual(steps[1].command[-2:], ["--", "unsloth"])

    def test_npm_installs_without_root(self):
        steps = core.install_steps(core.Entry("Codex", "npm", "@openai/codex"))
        self.assertEqual(steps[0].command[0], "npm")
        self.assertIn("--prefix", steps[0].command)
        self.assertNotIn("pkexec", steps[0].command)

    def test_flatpak_sets_up_user_flathub(self):
        steps = core.install_steps(core.Entry("Steam", "flatpak", "com.valvesoftware.Steam"))
        self.assertEqual(steps[0].command[:2], ["flatpak", "remote-add"])
        self.assertIn("--if-not-exists", steps[0].command)
        self.assertIn("--user", steps[1].command)

    def test_v3_catalogue_adds_only_belt_apps_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 3, "entries": []}))
            entries = core.load_catalogue(root)
            self.assertEqual(entries, core.BELT_APPS + core.ADMIN_APPS + core.DEV_APPS + core.EDITOR_APPS + core.CREATIVE_APPS + core.EXTRA_APPS)
            core.save_catalogue(entries[:-1], root)
            self.assertEqual(core.load_catalogue(root), entries[:-1])

    def test_v4_catalogue_adds_putty_once_and_preserves_removal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 4, "entries": []}))
            entries = core.load_catalogue(root)
            self.assertEqual([e.name for e in entries], ["PuTTY", "Graft", "Zed", "Obsidian", "Affinity · Wine installer", "ArtCraft · Linux setup", *[e.name for e in core.EXTRA_APPS]])
            self.assertEqual(entries[0].category, "MSP/Admin")
            core.save_catalogue(entries, root)
            self.assertEqual(core.load_catalogue(root), entries)
            core.save_catalogue([], root)
            self.assertEqual(core.load_catalogue(root), [])

    def test_v5_catalogue_adds_graft_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 5, "entries": []}))
            entries = core.load_catalogue(root)
            self.assertEqual(entries, core.DEV_APPS + core.EDITOR_APPS + core.CREATIVE_APPS + core.EXTRA_APPS)
            self.assertEqual(entries[0].category, "Dev/AI")
            self.assertEqual(core.install_steps(entries[0])[0].command[-1], "@nanonets/graft")
            core.save_catalogue(entries, root)
            self.assertEqual(core.load_catalogue(root), entries)
            core.save_catalogue([], root)
            self.assertEqual(core.load_catalogue(root), [])

    def test_v6_catalogue_adds_editors_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 6, "entries": []}))
            entries = core.load_catalogue(root)
            self.assertEqual(entries, core.EDITOR_APPS + core.CREATIVE_APPS + core.EXTRA_APPS)
            self.assertEqual([e.category for e in entries[:2]], ["Dev/AI", "Utilities"])
            core.save_catalogue(entries, root)
            self.assertEqual(core.load_catalogue(root), entries)
            core.save_catalogue([], root)
            self.assertEqual(core.load_catalogue(root), [])

    def test_creativity_guides_migrate_without_install_plans(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 7, "entries": []}))
            entries = core.load_catalogue(root)
            self.assertEqual(entries, core.CREATIVE_APPS + core.EXTRA_APPS)
            for entry in core.CREATIVE_APPS[1:]:
                entry.validate()
                with self.assertRaisesRegex(ValueError, "guided setup"):
                    core.install_steps(entry)
            core.save_catalogue(entries, root)
            self.assertEqual(core.load_catalogue(root), entries)
            core.save_catalogue([], root)
            self.assertEqual(core.load_catalogue(root), [])

    def test_frozen_helpers_and_host_environment(self):
        import os
        from tuxtools.runtime import host_environment
        with patch.object(core.sys, "frozen", True, create=True):
            self.assertEqual(core.helper_command("appimage"), [core.sys.executable, "--helper", "appimage"])
            with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/bundle", "LD_LIBRARY_PATH_ORIG": "/host"}):
                self.assertEqual(host_environment()["LD_LIBRARY_PATH"], "/host")

    def test_v8_catalogue_adds_extra_apps_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 8, "entries": []}))
            entries = core.load_catalogue(root)
            self.assertEqual(entries, core.EXTRA_APPS)
            core.save_catalogue(entries, root)
            self.assertEqual(core.load_catalogue(root), entries)
            core.save_catalogue([], root)
            self.assertEqual(core.load_catalogue(root), [])

    def test_affinity_guide_upgrades_preserving_favourite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 9, "entries": [{"name": "Affinity", "kind": "guide", "source": "https://github.com/seapear/AffinityOnLinux", "favourite": True, "category": "Creativity"}]}))
            entries = core.load_catalogue(root)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].kind, "git")
            self.assertTrue(entries[0].terminal)
            self.assertTrue(entries[0].favourite)
            with patch.object(core, "terminal_command", return_value=["konsole"]):
                steps = core.install_steps(entries[0], root)
            self.assertEqual(steps[-1].command[-1], str(core.checkout(entries[0], root) / entries[0].installer))
            core.save_catalogue([], root)
            self.assertEqual(core.load_catalogue(root), [])

    def test_legacy_affinity_upgrade_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            root.joinpath("catalogue.json").write_text(json.dumps({"version": 7, "entries": [{"name": "Affinity", "kind": "guide", "source": "https://github.com/seapear/AffinityOnLinux", "favourite": True}]}))
            entries = core.load_catalogue(root)
            affinity = [e for e in entries if "AffinityOnLinux" in e.source]
            self.assertEqual(len(affinity), 1)
            self.assertEqual(affinity[0].kind, "git")
            self.assertTrue(affinity[0].favourite)

    def test_azure_is_optional_and_wireshark_maps_to_arch_package(self):
        pwsh = next(e for e in core.BELT_APPS if e.name == "PowerShell")
        self.assertNotIn("--azure", core.install_steps(pwsh)[0].command)
        self.assertIn("--azure", core.install_steps(pwsh, azure=True)[0].command)
        wireshark = next(e for e in core.BELT_APPS if e.name == "Wireshark")
        self.assertEqual(core.package_name(wireshark, "pacman"), "wireshark-qt")
        self.assertEqual(core.package_name(wireshark, "apt-get"), "wireshark")


if __name__ == "__main__":
    unittest.main()
