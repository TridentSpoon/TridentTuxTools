"""Download portable AppImages and register a per-user desktop launcher."""
import argparse
import hashlib
import os
import platform
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


try:
    from .runtime import tls_context
except ImportError:
    from runtime import tls_context


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.label = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.label = ""

    def handle_data(self, data):
        if self.href is not None:
            self.label += data

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, self.label))
            self.href = None


def architecture():
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "x64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    raise ValueError(f"No AppImage recipe for architecture {machine}.")


def resolve_url(source, arch, fetch):
    if source in {"https://cursor.com/download", "https://cursor.com/downloads"}:
        parser = Links()
        parser.feed(fetch(source))
        for href, label in parser.links:
            label = label.lower()
            if "linux" in label and "appimage" in label and arch in label:
                url = urljoin(source, href)
                if urlsplit(url).scheme == "https":
                    return url
        raise ValueError("Cursor's download page has no matching Linux AppImage. Check the official download page.")
    if source.startswith("https://tmog.org/") and arch == "arm64":
        return source.replace("x86_64", "aarch64")
    return source


def open_url(url):
    response = urlopen(Request(url, headers={"User-Agent": "TridentsTuxTools/0.2"}), timeout=60, context=tls_context())
    if urlsplit(response.url).scheme != "https":
        response.close()
        raise ValueError("Download redirected to an insecure URL.")
    return response


def desktop_quote(path):
    text = str(path).replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        text = text.replace(character, "\\" + character)
    return '"' + text + '"'


def install(name, source, root):
    def fetch(url):
        with open_url(url) as response:
            return response.read(8 * 1024 * 1024).decode("utf-8")
    url = resolve_url(source, architecture(), fetch)
    key = hashlib.sha256(source.encode()).hexdigest()[:16]
    directory = root / "portable" / key
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "application.AppImage"
    print(f"Downloading {url}", flush=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as stream:
            temporary = Path(stream.name)
            with open_url(url) as response:
                size = 0
                while block := response.read(1024 * 1024):
                    stream.write(block)
                    size += len(block)
                expected = response.headers.get("Content-Length")
                if expected and size != int(expected):
                    raise ValueError("Download is incomplete.")
        with temporary.open("rb") as stream:
            header = stream.read(12)
        if header[:4] != b"\x7fELF" or header[8:11] not in {b"AI\x01", b"AI\x02"}:
            raise ValueError("The download is not an AppImage.")
        temporary.chmod(0o755)
        temporary.replace(target)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    applications = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("\n", " ").replace("\r", " ").replace("\\", "\\\\")
    desktop = applications / f"io.github.TridentSpoon.TuxTools.Portable{key}.desktop"
    desktop.write_text(f"[Desktop Entry]\nType=Application\nName={safe_name}\nExec={desktop_quote(target)}\n"
                       "Icon=application-x-executable\nTerminal=false\nCategories=Utility;\n")
    print(f"Installed {name}: {target}\nApplication menu launcher: {desktop}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--check-download", action="store_true", help="Check official URL and AppImage header without installing")
    args = parser.parse_args()
    if args.check_download:
        def fetch(url):
            with open_url(url) as response:
                return response.read(8 * 1024 * 1024).decode("utf-8")
        url = resolve_url(args.url, architecture(), fetch)
        with open_url(url) as response:
            header = response.read(12)
        if header[:4] != b"\x7fELF" or header[8:11] not in {b"AI\x01", b"AI\x02"}:
            raise ValueError("The download is not an AppImage.")
        print("HTTPS download and AppImage header verified")
    else:
        install(args.name, args.url, args.root)


if __name__ == "__main__":
    raise SystemExit(main())
