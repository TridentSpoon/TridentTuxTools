import sys
from tuxtools import __version__
if sys.argv[1:2] == ['--version']:
    print(__version__)
elif sys.argv[1:2] == ['--helper']:
    name = sys.argv[2]
    sys.argv = [name, *sys.argv[3:]]
    if name == 'terminal':
        from tuxtools.terminal import main
    elif name == 'appimage':
        from tuxtools.appimage import main
    elif name == 'powershell':
        from tuxtools.powershell import main
    else:
        raise SystemExit('Unknown helper')
    raise SystemExit(main())
elif sys.argv[1:2] == ['--smoke-test']:
    from tuxtools.gui import Window, Adw, GLib
    from unittest.mock import patch
    app = Adw.Application(application_id='io.github.TridentSpoon.TuxTools.Test')
    app.register(None)
    with patch.object(Window, 'refresh_installed'), patch.object(Window, 'poll_gaming', return_value=True):
        window = Window(app)
        category = window.entries[0].category
        window.collapsed_categories.add(category)
        window.render()
        # Inspect actual native category rows and verify state survives rebuilding.
        def find_section(widget):
            if isinstance(widget, Adw.ExpanderRow) and widget.get_title() == category:
                return widget
            child = widget.get_first_child()
            while child:
                found = find_section(child)
                if found:
                    return found
                child = child.get_next_sibling()
        section = find_section(window.catalogue)
        assert section is not None and not section.get_expanded()
        section.set_expanded(True)
        assert category not in window.collapsed_categories
        for entry in window.entries:
            window.show_more(entry)
        window.closing = True
        GLib.source_remove(window.gaming_timer)
        window.destroy()
    print('Native window smoke test passed')
else:
    from tuxtools.gui import main
    raise SystemExit(main())
