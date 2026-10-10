"""Catalogue persistence and explicit, shell-free installation plans."""
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit
from .runtime import host_environment


@dataclass
class Entry:
    name: str
    kind: str
    source: str
    description: str = ""
    installer: str = "install.sh"
    favourite: bool = False
    category: str = "Utilities"
    terminal: bool = False

    def validate(self):
        if not self.name.strip():
            raise ValueError("Enter an application name.")
        if not self.category.strip():
            raise ValueError("Enter a category.")
        if self.kind == "git":
            url = urlsplit(self.source)
            if url.scheme != "https" or not url.hostname or url.username or url.password or not url.path.strip("/"):
                raise ValueError("Use an HTTPS repository URL, without credentials.")
            path = Path(self.installer)
            if not self.installer or path.is_absolute() or ".." in path.parts:
                raise ValueError("Installer must be a relative path inside the repository.")
        elif self.kind in {"flatpak", "package", "python"}:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+:-]*", self.source):
                raise ValueError("Enter one package name or Flatpak ID, without options or spaces.")
        elif self.kind == "npm":
            if not re.fullmatch(r"(?:@[a-z0-9._-]+/)?[a-z0-9][a-z0-9._-]*", self.source):
                raise ValueError("Enter one npm package name.")
        elif self.kind in {"appimage", "guide"}:
            url = urlsplit(self.source)
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ValueError("Use an HTTPS AppImage URL or the official Cursor download page.")
        elif self.kind == "builtin":
            if self.source != "powershell":
                raise ValueError("Unknown built-in installer.")
        else:
            raise ValueError("Unknown source type.")


PUBLIC_APPS = [
    Entry("CaramelPopKern", "git", "https://github.com/TridentSpoon/CaramelPopKern.git",
          "Kernel and gaming manager · early build · graphical setup needs Zenity or KDialog",
          installer="install-gui.sh", category="Gaming"),
    Entry("KamaKiriStudio", "git", "https://github.com/TridentSpoon/KamaKiriStudio.git",
          "KDE desktop studio · requires Plasma 6 · experimental development build · guided terminal setup",
          category="Utilities", terminal=True),
]

BELT_APPS = [
    Entry("LocalSend", "flatpak", "org.localsend.localsend_app", "Send files to nearby family devices without cloud accounts", category="Utilities"),
    Entry("ProtonUp-Qt", "flatpak", "net.davidotek.pupgui2", "Manage Proton and Wine compatibility tools", category="Gaming"),
    Entry("GameMode", "package", "gamemode", "On-demand gaming optimisations · Steam launch option: gamemoderun %command%", category="Gaming"),
    Entry("PowerShell", "builtin", "powershell", "Microsoft scripting shell · optional Azure modules in More · per-user installation", category="MSP/Admin"),
    Entry("Wireshark", "package", "wireshark", "Network troubleshooting · capture permissions remain managed by your OS", category="MSP/Admin"),
]

ADMIN_APPS = [
    Entry("PuTTY", "package", "putty", "SSH and serial connection client for remote administration", category="MSP/Admin"),
]

DEV_APPS = [
    Entry("Graft", "npm", "@nanonets/graft", "Codebase context for coding agents · requires Node.js/npm · run graft init in your project after install", category="Dev/AI"),
]

EDITOR_APPS = [
    Entry("Zed", "flatpak", "dev.zed.Zed", "Fast code editor with AI tools · community-maintained Flatpak", category="Dev/AI"),
    Entry("Obsidian", "flatpak", "md.obsidian.Obsidian", "Local Markdown notes and linked knowledge vaults", category="Utilities"),
]

CREATIVE_APPS = [
    Entry("Affinity · Wine installer", "git", "https://github.com/seapear/AffinityOnLinux.git", "Experimental Wine wizard · select official Windows x64 installer · dependency/password prompts · Canva account required", installer="Guides/Wine/Script Installer/AoL_ScriptInstaller-GameDirection.sh", category="Creativity", terminal=True),
    Entry("ArtCraft · Linux setup", "guide", "https://github.com/storytold/artcraft/blob/main/_docs/dev_setup.md", "Free MIT/Apache-2.0 software · Linux source build · hosted AI generation may cost credits", category="Creativity"),
]

