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
        for entry in window.entries:
            window.show_more(entry)
        window.closing = True
        GLib.source_remove(window.gaming_timer)
        window.destroy()
    print('Native window smoke test passed')
else:
    from tuxtools.gui import main
    raise SystemExit(main())
