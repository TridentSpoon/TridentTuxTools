# Trident's Tux Tools

## Easy download

Download the latest **AppImage** from [Releases](https://github.com/TridentSpoon/TridentTuxTools/releases/latest), make it executable in your file manager, and double-click it. No Python or GTK installation is needed for the frontend.

Initial compatibility target: x86_64 Linux, glibc 2.39+ (Ubuntu 24.04+, current Fedora/Arch/CachyOS), with an X11 or Wayland desktop. This is not a universal binary for every Linux system; ARM and musl/Alpine are not currently supported. If FUSE is unavailable, run `APPIMAGE_EXTRACT_AND_RUN=1 ./TridentTuxTools-*.AppImage`.

The AppImage Updates button opens the latest release download. Replace your old AppImage with the new one; your catalogue remains in your user data folder. System installation tools (Flatpak, Git, npm, system Python for Python libraries, package manager and authentication agent) are required only for the relevant catalogue apps.

Every main-branch push and pull request builds and smoke-tests an AppImage in GitHub Actions. Every `vX.Y.Z` tag publishes that build and SHA256SUMS to a GitHub Release. Bump `tuxtools/__init__.py`, push the change, then tag the same commit with the matching version. Development builds are available as workflow artifacts.


A native GTK4/libadwaita installer collection with the same desktop styling as
AutoFSTAB (Set the Table), N-Able TuxControl and TuxMan. Follows your system's
light/dark theme. Includes categories, single-click installs and a bulk installation queue.

## Launch

Requires Python 3.10+, GTK4, libadwaita 1.4+ and PyGObject.
On Arch/CachyOS these are `python-gobject gtk4 libadwaita`; on Debian/Ubuntu,
`python3-gi gir1.2-gtk-4.0 gir1.2-adw-1`; on Fedora,
`python3-gobject gtk4 libadwaita`. Install using your distro's package manager.

```sh
python3 tuxtools_gui.py
```

For an application menu launcher:

```sh
bash install.sh
```

## Your collection

### Application updates

Use the **version · Updates** button in the header to check the frontend's
running, installed and available versions. **Install update** appears when the
original local project folder contains a newer version. The installer records
that folder in `install-source.json`; keep it available or rerun `install.sh`
from its new location. Updates run in the background and retain your catalogue,
integrity records and approved icon. Close and reopen the app after updating.
Version checks read the source declaration without executing it, and updates
recheck before installation to prevent installing a changed or older source.
Online releases are not configured; this control checks the recorded local source.

The starter collection contains:

| Category | Apps |
| --- | --- |
| Dev/AI | Zed, Graft, Unsloth (Core), Claude Code, OpenAI Codex CLI, Cursor, Aether1 |
| Gaming | Heroic, Lutris, Steam, CaramelPopKern, ProtonUp-Qt, GameMode |
| Utilities | Obsidian, AutoFSTAB (Set the Table), N-Able TuxControl, TuxMan, TMOG, KamaKiriStudio, LocalSend |
| MSP/Admin | PowerShell, Wireshark, PuTTY |

LocalSend and ProtonUp-Qt use their official Flathub entries. GameMode uses
the distro package; in Steam use `gamemoderun %command%` as a game's launch
option. The app's header/window icon changes to the couch/controller variant
only while GameMode reports an active session, reverting afterward. Checking
status does not register Tux Tools as a game. The desktop launcher keeps the
approved normal icon. Some 32-bit games need the distro's 32-bit GameMode library.

PowerShell uses Microsoft's latest stable Linux binary archive for x64 or
ARM64, checks its published GitHub SHA-256 digest, and tests the runtime before
activating it. Files are per-user, with `pwsh` linked in `~/.local/bin`. OS runtime
dependencies must be installed separately if missing. CachyOS support is community
based. Previous runtime deployments are retained during updates.
Open PowerShell's More panel to enable **Include Azure PowerShell modules (Az)**
before installing individually or in bulk. This optional extra is off by default;
it installs the modules from PowerShell Gallery for your user. Azure CLI is not
included. Wireshark maps to `wireshark-qt` on Arch/CachyOS; packet-capture
permissions must be configured through your distro's supported mechanism.

Sources: [PowerShell binaries](https://learn.microsoft.com/en-us/powershell/scripting/install/alternate-install-methods),
[Azure modules](https://learn.microsoft.com/en-us/powershell/azure/install-azps-linux),
[LocalSend](https://flathub.org/en/apps/org.localsend.localsend_app),
[ProtonUp-Qt](https://flathub.org/en/apps/net.davidotek.pupgui2).

The catalogue includes all installable apps in TridentSpoon's public repositories
checked on 7 October 2026. The profile repository and empty `TridentTuxTools`
repository have no app to install. Existing N-Able TuxControl remains in the
catalogue even though it is not currently listed among the public repositories.
This is a bundled catalogue snapshot; newly published apps need a catalogue update.

[CaramelPopKern](https://github.com/TridentSpoon/CaramelPopKern) uses its
`install-gui.sh` graphical installer, requiring Zenity or KDialog. It is an early
kernel/gaming management build.
[KamaKiriStudio](https://github.com/TridentSpoon/KamaKiriStudio) runs `install.sh`
in a terminal and requires KDE Plasma 6. Its current development branch is
experimental; on Arch, its dependency setup can include a full system upgrade.

Click **Install** on any row, or check multiple rows and click **Install selected**.
**Select category** selects the visible entries in that category; **Select shown**
selects all current search/filter results. Selection survives filtering, and the
install count includes selected entries that are currently hidden. **Clear selection**
clears everything. Favourites and installation checkboxes are independent.

Installs run sequentially. A failed install is logged and the remaining apps
continue. Successful selections are cleared; failed selections stay checked for
retrying. The activity log shows commands, output, and per-app results. Enable
**Review commands before installing** for an optional preview before either
single or bulk installations. The default is single-click installation.

Use **+** to add Git, Flatpak, system package, npm, Python library or AppImage
sources. Enter any category name to create a custom category. Edit entries with
the pencil button. Removing an entry removes its listing only, leaving installed
apps and downloaded files alone.

### Installation methods

- **Git:** Install clones a missing repository and then runs its configured script
  (`install.sh` by default). The download-only button lets you inspect it first;
  the folder and update buttons appear after downloading. Updates use fast-forward
  pull without automatically running installers. Enable **Run Git installer in
  terminal** for interactive setup. Aether1 uses `setup.sh` and opens Konsole,
  GNOME Terminal or xterm for its dependency/password prompts. The queue waits for
  its actual script exit status. Git repositories need `git` and network access.
- **Gaming / Flatpak:** requires `flatpak`. Sets up the per-user Flathub remote if
  missing, then installs Heroic, Lutris and Steam from Flathub.
- **Claude Code / Codex CLI:** requires Node.js and npm. Installs npm packages to
  `~/.local` without root. Add `~/.local/bin` to your PATH to launch `claude` and
  `codex` in a terminal. Sign in through the respective app after installation.
  Claude's current npm installer recommends Node.js 22+.
- **Unsloth Core:** creates an isolated Python environment under
  `tridents-tux-tools/environments/unsloth` and installs the Python library there.
  This entry is the Core library, not Studio or the desktop app. Compatible GPU,
  driver and Python/PyTorch requirements still apply; installation does not
  configure hardware. Some distros require their `python3-venv` package.
- **Cursor / TMOG:** downloads a portable AppImage, checks its AppImage header,
  marks it executable, and adds a per-user application-menu launcher. Cursor's
  current Linux download is resolved from its official page; TMOG uses the supplied
  1.0.0 URL. Both support x64 and ARM64. AppImage runtime dependencies such as FUSE
  may be needed; TMOG requires glibc 2.35+. Downloads are staged and atomically
  replaced so a failed download preserves an existing installed AppImage.
- **System packages:** supports apt, dnf, pacman and zypper, authenticating through
  `pkexec`. Package names must match your distro's repositories.

### More, opening apps, and integrity

**More** opens a panel on the right with source details, installation status,
integrity results, and repository/edit actions. On narrow screens it overlays
the content instead of forcing the window offscreen. The UI uses native GTK4 /
libadwaita widgets, the OS appearance preference, and system fonts, without a
forced light/dark palette. The approved Tux/trident/wrench icon stays unchanged.

Installed applications show **Open** alongside **Install**. Detection includes
the built-in Git projects' desktop launchers, externally installed Cursor/TMOG,
user/system Flatpaks, supported native gaming launchers, system packages, coding
CLI tools, and the isolated Unsloth Core library. A downloaded Git checkout alone
is not treated as an installation. Libraries and packages without a known launch
command have installation details but no Open action.

Checks run in the background at startup and after installation. **Check integrity**
in More performs a fresh check; the header refresh checks all installations again.
Open checks again before launch and blocks on a detected failure.

- Successful installs through this tool record SHA-256 hashes and executable
  permissions for detected installed files. Later checks report missing, changed,
  or newly detected files. Copied Git apps cover their installed app directories;
  standalone launchers/CLI tools cover their recorded entrypoint and metadata.
  The displayed scope states what was checked. These are local comparisons,
  not publisher-signature or malware verification.
- Native system packages use `dpkg --verify`, `rpm -V`, or `pacman -Qkk`.
- A manual Flatpak check can run read-only `ostree fsck` when available. This
  checks the corresponding Flatpak repository, not application settings or user
  data; no repair/delete flags are used. Startup checks deployment presence only.
- Existing installations without a checksum record are labelled **unverified**,
  even if their launcher is present and executable. Merely scanning an installation
  never creates or silently replaces its baseline. External upgrades may change
  recorded files and will be reported for review.

Successful installs are determined by exit status. The app does not yet provide
uninstall actions or a complete installed-version inventory. Integrity records
are stored in `tridents-tux-tools/integrity` beside the catalogue.

Sources: [Unsloth](https://unsloth.ai/docs/get-started/install),
[Claude Code](https://code.claude.com/docs/en/setup),
[Codex CLI](https://github.com/openai/codex),
[Cursor](https://cursor.com/download), [TMOG](https://tmog.org/),
[Heroic](https://flathub.org/en/apps/com.heroicgameslauncher.hgl),
[Lutris](https://flathub.org/en/apps/net.lutris.Lutris),
[Steam](https://flathub.org/en/apps/com.valvesoftware.Steam).

The catalogue and Git checkouts are stored under
`$XDG_DATA_HOME/tridents-tux-tools` (default `~/.local/share/tridents-tux-tools`).
The application itself is installed separately, so reinstalling preserves your
collection. A malformed catalogue is reported instead of overwritten.
The original catalogue format is upgraded with the new starter entries. Your
custom entries and favourites are preserved, and later removals stay removed.
Version 0.3 also adds the two public apps to saved version-2 catalogues without
restoring previously removed apps. Once saved, removing either new entry is preserved.

## Checks

```sh
python3 -m unittest discover -s tests -v
```

Graft uses the upstream documented `@nanonets/graft` npm package. After installation,
run `graft init` inside the project you want to integrate (or `graft init --dry-run`
to preview changes). Installation does not configure agents or modify projects.
Source: [trailhq/Graft](https://github.com/trailhq/graft).

Zed (`dev.zed.Zed`, community-maintained) and Obsidian (`md.obsidian.Obsidian`)
install as per-user Flatpaks from Flathub. Existing native desktop launchers
are also detected for Open.

Creativity includes Affinity as an interactive Wine installer and ArtCraft as a
setup-guide entry excluded from bulk installation. Affinity has no official Linux build; the community
[AffinityOnLinux](https://github.com/seapear/AffinityOnLinux) guides describe Wine
setup and current compatibility issues. ArtCraft's current source is dual
MIT/Apache-2.0 licensed; [Linux setup](https://github.com/storytold/artcraft/blob/main/_docs/dev_setup.md)
requires a Rust/Tauri source build. The software is free, while hosted generation
can require paid credits or third-party services: [pricing](https://getartcraft.com/pricing).
Setup guides are references; Tux Tools does not report them as installed apps.

Additional entries: AnyDesk and RustDesk (MSP/Admin), Discord (Gaming),
GitHub Desktop community Linux port (Dev/AI), Bottles and Brave Origin (Utilities).
AnyDesk uses a community Flatpak; unattended access may need its native package.
Brave Origin runs the official installer in a terminal with FLAVOR=origin. Microsoft 365 is a guided, unstable
Bottles recipe with an experimental Soda runner and a valid Microsoft licence,
not an unattended bulk installation. Both Business and Enterprise recipe links
are in More.

Affinity now has an Install button that clones AffinityOnLinux and opens the
experimental script installer linked from its Wine guide, in a terminal.
Download the official Windows x64 MSIX or Enterprise x64 EXE and select it in
the wizard. Dependency installation may require your password and 10 GB free
space; .NET setup may take 10–20 minutes. Complete normal Affinity and Canva
activation prompts. The wizard controls Wine setup and optional community
fixes; read its choices and current compatibility notes. Closing the wizard
without a detected Affinity.exe is reported as incomplete. Open and integrity
checks cover the application files and launcher, not the entire Wine prefix.

Brave Origin clones the official `brave/install.sh` source repository and runs
`env FLAVOR=origin sh install.sh`, equivalent to the official download command.
It uses upstream package-manager setup and may request your password.

### Proton privacy tools

The **Privacy** category includes Mail + Calendar, VPN, Pass, Mail Bridge,
Authenticator, Meet, Drive CLI, Calendar, Drive, Docs, Sheets, Wallet, Lumo,
Standard Notes and SimpleLogin. Mail, VPN, Pass, Bridge and Standard Notes use
community-maintained Flathub packages for single or bulk installation. Their More
panels link to official Linux downloads/setup; Proton VPN's Flatpak has sandbox
limitations, so use Proton's native instructions when full functionality is needed.
Mail desktop requires an eligible paid plan after its trial; Bridge requires a paid
Mail plan. Accounts and subscription features remain managed by Proton.

Authenticator and Meet link to official DEB/RPM downloads. Drive CLI links to its
Linux setup instructions. Browser services have **Open website** buttons and are
excluded from bulk installs. Docs and Sheets share the Docs dashboard; create a
spreadsheet there for Sheets. No unsupported Linux desktop client is implied.
Sources: [Proton apps](https://protonapps.com/),
[Drive CLI](https://proton.me/support/drive-cli),
[Standard Notes](https://standardnotes.com/download).

All categories start collapsed when the app opens. Category headers expand and collapse. Their state is kept while you search,
select apps or refresh installed-app checks during the current session.

Expanding a category while More is open shows its Tux artwork there. Gaming,
Dev/AI and Privacy use their category images; other categories use the original Tux.
Click an app’s More button to switch back to that app’s details.
