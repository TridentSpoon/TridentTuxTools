"""Per-user PowerShell deployment from checksum-verified Microsoft binaries."""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.github.com/repos/PowerShell/PowerShell/releases/latest"
AZ_COMMAND = "$ErrorActionPreference='Stop'; Install-Module -Name Az -Repository PSGallery -Scope CurrentUser -Force -AllowClobber"


def open_url(url):
    if not url.startswith("https://"):
        raise ValueError("Expected HTTPS download.")
    response = urlopen(Request(url, headers={"User-Agent": "TridentsTuxTools/0.6"}), timeout=60)
    if not response.url.startswith("https://"):
        response.close()
        raise ValueError("Insecure download redirect.")
    return response


def select_asset(release, machine):
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(machine.lower())
    if not arch:
        raise ValueError(f"Unsupported PowerShell architecture: {machine}")
    if release.get("prerelease") or release.get("draft"):
        raise ValueError("Expected a stable public release.")
    for asset in release["assets"]:
        if re.fullmatch(rf"powershell-\d+\.\d+\.\d+-linux-{arch}\.tar\.gz", asset["name"]):
            url = asset["browser_download_url"]
            digest = asset.get("digest", "") or ""
            if not url.startswith("https://github.com/PowerShell/PowerShell/releases/download/"):
                raise ValueError("Unexpected release download location.")
            if not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest):
                raise ValueError("GitHub provides no SHA-256 digest for this release. Installation stopped.")
            return asset, digest.split(":")[1].lower()
    raise ValueError("The release has no matching Linux archive.")


def extract(archive, target):
    with tarfile.open(archive, "r:gz") as bundle:
        for item in bundle.getmembers():
            path = target / item.name
            if Path(item.name).is_absolute() or not path.resolve().is_relative_to(target.resolve()):
                raise ValueError("Archive contains an unsafe path.")
            if not item.isfile() and not item.isdir():
                raise ValueError("Archive contains unsupported links or special files.")
        if hasattr(tarfile, "data_filter"):
            bundle.extractall(target, filter="data")
        else:
            bundle.extractall(target)


def install(root, azure=False):
    with open_url(API) as response:
        release = json.load(response)
    asset, expected = select_asset(release, platform.machine())
    directory = root / "powershell"
    directory.mkdir(parents=True, exist_ok=True)
    current = directory / "current"
    if current.exists() and not current.is_symlink():
        raise ValueError("Existing PowerShell directory is not managed by this installer.")
    link = Path.home() / ".local/bin/pwsh"
    if (link.exists() or link.is_symlink()) and (not link.is_symlink() or link.readlink() != current / "pwsh"):
        raise ValueError("~/.local/bin/pwsh already exists and is not managed by this tool. Open the existing PowerShell instead.")
    with tempfile.TemporaryDirectory(dir=directory, prefix="stage-") as folder:
        stage = Path(folder)
        archive = stage / "download.tar.gz"
        print(f"Downloading {asset['name']}", flush=True)
        hasher = hashlib.sha256()
        with open_url(asset["browser_download_url"]) as response, archive.open("wb") as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
                hasher.update(block)
        if hasher.hexdigest() != expected:
            raise ValueError("PowerShell archive checksum mismatch.")
        extracted = stage / "runtime"
        extracted.mkdir()
        extract(archive, extracted)
        executable = extracted / "pwsh"
        executable.chmod(executable.stat().st_mode | 0o111)
        subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.ToString()"], check=True)
        if azure:
            print("Installing optional Azure PowerShell modules for your user…", flush=True)
            subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-Command", AZ_COMMAND], check=True)
        version = release["tag_name"].removeprefix("v")
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError("Unexpected release version.")
        version_dir = Path(tempfile.mkdtemp(dir=directory, prefix=version + "-"))
        version_dir.rmdir()
        extracted.rename(version_dir)
        temporary = directory / "current.new"
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(version_dir, target_is_directory=True)
        temporary.replace(current)
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink():
            link.symlink_to(current / "pwsh")
    print("PowerShell installed. Run pwsh (ensure ~/.local/bin is on PATH).", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--azure", action="store_true")
    args = parser.parse_args()
    install(args.root, args.azure)
