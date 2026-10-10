"""Native GTK4/libadwaita installer frontend."""
import shlex
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from . import core, installed, updates, gaming, __version__

APP_ID = "io.github.TridentSpoon.TuxTools"
ASSETS = Path(__file__).with_name("assets")


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Trident's Tux Tools", default_width=800, default_height=820)
        Gtk.IconTheme.get_for_display(self.get_display()).add_search_path(str(ASSETS))
        self.set_icon_name(APP_ID)
        self.busy = False
        self.entries = []
        self.selected = set()
        self.results = {}
        self.installations = {}
        self.integrity = {}
        self.more_entry = None
        self.scanning = False
        self.include_azure = False
        self.gaming_active = False
        self.checking_gaming = False
        self.closing = False
        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        add = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add a repository or app")
        add.connect("clicked", lambda *_: self.edit())
        header.pack_start(add)
        self.spinner = Gtk.Spinner()
        header.pack_start(self.spinner)
        about = Gtk.Button(icon_name="help-about-symbolic", tooltip_text="About")
        about.connect("clicked", self.about)
        header.pack_end(about)
        self.update_button = Gtk.Button(label=f"v{__version__} · Updates", tooltip_text="Check application version and install updates")
        self.update_button.connect("clicked", self.check_updates)
        header.pack_end(self.update_button)
        more = Gtk.Button(label="More", tooltip_text="Show app details and integrity checks")
        more.connect("clicked", lambda *_: self.show_more(self.more_entry or (self.entries[0] if self.entries else None)))
        header.pack_end(more)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Check installed apps")
        refresh.connect("clicked", lambda *_: self.refresh_installed())
        header.pack_start(refresh)
        view.add_top_bar(header)
        self.set_content(view)
        scroll = Gtk.ScrolledWindow()
        self.split = Adw.OverlaySplitView(sidebar_position=Gtk.PackType.END,
                                         min_sidebar_width=320, max_sidebar_width=360,
                                         show_sidebar=False)
        self.split.set_content(scroll)
        self.more_view = self.build_more_panel()
        self.split.set_sidebar(self.more_view)
        view.set_content(self.split)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 900px"))
        breakpoint.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(breakpoint)
        clamp = Adw.Clamp(maximum_size=760)
        scroll.set_child(clamp)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24, margin_top=24,
                      margin_bottom=24, margin_start=24, margin_end=24)
        clamp.set_child(box)
        title = Gtk.Label(label="Your tools, in one place", xalign=0)
        title.add_css_class("title-1")
        brand = Gtk.Box(spacing=16)
        self.brand_icon = Gtk.Image.new_from_file(str(ASSETS / f"{APP_ID}.png"))
        self.brand_icon.set_pixel_size(64)
        brand.append(self.brand_icon)
        brand.append(title)
        box.append(brand)
        box.append(Gtk.Label(label="Install your projects and favourite Linux apps. Add sources to build your own collection.", xalign=0, wrap=True))
        self.search = Gtk.SearchEntry(placeholder_text="Search your collection")
        self.search.connect("search-changed", lambda *_: self.render())
        box.append(self.search)
        self.only_favourites = Gtk.CheckButton(label="Show favourites only")
        self.only_favourites.connect("toggled", lambda *_: self.render())
        box.append(self.only_favourites)
        filters = Adw.PreferencesGroup()
        self.category_filter = Adw.ComboRow(title="Category", model=Gtk.StringList.new(["All categories", *core.CATEGORIES]))
        self.category_filter.connect("notify::selected", lambda *_: self.render())
        filters.add(self.category_filter)
        box.append(filters)
        selection = Gtk.Box(spacing=12)
        self.select_all = Gtk.Button(label="Select shown")
        self.select_all.connect("clicked", lambda *_: self.select_visible())
        selection.append(self.select_all)
        self.clear_selection = Gtk.Button(label="Clear selection")
        self.clear_selection.connect("clicked", lambda *_: self.clear_selected())
        selection.append(self.clear_selection)
        self.bulk_install = Gtk.Button(label="Install selected (0)", sensitive=False)
        self.bulk_install.add_css_class("suggested-action")
        self.bulk_install.connect("clicked", lambda *_: self.install_entries([e for e in self.entries if core.entry_key(e) in self.selected]))
        selection.append(self.bulk_install)
        box.append(selection)
        self.review = Gtk.CheckButton(label="Review commands before installing")
        box.append(self.review)
        self.catalogue = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.append(self.catalogue)
        log_group = Adw.PreferencesGroup(title="Activity", description="Commands and installer output appear here.")
        box.append(log_group)
        self.status = Gtk.Label(label="Ready. Choose a tool or add an app.", xalign=0, wrap=True, selectable=True)
        log_group.add(self.status)
        self.log = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        log_scroll = Gtk.ScrolledWindow(min_content_height=150)
        log_scroll.set_child(self.log)
        log_group.add(log_scroll)
        clear = Gtk.Button(label="Clear log", halign=Gtk.Align.START)
        clear.connect("clicked", lambda *_: self.log.get_buffer().set_text(""))
        log_group.add(clear)
        try:
            self.entries = core.load_catalogue()
        except Exception as exc:
            self.status.set_text(f"Cannot load catalogue: {exc}")
            add.set_sensitive(False)
        self.refresh_categories()
        self.render()
        self.connect("close-request", self.close_requested)
        self.refresh_installed()
        self.gaming_timer = GLib.timeout_add_seconds(5, self.poll_gaming)
        self.poll_gaming()

    def close_requested(self, *_):
        if self.busy:
            self.status.set_text("An operation is running. Wait for it to finish before closing.")
        if not self.busy:
            self.closing = True
            GLib.source_remove(self.gaming_timer)
        return self.busy

    def poll_gaming(self):
        if self.closing:
            return False
        if not self.checking_gaming:
            self.checking_gaming = True
            def worker():
                GLib.idle_add(self.gaming_checked, gaming.active())
            threading.Thread(target=worker, daemon=True).start()
        return True

    def gaming_checked(self, active):
        self.checking_gaming = False
        if self.closing:
            return False
        self.gaming_active = active is True
        icon_id = APP_ID + (".Gaming" if self.gaming_active else "")
        self.brand_icon.set_from_file(str(ASSETS / f"{icon_id}.png"))
        self.brand_icon.set_tooltip_text("GameMode session active" if self.gaming_active else "Normal tool belt")
        self.set_icon_name(icon_id)
        return False

    def append_log(self, text):
        buffer = self.log.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        return False

    def persist(self):
        try:
            core.save_catalogue(self.entries)
            return True
        except Exception as exc:
            self.status.set_text(f"Could not save catalogue: {exc}")
            return False

    def render(self):
        child = self.catalogue.get_first_child()
        while child:
            following = child.get_next_sibling()
            self.catalogue.remove(child)
            child = following
        count = 0
        visible = self.visible_entries()
        categories = list(core.CATEGORIES) + sorted({entry.category for entry in self.entries} - set(core.CATEGORIES))
        for category in categories:
            group = Adw.PreferencesGroup(title=category)
            matching = [entry for entry in visible if entry.category == category]
            if not matching:
                continue
            select = Gtk.Button(label="Select category", valign=Gtk.Align.CENTER)
            select.connect("clicked", lambda _, c=category: self.select_visible(c))
            group.set_header_suffix(select)
            self.catalogue.append(group)
            for entry in matching:
                count += 1
                kind = entry.kind
                key = core.entry_key(entry)
                subtitle = f"{entry.description or entry.source} · {kind}"
                if key in self.results:
                    subtitle += " · " + self.results[key]
                if key in self.installations and self.installations[key].found:
                    subtitle += " · Installed"
                row = Adw.ActionRow(title=entry.name, subtitle=subtitle)
                row.set_use_markup(False)
                row.set_subtitle_lines(2)
                selected = Gtk.CheckButton(sensitive=entry.kind != "guide", active=key in self.selected, valign=Gtk.Align.CENTER, tooltip_text="Select for bulk installation")
                selected.connect("toggled", self.selection_changed, entry)
                row.add_prefix(selected)
                favourite = Gtk.ToggleButton(icon_name="starred-symbolic" if entry.favourite else "non-starred-symbolic",
                                             active=entry.favourite, valign=Gtk.Align.CENTER, tooltip_text="Favourite")
                favourite.connect("toggled", self.favourite, entry)
                row.add_prefix(favourite)
                detected = self.installations.get(key)
                if detected and detected.found and (detected.desktop or detected.command):
                    open_button = Gtk.Button(label="Open", valign=Gtk.Align.CENTER)
                    open_button.connect("clicked", lambda _, e=entry: self.open_app(e))
                    row.add_suffix(open_button)
                button = Gtk.Button(label="Setup guide" if entry.kind == "guide" else "Install", valign=Gtk.Align.CENTER)
                button.connect("clicked", lambda _, e=entry: Gio.AppInfo.launch_default_for_uri(e.source, None) if e.kind == "guide" else self.install_entries([e]))
                button.add_css_class("suggested-action")
                row.add_suffix(button)
                more = Gtk.Button(label="More", valign=Gtk.Align.CENTER)
                more.connect("clicked", lambda _, e=entry: self.show_more(e))
                row.add_suffix(more)
                group.add(row)
        if not count:
            self.catalogue.append(Gtk.Label(label="No matching tools. Use + to add a repository or app.", wrap=True))
        self.catalogue.set_sensitive(not self.busy)
        self.update_selection()
        self.update_more()

    def build_more_panel(self):
        panel = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False, show_end_title_buttons=False)
        header.set_title_widget(Gtk.Label(label="More"))
        close = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close More")
        close.connect("clicked", lambda *_: self.hide_more())
        header.pack_end(close)
        panel.add_top_bar(header)
        scroll = Gtk.ScrolledWindow()
        panel.set_content(scroll)
        self.more_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                               margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        scroll.set_child(self.more_box)
        panel.add_css_class("sidebar")
        return panel

    def show_more(self, entry):
        self.more_entry = entry
        if not self.split.get_show_sidebar() and not self.is_maximized():
            self.set_default_size(max(800, self.get_width()) + 360, max(820, self.get_height()))
        self.split.set_show_sidebar(True)
        self.update_more()

    def hide_more(self):
        self.split.set_show_sidebar(False)
        if not self.is_maximized():
            self.set_default_size(max(800, self.get_width() - 360), max(820, self.get_height()))

    def update_more(self):
        if not hasattr(self, "more_box"):
            return
        child = self.more_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.more_box.remove(child)
            child = next_child
        entry = self.more_entry
        if entry is None:
            self.more_box.append(Gtk.Label(label="Choose More beside an app for its details.", wrap=True))
            return
        category_artwork = {"Gaming": ("Gaming", "Tux knows how to game"),
                            "Dev/AI": ("DevAI", "Tux fixes bugs and builds tools")}
        if entry.category in category_artwork:
            variant, description = category_artwork[entry.category]
            artwork = Gtk.Image.new_from_file(str(ASSETS / f"{APP_ID}.{variant}.png"))
            artwork.set_pixel_size(220)
            artwork.set_tooltip_text(description)
            self.more_box.append(artwork)
        for text, css in ((entry.name, "title-2"), (entry.description, None),
                          (f"{entry.category} · {entry.kind}", "dim-label"), (entry.source, None)):
            label = Gtk.Label(label=text, xalign=0, wrap=True, selectable=True)
            if css:
                label.add_css_class(css)
            self.more_box.append(label)
        if entry.kind == "guide":
            button = Gtk.Button(label="Open setup guide")
            button.connect("clicked", lambda *_: Gio.AppInfo.launch_default_for_uri(entry.source, None))
            self.more_box.append(button)
            edit_button = Gtk.Button(label="Edit source")
            edit_button.connect("clicked", lambda *_: self.edit(entry))
            self.more_box.append(edit_button)
            return
        key = core.entry_key(entry)
        info = self.installations.get(key)
        report = self.integrity.get(key)
        group = Adw.PreferencesGroup(title="Installed app")
        self.more_box.append(group)
        status = Adw.ActionRow(title=info.detail if info else "Checking installation…",
                              subtitle=report.text if report else "Integrity check pending")
        status.set_use_markup(False)
        status.set_subtitle_lines(0)
        group.add(status)
        if info and info.scope:
            label = Gtk.Label(label=f"Check scope: {info.scope}", xalign=0, wrap=True)
            self.more_box.append(label)
        def action(label, callback, sensitive=True):
            button = Gtk.Button(label=label, sensitive=sensitive and not self.busy)
            button.connect("clicked", lambda *_: callback())
            self.more_box.append(button)
        if info and info.found and (info.desktop or info.command):
            action("Open app", lambda: self.open_app(entry))
        action("Check integrity", lambda: self.refresh_installed([entry]), not self.scanning)
        if entry.kind == "builtin" and entry.source == "powershell":
            azure = Gtk.CheckButton(label="Include Azure PowerShell modules (Az)", active=self.include_azure, sensitive=not self.busy)
            azure.connect("toggled", lambda button: setattr(self, "include_azure", button.get_active()))
            self.more_box.append(azure)
            self.more_box.append(Gtk.Label(label="Optional, installed for your user. Azure CLI is not required. Applies when you click Install, including bulk installs.", xalign=0, wrap=True))
        if entry.kind == "package" and entry.source == "gamemode":
            self.more_box.append(Gtk.Label(label="In Steam, set launch options to: gamemoderun %command%\nThe couch icon appears while a game is using GameMode. Installing it alone does not enable optimisations.", xalign=0, wrap=True, selectable=True))
        action("Install", lambda: self.install_entries([entry]))
        if entry.kind == "git":
            downloaded = (core.checkout(entry) / ".git").is_dir()
            if downloaded:
                action("Open repository folder", lambda: self.open_folder(entry))
                action("Update repository", lambda: self.confirm(entry, "update"))
            else:
                action("Download repository only", lambda: self.confirm(entry, "download"))
        action("Edit source", lambda: self.edit(entry))

    def refresh_installed(self, entries=None):
        if self.scanning or self.busy:
            return
        self.scanning = True
        targets = list(entries if entries is not None else self.entries)
        self.update_more()
        def worker():
            checks = {}
            for entry in targets:
                try:
                    checks[core.entry_key(entry)] = installed.check(entry, deep=entries is not None)
                except Exception as exc:
                    checks[core.entry_key(entry)] = (installed.Installation(detail="Check unavailable"), installed.Report("unknown", str(exc)))
            GLib.idle_add(self.installed_checked, checks)
        threading.Thread(target=worker, daemon=True).start()

    def installed_checked(self, checks):
        self.scanning = False
        for key, (info, report) in checks.items():
            self.installations[key] = info
            self.integrity[key] = report
            if report.state == "failed":
                self.append_log("Integrity check failed: " + key[1] + "\n" + report.text + "\n")
        self.render()
        return False

    def open_app(self, entry):
        if self.busy:
            return
        self.status.set_text(f"Checking {entry.name} before opening…")
        def worker():
            try:
                info, report = installed.check(entry)
                GLib.idle_add(self.launch_checked, entry, info, report)
            except Exception as exc:
                GLib.idle_add(self.status.set_text, f"Cannot open {entry.name}: {exc}")
        threading.Thread(target=worker, daemon=True).start()

    def launch_checked(self, entry, info, report):
        self.installations[core.entry_key(entry)] = info
        self.integrity[core.entry_key(entry)] = report
        self.update_more()
        if not info.found or report.state == "failed":
            self.status.set_text(f"Cannot open {entry.name}: {report.text}")
            return False
        try:
            if info.desktop:
                app = Gio.DesktopAppInfo.new_from_filename(str(info.desktop))
                if not app:
                    raise ValueError("Desktop launcher is invalid")
                app.launch([], self.get_display().get_app_launch_context())
            elif info.command:
                app = Gio.AppInfo.create_from_commandline(shlex.join(info.command), entry.name,
                          Gio.AppInfoCreateFlags.NEEDS_TERMINAL if entry.kind in {"npm", "builtin"} else Gio.AppInfoCreateFlags.NONE)
                app.launch([], self.get_display().get_app_launch_context())
            else:
                raise ValueError("No launch command is known for this package")
            self.status.set_text(f"Opened {entry.name}. {report.text}")
        except Exception as exc:
            self.status.set_text(f"Could not open {entry.name}: {exc}")
        return False

    def visible_entries(self):
        query = self.search.get_text().casefold()
        item = self.category_filter.get_selected_item()
        category = item.get_string() if item else "All categories"
        return [entry for entry in self.entries
                if (category == "All categories" or entry.category == category)
                and (not self.only_favourites.get_active() or entry.favourite)
                and query in f"{entry.name} {entry.description} {entry.source} {entry.category}".casefold()]

    def selection_changed(self, button, entry):
        key = core.entry_key(entry)
        if button.get_active():
            self.selected.add(key)
        else:
            self.selected.discard(key)
        self.update_selection()

    def update_selection(self):
        self.bulk_install.set_label(f"Install selected ({len(self.selected)})")
        self.bulk_install.set_sensitive(bool(self.selected) and not self.busy)
        self.select_all.set_sensitive(not self.busy)
        self.clear_selection.set_sensitive(bool(self.selected) and not self.busy)
        self.review.set_sensitive(not self.busy)

    def select_visible(self, category=None):
        self.selected.update(core.entry_key(entry) for entry in self.visible_entries() if entry.kind != "guide" and (category is None or entry.category == category))
        self.render()

    def clear_selected(self):
        self.selected.clear()
        self.render()

    def button(self, row, icon, tooltip, callback):
        button = Gtk.Button(icon_name=icon, tooltip_text=tooltip, valign=Gtk.Align.CENTER)
        button.connect("clicked", lambda *_: callback())
        row.add_suffix(button)

    def favourite(self, button, entry):
        entry.favourite = button.get_active()
        self.persist()
        self.render()

    def open_folder(self, entry):
        try:
            Gio.AppInfo.launch_default_for_uri(core.checkout(entry).as_uri(), None)
        except Exception as exc:
            self.status.set_text(str(exc))

    def edit(self, entry=None):
        if self.busy:
            return
        dialog = Adw.MessageDialog(transient_for=self, heading="Edit tool" if entry else "Add a tool", body="Choose a source and give it a name.")
        form = Adw.PreferencesGroup()
        name = Adw.EntryRow(title="Name", text=entry.name if entry else "")
        kind = Adw.ComboRow(title="Source type", model=Gtk.StringList.new(["Git repository", "Flatpak", "System package", "npm package", "Python library", "AppImage", "PowerShell recipe", "Setup guide"]))
        kinds = ["git", "flatpak", "package", "npm", "python", "appimage", "builtin", "guide"]
        kind.set_selected(kinds.index(entry.kind) if entry else 0)
        source = Adw.EntryRow(title="HTTPS URL / Flatpak ID / package", text=entry.source if entry else "")
        description = Adw.EntryRow(title="Description", text=entry.description if entry else "")
        installer = Adw.EntryRow(title="Installer path (Git only)", text=entry.installer if entry else "install.sh")
        category = Adw.EntryRow(title="Category (e.g. Dev/AI, Gaming, Utilities)", text=entry.category if entry else "Utilities")
        terminal = Adw.SwitchRow(title="Run Git installer in terminal", subtitle="For setup scripts with password or input prompts", active=entry.terminal if entry else False)
        for widget in (name, category, kind, source, description, installer, terminal):
            form.add(widget)
        dialog.set_extra_child(form)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        if entry:
            dialog.add_response("remove", "Remove from collection")
            dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def response(_, result):
            if result == "remove":
                self.selected.discard(core.entry_key(entry))
                self.entries.remove(entry)
            elif result == "save":
                replacement = core.Entry(name.get_text().strip(), kinds[kind.get_selected()], source.get_text().strip(),
                                         description.get_text().strip(), installer.get_text().strip(), entry.favourite if entry else False,
                                         category.get_text().strip(), terminal.get_active())
                try:
                    replacement.validate()
                    if any(other is not entry and core.entry_key(other) == core.entry_key(replacement) for other in self.entries):
                        raise ValueError("That source is already in your collection. Edit its existing entry instead.")
                except ValueError as exc:
                    self.status.set_text(str(exc))
                    return
                if entry:
                    was_selected = core.entry_key(entry) in self.selected
                    self.selected.discard(core.entry_key(entry))
                    if was_selected:
                        self.selected.add(core.entry_key(replacement))
                    self.entries[self.entries.index(entry)] = replacement
                else:
                    self.entries.append(replacement)
            else:
                return
            self.persist()
            self.refresh_categories()
            self.render()
        dialog.connect("response", response)
        dialog.present()

    def refresh_categories(self):
        current = self.category_filter.get_selected_item()
        current = current.get_string() if current else "All categories"
        names = ["All categories", *core.CATEGORIES, *sorted({e.category for e in self.entries} - set(core.CATEGORIES))]
        self.category_filter.set_model(Gtk.StringList.new(names))
        self.category_filter.set_selected(names.index(current) if current in names else 0)

    def install_entries(self, entries):
        if self.busy or not entries:
            return
        jobs, errors = [], []
        for entry in entries:
            try:
                jobs.append((entry, core.install_steps(entry, azure=self.include_azure)))
            except Exception as exc:
                errors.append(f"{entry.name}: {exc}")
        if errors:
            self.status.set_text("Cannot start installation. " + " · ".join(errors))
            return
        if not self.review.get_active():
            self.execute_queue(jobs)
            return
        text = "\n\n".join(entry.name + "\n" + "\n".join(shlex.join(step.command) for step in steps) for entry, steps in jobs)
        text += "\n\nGit installation downloads missing repositories and runs their configured installer. Terminal-enabled projects open a terminal for prompts."
        dialog = Adw.MessageDialog(transient_for=self, heading=f"Install {len(jobs)} tool(s)?", body="The full plan is shown below.")
        preview = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        preview.get_buffer().set_text(text)
        scroll = Gtk.ScrolledWindow(min_content_height=250, max_content_height=400)
        scroll.set_child(preview)
        dialog.set_extra_child(scroll)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _, response: self.execute_queue(jobs) if response == "install" else None)
        dialog.present()

    def execute_queue(self, jobs):
        if self.busy:
            return
        self.busy = True
        self.spinner.start()
        self.render()

        def progress(index, total, entry):
            GLib.idle_add(self.status.set_text, f"Installing {index}/{total}: {entry.name}…")

        def worker():
            results = core.run_queue(jobs, lambda line: GLib.idle_add(self.append_log, line), progress)
            GLib.idle_add(self.queue_finished, results)
        threading.Thread(target=worker, daemon=True).start()

    def queue_finished(self, results):
        failures = []
        for entry, error in results:
            key = core.entry_key(entry)
            self.results[key] = "Failed — see log" if error else "Installed this session"
            if error:
                failures.append(entry.name)
            else:
                self.selected.discard(key)
        message = f"Finished: {len(results) - len(failures)} installed, {len(failures)} failed."
        if failures:
            message += " Failed: " + ", ".join(failures)
        self.finished(message)
        return False

    def confirm(self, entry, action):
        if self.busy:
            return
        try:
            command, cwd = core.plan(entry, action)
        except Exception as exc:
            self.status.set_text(str(exc))
            return
        message = shlex.join(command)
        if cwd:
            message += f"\n\nWorking folder: {cwd}\n\nThis executes the project's installer. Inspect its README and script using the folder button first. Interactive terminal prompts are not supported."
        dialog = Adw.MessageDialog(transient_for=self, heading=f"{action.capitalize()} {entry.name}?", body=message)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("run", "Run installer" if action == "install" else action.capitalize())
        dialog.set_response_appearance("run", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_close_response("cancel")
        dialog.connect("response", lambda _, response: self.execute(entry, command, cwd) if response == "run" else None)
        dialog.present()

    def execute(self, entry, command, cwd):
        if self.busy:
            return
        self.busy = True
        self.spinner.start()
        self.render()
        self.status.set_text(f"Working on {entry.name}…")
        self.append_log("\n$ " + shlex.join(command) + "\n")

        def worker():
            try:
                core.run_plan(command, cwd, lambda line: GLib.idle_add(self.append_log, line))
                message = f"Finished: {entry.name}."
            except Exception as exc:
                message = f"Failed: {exc}"
            GLib.idle_add(self.finished, message)
        threading.Thread(target=worker, daemon=True).start()

    def finished(self, message):
        self.busy = False
        self.spinner.stop()
        self.status.set_text(message)
        self.append_log(message + "\n")
        self.render()
        self.refresh_installed()
        return False

    def check_updates(self, *_):
        if self.busy:
            return
        self.update_button.set_sensitive(False)
        self.status.set_text("Checking the installed version and local update source…")
        def worker():
            try:
                result, error = updates.check(), None
            except Exception as exc:
                result, error = None, str(exc)
            GLib.idle_add(self.updates_checked, result, error)
        threading.Thread(target=worker, daemon=True).start()

    def updates_checked(self, result, error):
        self.update_button.set_sensitive(True)
        if error:
            message = f"Running version: {__version__}\n\nCannot check for updates: {error}"
        else:
            state = "Update available" if result.newer else "Installed version is up to date with the local source"
            message = f"Running version: {__version__}\nInstalled version: {result.installed}\nAvailable version: {result.available}\n\n{state}.\n\nSource: {result.source}\nThis checks your local project folder. Online releases are not configured."
            if __version__ != result.installed:
                message += "\n\nReopen the app to use the installed version."
        self.status.set_text("Update check failed." if error else ("An application update is available." if result.newer else "Application version check complete."))
        dialog = Adw.MessageDialog(transient_for=self, heading="Application updates", body=message)
        dialog.add_response("close", "Close")
        dialog.set_close_response("close")
        if result and result.newer:
            dialog.add_response("update", "Install update")
            dialog.set_response_appearance("update", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", lambda _, response: self.apply_update(result) if response == "update" else None)
        dialog.present()
        return False

    def apply_update(self, result):
        if self.busy:
            return
        self.busy = True
        self.update_button.set_sensitive(False)
        self.spinner.start()
        self.render()
        self.status.set_text(f"Updating to {result.available}…")
        def worker():
            try:
                updates.apply(result, lambda line: GLib.idle_add(self.append_log, line))
                message = f"Updated to {result.available}. Close and reopen the app to use the new version."
            except Exception as exc:
                message = f"Update failed: {exc}"
            GLib.idle_add(self.update_finished, message)
        threading.Thread(target=worker, daemon=True).start()

    def update_finished(self, message):
        self.update_button.set_sensitive(True)
        self.finished(message)
        return False

    def about(self, *_):
        dialog = Adw.MessageDialog(transient_for=self, heading="Trident's Tux Tools", body=f"A personal installer collection.\nGTK4 / libadwaita · Version {__version__}\n\nCategories, single-app and bulk installs in one place.")
        icon = Gtk.Image.new_from_file(str(ASSETS / f"{APP_ID}.png"))
        icon.set_pixel_size(128)
        dialog.set_extra_child(icon)
        dialog.add_response("close", "Close")
        dialog.present()


def main():
    if not Gtk.init_check():
        print("Cannot open the desktop display. Launch Trident's Tux Tools from your graphical desktop.")
        return 1
    app = Adw.Application(application_id="io.github.TridentSpoon.TuxTools")
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
    app.connect("activate", lambda app: (app.get_active_window() or Window(app)).present())
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
