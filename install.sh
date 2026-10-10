#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 -c 'import sys; assert sys.version_info >= (3, 10); import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1"); from gi.repository import Adw; assert (Adw.MAJOR_VERSION, Adw.MINOR_VERSION) >= (1, 4)' || {
    echo 'Requires Python 3.10+, GTK4, libadwaita 1.4+ and PyGObject. See README.md.' >&2
    exit 1
}
APP_DIR="$HOME/.local/share/tridents-tux-tools-app"
mkdir -p "$APP_DIR" "$HOME/.local/bin" "$HOME/.local/share/applications"
cp -R "$SOURCE_DIR/tuxtools" "$APP_DIR/"
cp "$SOURCE_DIR/tuxtools_gui.py" "$APP_DIR/"
python3 - "$APP_DIR" "$SOURCE_DIR" <<'METADATA'
import json
import sys
from pathlib import Path
destination = Path(sys.argv[1]) / "install-source.json"
temporary = destination.with_suffix(".tmp")
temporary.write_text(json.dumps({"source": str(Path(sys.argv[2]).resolve())}, indent=2) + "\n")
temporary.replace(destination)
METADATA
cat > "$HOME/.local/bin/tridents-tux-tools" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 "$HOME/.local/share/tridents-tux-tools-app/tuxtools_gui.py" "$@"
LAUNCHER
chmod +x "$HOME/.local/bin/tridents-tux-tools"
cat > "$HOME/.local/share/applications/io.github.TridentSpoon.TuxTools.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Trident's Tux Tools
Comment=Install your Git projects and favourite Linux apps
Exec="$HOME/.local/bin/tridents-tux-tools"
Icon=$APP_DIR/tuxtools/assets/io.github.TridentSpoon.TuxTools.png
Terminal=false
Categories=System;Utility;
DESKTOP
echo "Installed. Open Trident's Tux Tools from your application menu."