EXTRA_APPS = [
    Entry("AnyDesk", "flatpak", "com.anydesk.Anydesk", "Remote desktop · community Flatpak · native package recommended for unattended access", category="MSP/Admin"),
    Entry("RustDesk", "flatpak", "com.rustdesk.RustDesk", "Remote desktop with optional self-hosting", category="MSP/Admin"),
    Entry("Brave Origin", "git", "https://github.com/brave/install.sh.git", "Official Origin installer · terminal/password prompts · uses your system package manager", category="Utilities", terminal=True),
    Entry("Discord", "flatpak", "com.discordapp.Discord", "Voice, video and chat for gaming communities", category="Gaming"),
    Entry("GitHub Desktop", "flatpak", "io.github.shiftey.Desktop", "Visual Git client · community Linux port", category="Dev/AI"),
    Entry("Bottles", "flatpak", "com.usebottles.bottles", "Manage Windows apps and Wine environments", category="Utilities"),
    Entry("Microsoft 365 · Bottles setup", "guide", "https://github.com/bottlesdevs/programs/blob/main/Software/microsoft365business.yml", "Experimental Bottles Business/Enterprise recipes · Microsoft licence required · use supported Soda runner", category="Utilities"),
]

DEFAULTS = [
    Entry("Set the Table · AutoFSTAB", "git", "https://github.com/TridentSpoon/set-the-table.git", "An auto-mount FSTAB assistant", favourite=True),
    Entry("N-Able TuxControl", "git", "https://github.com/TridentSpoon/NAble-TuxControl.git", "N-able Take Control for Linux", favourite=True),
    Entry("TuxMan", "git", "https://github.com/TridentSpoon/TuxMan.git", "Make Linux applications portable", favourite=True),
    Entry("Unsloth (Core)", "python", "unsloth", "Fine-tuning Python library · isolated environment · compatible GPU required", category="Dev/AI"),
    Entry("Claude Code", "npm", "@anthropic-ai/claude-code", "Anthropic coding assistant · requires Node.js/npm · sign in after install", category="Dev/AI"),
    Entry("OpenAI Codex CLI", "npm", "@openai/codex", "OpenAI coding assistant · requires Node.js/npm · sign in after install", category="Dev/AI"),
    Entry("Cursor", "appimage", "https://cursor.com/download", "AI code editor · portable AppImage with application menu launcher", category="Dev/AI"),
    Entry("Aether1", "git", "https://github.com/TridentSpoon/Aether1.git", "Your AI companion · builds from source · setup opens a terminal", installer="setup.sh", category="Dev/AI", terminal=True),
    Entry("Heroic", "flatpak", "com.heroicgameslauncher.hgl", "Epic, GOG and Amazon games", category="Gaming"),
    Entry("Lutris", "flatpak", "net.lutris.Lutris", "Manage games and compatibility tools", category="Gaming"),
    Entry("Steam", "flatpak", "com.valvesoftware.Steam", "Steam games and Proton", category="Gaming"),
    Entry("TMOG", "appimage", "https://tmog.org/rtm/downloads/TaskManagerOG-1.0.0-x86_64.AppImage", "Task Manager OG · portable AppImage · glibc 2.35+", category="Utilities"),
] + PUBLIC_APPS + BELT_APPS + ADMIN_APPS + DEV_APPS + EDITOR_APPS + CREATIVE_APPS + EXTRA_APPS

CATEGORIES = ("Dev/AI", "Gaming", "Creativity", "Utilities", "MSP/Admin")


def entry_key(entry):
    return (entry.kind, entry.source)


def data_dir():
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "tridents-tux-tools"


