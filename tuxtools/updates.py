"""Version checks and updates from the recorded local project source."""
import ast
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import __version__


def install_dir():
    return Path.home() / ".local/share/tridents-tux-tools-app"


def read_version(root):
    tree = ast.parse((root / "tuxtools/__init__.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            value = ast.literal_eval(node.value)
            version_tuple(value)
            return value
    raise ValueError("The source does not declare an application version.")


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise ValueError("Expected a version in major.minor.patch format.")
    return tuple(int(part) for part in value.split("."))


@dataclass
class Update:
    installed: str
    available: str
    source: Path
    newer: bool


def check(destination=None):
    destination = destination or install_dir()
    current = read_version(destination) if (destination / "tuxtools/__init__.py").is_file() else __version__
    metadata = destination / "install-source.json"
    if metadata.is_file():
        source = Path(json.loads(metadata.read_text())["source"])
    else:
        source = Path(__file__).resolve().parent.parent
    if not source.is_absolute() or source.resolve() == destination.resolve():
        raise ValueError("No original project source is configured. Run install.sh from your project folder once.")
    if not (source / "install.sh").is_file():
        raise ValueError(f"The update source is unavailable: {source}. Restore the project folder or reinstall from its new location.")
    available = read_version(source)
    return Update(current, available, source, version_tuple(available) > version_tuple(current))


def apply(update, output):
    # Recheck immediately before copying, to avoid installing an older source.
    current = check()
    if current.source.resolve() != update.source.resolve() or current.available != update.available:
        raise ValueError("The update source changed. Check for updates again.")
    if not current.newer:
        raise ValueError("The installed application is already up to date.")
    with subprocess.Popen(["bash", str(current.source / "install.sh")], cwd=current.source,
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, errors="replace") as process:
        for line in process.stdout:
            output(line)
        if process.wait():
            raise RuntimeError("Update failed. See the activity log.")
    if read_version(install_dir()) != current.available:
        raise RuntimeError("The installer finished but the expected version was not installed.")
