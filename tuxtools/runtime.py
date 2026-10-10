"""Keep bundled libraries out of host commands."""
import os
import sys


def host_environment():
    env = os.environ.copy()
    if getattr(sys, 'frozen', False):
        original = env.get('LD_LIBRARY_PATH_ORIG')
        if original is None:
            env.pop('LD_LIBRARY_PATH', None)
        else:
            env['LD_LIBRARY_PATH'] = original
        for key in ('GI_TYPELIB_PATH', 'GSETTINGS_SCHEMA_DIR', 'GDK_PIXBUF_MODULE_FILE'):
            env.pop(key, None)
    return env
