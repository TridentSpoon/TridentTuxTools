from pathlib import Path
root = Path(SPECPATH).parent
analysis = Analysis([str(root / 'packaging/entrypoint.py')], pathex=[str(root)],
    datas=[(str(root / 'tuxtools/assets'), 'tuxtools/assets')],
    hiddenimports=['tuxtools.appimage', 'tuxtools.powershell', 'tuxtools.terminal'],
    hooksconfig={'gi': {'module-versions': {'Gtk': '4.0', 'Adw': '1'}, 'icons': ['Adwaita'], 'themes': ['Adwaita']}},
    excludes=['tkinter'], noarchive=False)
pyz = PYZ(analysis.pure)
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='tuxtools', console=True)
coll = COLLECT(exe, analysis.binaries, analysis.datas, name='tuxtools')
