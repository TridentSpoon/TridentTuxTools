"""Read-only installation discovery and integrity checks for catalogue entries."""
import configparser
import hashlib
import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import core

GIT_APPS = {
    "set-the-table": ("io.github.autofstab.SetTheTable.desktop", "set-the-table"),
    "nable-tuxcontrol": ("io.github.tridentspoon.TuxControl.desktop", "nable-tuxcontrol-app"),
    "tuxman": ("io.github.TridentSpoon.TuxMan.desktop", "tuxman"),
    "aether1": ("Aether1.desktop", None),
    "caramelpopkern": ("caramelpopkern.desktop", "caramelpopkern"),
    "kamakiristudio": ("kamakiri-studio.desktop", "kamakiri-studio"),
}


@dataclass
class Installation:
    found: bool = False
    detail: str = "Not detected"
    desktop: Path = None
    command: list = field(default_factory=list)
    files: list = field(default_factory=list)
    scope: str = ""


@dataclass
class Report:
    state: str
    text: str


from .runtime import host_environment

def query(command):
    return subprocess.run(command, env=host_environment(), capture_output=True, text=True, timeout=30, errors="replace")


def share_dir():
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")


def desktop_paths():
    directories = [share_dir() / "applications"]
    directories.extend(Path(path) / "applications" for path in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"))
    return directories


def desktop_installation(path):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read(path)
    row = config["Desktop Entry"]
    command = [word.replace("%%", "%") for word in shlex.split(row.get("Exec", "")) if word not in {"%f", "%F", "%u", "%U", "%i", "%c", "%k"}]
    if not command:
        return Installation(True, "Launcher has no executable", desktop=path, files=[path])
    executable = shutil.which(command[0])
    files = [path]
    if executable:
        files.append(Path(executable))
    # Include script/entrypoint arguments, without invoking them.
    files.extend(Path(word) for word in command[1:] if Path(word).is_absolute() and Path(word).is_file())
    return Installation(True, "Desktop launcher detected", path, command, files, "Launcher and entrypoint files")


def detect(entry, root=None):
    entry.validate()
    root = root or core.data_dir()
    if entry.kind == "git" and entry.source == "https://github.com/seapear/AffinityOnLinux.git":
        for directory in desktop_paths():
            desktop = directory / "Affinity.desktop"
            if desktop.is_file():
                info = desktop_installation(desktop)
                exe = next((p for p in info.files if p.name == "Affinity.exe"), None)
                if exe:
                    info.files.extend(p for p in exe.parent.rglob("*") if p.is_file() and p not in info.files)
                    info.scope = "Affinity application files and Wine launcher (not the full Wine prefix)"
                    return info
        for prefix in (Path.home() / ".AffinityOnLinux", Path.home() / ".affinity"):
            exe = prefix / "drive_c/Program Files/Affinity/Affinity/Affinity.exe"
            if exe.is_file():
                return Installation(True, "Affinity Wine installation detected", command=["env", f"WINEPREFIX={prefix}", "wine", str(exe)], files=[p for p in exe.parent.rglob("*") if p.is_file()], scope="Affinity application files (not the full Wine prefix)")
        return Installation(detail="Affinity.exe not detected; complete the Wine wizard")
    if entry.kind == "git" and entry.source == "https://github.com/brave/install.sh.git":
        for directory in desktop_paths():
            for name in ("brave-origin.desktop", "brave-origin-browser.desktop"):
                desktop = directory / name
                if desktop.is_file():
                    return desktop_installation(desktop)
        executable = shutil.which("brave-origin")
        if executable:
            return Installation(True, "Brave Origin installed", command=[executable], files=[Path(executable).resolve()], scope="Brave Origin entrypoint")
        return Installation(detail="Brave Origin not detected")
    if entry.kind == "guide":
        return Installation(detail="Guided setup; automatic detection unavailable")
    if entry.kind == "builtin":
        executable = root / "powershell/current/pwsh"
        managed = executable.is_file()
        if not managed:
            found = shutil.which("pwsh")
            if not found:
                return Installation()
            executable = Path(found)
        files = [p for p in executable.parent.rglob("*") if p.is_file()] if managed else [executable]
        return Installation(True, "PowerShell installed", command=[str(executable)], files=files, scope="PowerShell runtime files" if managed else "PowerShell executable")
    if entry.kind == "flatpak":
        if shutil.which("flatpak"):
            for flag in ("--user", "--system"):
                result = query(["flatpak", "info", flag, "--show-location", entry.source])
                if result.returncode == 0:
                    return Installation(True, f"Flatpak installed ({flag[2:]})", command=["flatpak", "run", flag, entry.source], scope="Flatpak deployment metadata")
        ids = {"com.anydesk.Anydesk": ["anydesk.desktop"],
               "com.rustdesk.RustDesk": ["rustdesk.desktop"],
               "com.discordapp.Discord": ["discord.desktop"],
               "io.github.shiftey.Desktop": ["github-desktop.desktop"],
               "com.usebottles.bottles": ["com.usebottles.bottles.desktop", "bottles.desktop"],
               "dev.zed.Zed": ["dev.zed.Zed.desktop", "zed.desktop"],
               "md.obsidian.Obsidian": ["md.obsidian.Obsidian.desktop", "obsidian.desktop"],
               "org.localsend.localsend_app": ["localsend.desktop", "org.localsend.localsend_app.desktop"],
               "net.davidotek.pupgui2": ["net.davidotek.pupgui2.desktop", "protonup-qt.desktop"],
               "com.valvesoftware.Steam": ["steam.desktop"], "net.lutris.Lutris": ["net.lutris.Lutris.desktop", "lutris.desktop"],
               "com.heroicgameslauncher.hgl": ["heroic.desktop", "com.heroicgameslauncher.hgl.desktop"]}.get(entry.source, [])
        for directory in desktop_paths():
            for name in ids:
                if (directory / name).is_file():
                    return desktop_installation(directory / name)
        return Installation()
    if entry.kind == "package":
        manager = core.package_manager()
        package = core.package_name(entry, manager)
        commands = {"apt-get": ["dpkg-query", "-W", "-f=${Status}", package],
                    "pacman": ["pacman", "-Q", package], "dnf": ["rpm", "-q", package], "zypper": ["rpm", "-q", package]}
        result = query(commands[manager])
        found = result.returncode == 0 and (manager != "apt-get" or "install ok installed" in result.stdout)
        executable = shutil.which(entry.source) if found else None
        return Installation(found, "System package installed" if found else "Not detected", command=[executable] if executable else [], scope="Package-manager file records")
    if entry.kind == "python":
        environment = root / "environments" / entry.source
        files = list(environment.glob(f"lib/python*/site-packages/{entry.source.replace('-', '_')}-*.dist-info/METADATA"))
        if files:
            return Installation(True, "Python library installed in an isolated environment", files=files, scope="Python distribution metadata")
        return Installation()
    if entry.kind == "npm":
        package = Path.home() / ".local/lib/node_modules" / entry.source
        executable_name = {"@nanonets/graft": "graft", "@openai/codex": "codex", "@anthropic-ai/claude-code": "claude"}.get(entry.source)
        executable = shutil.which(executable_name) if executable_name else None
        if executable_name and not executable:
            local = Path.home() / ".local/bin" / executable_name
            if local.is_file():
                executable = str(local)
        if (package / "package.json").is_file() or executable:
            files = [package / "package.json"] if (package / "package.json").is_file() else []
            if executable:
                files.append(Path(executable))
            return Installation(True, "Coding tool installed", command=[executable] if executable else [], files=files, scope="Package metadata and executable")
        return Installation()
    desktop_id = None
    app_folder = None
    if entry.kind == "git":
        slug = entry.source.rstrip("/").split("/")[-1].removesuffix(".git").lower()
        desktop_id, app_folder = GIT_APPS.get(slug, (None, None))
    elif entry.kind == "appimage":
        key = hashlib.sha256(entry.source.encode()).hexdigest()[:16]
        desktop_id = f"io.github.TridentSpoon.TuxTools.Portable{key}.desktop"
    if desktop_id:
        for directory in desktop_paths():
            path = directory / desktop_id
            if path.is_file():
                result = desktop_installation(path)
                if app_folder:
                    folder = share_dir() / app_folder
                    if folder.is_dir():
                        result.files.extend(p for p in folder.rglob("*") if p.is_file() and not any(part in {"__pycache__", ".git"} for part in p.relative_to(folder).parts))
                        result.scope = "Installed application files, launcher and entrypoint"
                return result
    # Match externally installed portable apps by desktop application name.
    if entry.kind == "appimage":
        aliases = {"Cursor": {"cursor"}, "TMOG": {"task manager tmog", "tmog", "task manager og"}}.get(entry.name, {entry.name.casefold()})
        for directory in desktop_paths():
            for path in sorted(directory.glob("*.desktop")):
                config = configparser.ConfigParser(interpolation=None, strict=False)
                try:
                    config.read(path)
                    if config.get("Desktop Entry", "Name", fallback="").casefold() in aliases:
                        return desktop_installation(path)
                except (configparser.Error, ValueError):
                    continue
    return Installation(detail="No installed launcher detected" if entry.kind == "git" else "Not detected")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else _hash_stream(stream)


def _hash_stream(stream):
    hasher = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        hasher.update(block)
    return hasher.hexdigest()


def record_path(entry, root=None):
    key = hashlib.sha256((entry.kind + "\n" + entry.source).encode()).hexdigest()[:24]
    return (root or core.data_dir()) / "integrity" / f"{key}.json"


def record_install(entry, root=None):
    installation = detect(entry, root)
    if not installation.found or not installation.files:
        return
    files = {str(path): {"sha256": digest(path), "executable": os.access(path, os.X_OK)} for path in set(installation.files)}
    path = record_path(entry, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"scope": installation.scope, "files": files}, indent=2))
    temporary.replace(path)