def load_catalogue(root=None):
    path = (root or data_dir()) / "catalogue.json"
    if not path.exists():
        return [Entry(**asdict(entry)) for entry in DEFAULTS]
    saved = json.loads(path.read_text())
    entries = [Entry(**item) for item in (saved if isinstance(saved, list) else saved["entries"])]
    # Upgrade the original catalogue once; later removals stay removed.
    if isinstance(saved, list):
        existing = {entry_key(entry) for entry in entries}
        entries.extend(Entry(**asdict(entry)) for entry in DEFAULTS if entry_key(entry) not in existing)
    else:
        existing = {entry_key(entry) for entry in entries}
        additions = (PUBLIC_APPS if saved.get("version", 2) < 3 else []) + (BELT_APPS if saved.get("version", 2) < 4 else []) + (ADMIN_APPS if saved.get("version", 2) < 5 else []) + (DEV_APPS if saved.get("version", 2) < 6 else []) + (EDITOR_APPS if saved.get("version", 2) < 7 else []) + (CREATIVE_APPS if saved.get("version", 2) < 8 else []) + (EXTRA_APPS if saved.get("version", 2) < 9 else [])
        entries.extend(Entry(**asdict(entry)) for entry in additions if entry_key(entry) not in existing)
    # Upgrade the exact old Affinity guide while preserving user preferences.
    if isinstance(saved, list) or saved.get("version", 2) < 10:
        for entry in list(entries):
            if entry.kind == "guide" and entry.source == "https://github.com/seapear/AffinityOnLinux":
                replacement = Entry(**asdict(CREATIVE_APPS[0]))
                replacement.favourite = entry.favourite
                replacement.category = entry.category
                existing_affinity = next((e for e in entries if entry_key(e) == entry_key(replacement)), None)
                if existing_affinity:
                    existing_affinity.favourite = entry.favourite
                    existing_affinity.category = entry.category
                    entries.remove(entry)
                else:
                    entries[entries.index(entry)] = replacement
    if isinstance(saved, list) or saved.get("version", 2) < 11:
        for entry in list(entries):
            if entry.kind == "guide" and entry.source == "https://brave.com/origin/linux/":
                replacement = Entry(**asdict(next(e for e in EXTRA_APPS if e.name == "Brave Origin")))
                replacement.favourite = entry.favourite
                replacement.category = entry.category
                existing_brave = next((e for e in entries if entry_key(e) == entry_key(replacement)), None)
                if existing_brave:
                    existing_brave.favourite = entry.favourite
                    existing_brave.category = entry.category
                    entries.remove(entry)
                else:
                    entries[entries.index(entry)] = replacement
    for entry in entries:
        entry.validate()
    return entries


def save_catalogue(entries, root=None):
    for entry in entries:
        entry.validate()
    root = root or data_dir()
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / "catalogue.json.tmp"
    temporary.write_text(json.dumps({"version": 11, "entries": [asdict(entry) for entry in entries]}, indent=2) + "\n")
    temporary.replace(root / "catalogue.json")


def checkout(entry, root=None):
    import hashlib
    key = hashlib.sha256(entry.source.encode()).hexdigest()[:16]
    return (root or data_dir()) / "repositories" / key


def package_manager():
    for manager in ("apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(manager):
            return manager
    raise ValueError("No supported package manager found (apt, dnf, pacman, zypper).")


def package_name(entry, manager):
    return "wireshark-qt" if entry.source == "wireshark" and manager == "pacman" else entry.source


def plan(entry, action, root=None):
    entry.validate()
    if entry.kind == "git":
        path = checkout(entry, root)
        if action == "download":
            if path.exists():
                raise ValueError("Already downloaded. Open the repository to inspect it.")
            return ["git", "clone", "--", entry.source, str(path)], None
        if action == "update":
            if not (path / ".git").is_dir():
                raise ValueError("Download the repository first.")
            return ["git", "-C", str(path), "-c", "core.hooksPath=/dev/null", "pull", "--ff-only"], None
        if action == "install":
            script = (path / entry.installer).resolve()
            if not script.is_relative_to(path.resolve()) or not script.is_file():
                raise ValueError("Installer not found inside the downloaded repository. Check its README and edit the installer path.")
            if entry.source == "https://github.com/brave/install.sh.git":
                return ["env", "FLAVOR=origin", "sh", str(script)], path
            return ["bash", str(script)], path
    elif action == "install" and entry.kind == "flatpak":
        return ["flatpak", "install", "--user", "--noninteractive", "flathub", entry.source], None
    elif action == "install" and entry.kind == "package":
        manager = package_manager()
        arguments = {"apt-get": ["install", "-y"], "dnf": ["install", "-y"],
                     "pacman": ["-S", "--needed", "--noconfirm"], "zypper": ["--non-interactive", "install"]}[manager]
        executable = shutil.which(manager)
        return ["pkexec", executable, *arguments, "--", package_name(entry, manager)], None
    raise ValueError("Unsupported action.")


def helper_command(name):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--helper", name]
    return [sys.executable, str(Path(__file__).with_name(name + ".py"))]


def run_plan(command, cwd, output):
    if not shutil.which(command[0]):
        raise ValueError(f"Required command is missing: {command[0]}")
    if command[:2] == ["git", "clone"]:
        Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy() if command[0] == sys.executable and getattr(sys, "frozen", False) else host_environment()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    with subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                          errors="replace") as process:
        for line in process.stdout:
            output(line)
        code = process.wait()
    if code:
        raise RuntimeError(f"Command exited with status {code}. See the log for details.")


