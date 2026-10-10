#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m PyInstaller --clean --noconfirm packaging/tuxtools.spec
mkdir -p build/TuxTools.AppDir/usr/bin
cp -a dist/tuxtools/. build/TuxTools.AppDir/usr/bin/
cp tuxtools/assets/io.github.TridentSpoon.TuxTools.png build/TuxTools.AppDir/
cat > build/TuxTools.AppDir/AppRun <<'RUN'
#!/bin/sh
APPDIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "$APPDIR/usr/bin/tuxtools" "$@"
RUN
chmod +x build/TuxTools.AppDir/AppRun
cat > build/TuxTools.AppDir/io.github.TridentSpoon.TuxTools.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Trident's Tux Tools
Exec=tuxtools
Icon=io.github.TridentSpoon.TuxTools
Categories=System;Utility;
Terminal=false
DESKTOP
version=$(python3 -c 'from tuxtools import __version__; print(__version__)')
mkdir -p tools
curl --fail --location --retry 3 https://github.com/AppImage/appimagetool/releases/download/1.9.0/appimagetool-x86_64.AppImage -o tools/appimagetool.AppImage
chmod +x tools/appimagetool.AppImage
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 tools/appimagetool.AppImage build/TuxTools.AppDir "dist/TridentTuxTools-${version}-x86_64.AppImage"
(cd dist && sha256sum *.AppImage > SHA256SUMS)