def check(entry, root=None, deep=False):
    installation = detect(entry, root)
    if not installation.found:
        return installation, Report("missing", installation.detail)
    if installation.desktop and not installation.command:
        return installation, Report("failed", "The installed launcher has no executable.")
    if installation.command and not shutil.which(installation.command[0]):
        return installation, Report("failed", "The launch executable is missing or is not executable.")
    if entry.kind == "package":
        manager = core.package_manager()
        package = core.package_name(entry, manager)
        command = ["dpkg", "--verify", package] if manager == "apt-get" else (["pacman", "-Qkk", package] if manager == "pacman" else ["rpm", "-V", package])
        result = query(command)
        if result.returncode or (manager != "pacman" and result.stdout.strip()):
            return installation, Report("failed", (result.stdout + result.stderr).strip() or "Package verification failed.")
        return installation, Report("verified", "Package-manager file verification passed. " + result.stdout.strip())
    if deep and installation.command[:2] == ["flatpak", "run"]:
        user = "--user" in installation.command
        repo = (share_dir() / "flatpak" if user else Path("/var/lib/flatpak")) / "repo"
        if shutil.which("ostree") and repo.is_dir():
            result = query(["ostree", f"--repo={repo}", "fsck", "--quiet"])
            if result.returncode:
                return installation, Report("failed", (result.stdout + result.stderr).strip() or "Flatpak repository consistency check failed.")
            return installation, Report("verified", "Read-only OSTree checksum consistency check passed for the Flatpak repository. This checks repository objects, not application settings or user data.")
    path = record_path(entry, root)
    if path.exists():
        record = json.loads(path.read_text())
        problems = []
        for filename, expected in record["files"].items():
            file = Path(filename)
            if not file.is_file():
                problems.append(f"Missing: {filename}")
            elif digest(file) != expected["sha256"] or os.access(file, os.X_OK) != expected["executable"]:
                problems.append(f"Changed: {filename}")
        added = set(str(p) for p in installation.files) - set(record["files"])
        problems.extend(f"New file: {name}" for name in sorted(added))
        if problems:
            return installation, Report("failed", "\n".join(problems))
        return installation, Report("verified", f"SHA-256 comparison passed for {len(record['files'])} recorded files. Scope: {record['scope']}. This checks changes since installation, not publisher authenticity.")
    return installation, Report("unverified", "Installation detected; launcher checks passed. No saved file checksum baseline is available. Full file integrity is unverified. A successful installation through this tool records checksums where supported.")