@dataclass
class Step:
    command: list
    cwd: Path = None
    git_installer: bool = False


def install_steps(entry, root=None, azure=False):
    """Build the complete single-click plan without downloading or executing it."""
    entry.validate()
    root = root or data_dir()
    if entry.kind == "guide":
        raise ValueError("This tool requires guided setup. Open its setup guide.")
    if entry.kind == "builtin":
        command = [*helper_command("powershell"), "--root", str(root)]
        if azure:
            command.append("--azure")
        return [Step(command)]
    if entry.kind == "git":
        path = checkout(entry, root)
        steps = []
        if not path.exists():
            command, cwd = plan(entry, "download", root)
            steps.append(Step(command, cwd))
        elif not (path / ".git").is_dir():
            raise ValueError("Checkout is incomplete. Inspect or remove its folder before retrying.")
        steps.append(Step(["bash", str(path / entry.installer)], path, True))
        if entry.terminal and not terminal_command():
            raise ValueError("Interactive setup needs Konsole, GNOME Terminal, or xterm.")
        return steps
    if entry.kind == "flatpak":
        return [Step(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", "https://flathub.org/repo/flathub.flatpakrepo"]),
                Step(plan(entry, "install", root)[0])]
    if entry.kind == "npm":
        return [Step(["npm", "install", "--global", "--prefix", str(Path.home() / ".local"), "--", entry.source])]
    if entry.kind == "python":
        environment = root / "environments" / entry.source
        return [Step([shutil.which("python3") or "python3", "-m", "venv", str(environment)]),
                Step([str(environment / "bin/python"), "-m", "pip", "install", "--upgrade", "--", entry.source])]
    if entry.kind == "appimage":
        return [Step([*helper_command("appimage"),
                      "--name", entry.name, "--url", entry.source, "--root", str(root)])]
    return [Step(plan(entry, "install", root)[0])]


def terminal_command():
    for tool, args in (("konsole", ["--nofork", "-e"]), ("gnome-terminal", ["--wait", "--"]), ("xterm", ["-e"])):
        if shutil.which(tool):
            return [tool, *args]
    return None


def run_install(entry, steps, output, root=None):
    for step in steps:
        command, cwd = step.command, step.cwd
        if step.git_installer:
            # Validate after cloning, before executing: reject missing scripts and escapes.
            command, cwd = plan(entry, "install", root)
            if entry.terminal:
                run_in_terminal(command, cwd, output)
                if entry.source == "https://github.com/seapear/AffinityOnLinux.git":
                    from .installed import detect
                    if not detect(entry, root).found:
                        raise RuntimeError("Affinity setup closed without a detected Affinity.exe. Complete the wizard, then retry or check its log.")
                continue
        import shlex
        output("$ " + shlex.join(command) + "\n")
        run_plan(command, cwd, output)


def run_in_terminal(command, cwd, output):
    import tempfile
    launcher = terminal_command()
    if not launcher:
        raise ValueError("No supported terminal installed.")
    with tempfile.TemporaryDirectory(prefix="tuxtools-install-") as folder:
        result = Path(folder) / "result"
        log = Path(folder) / "log"
        helper = Path(__file__).with_name("terminal.py")
        output("Interactive setup is running in your terminal. Complete its prompts there.\n")
        run_plan([*launcher, *helper_command("terminal"), str(result), str(log), *command], cwd, output)
        if log.exists():
            output(log.read_text(errors="replace"))
        if not result.exists() or result.read_text().strip() != "0":
            raise RuntimeError("Terminal installer failed or the terminal was closed before completion.")


def run_queue(jobs, output, progress, runner=None):
    """Sequential installs; failures do not prevent independent apps from running."""
    runner = runner or run_install
    results = []
    for index, (entry, steps) in enumerate(jobs, 1):
        progress(index, len(jobs), entry)
        output(f"\n[{index}/{len(jobs)}] {entry.name}\n")
        try:
            runner(entry, steps, output)
            if runner is run_install:
                from . import installed
                try:
                    installed.record_install(entry)
                except Exception as exc:
                    output(f"Could not record integrity checksums: {exc}\n")
            results.append((entry, None))
            output(f"Installed: {entry.name}\n")
        except Exception as exc:
            results.append((entry, str(exc)))
            output(f"Failed: {entry.name}: {exc}\n")
    return results
