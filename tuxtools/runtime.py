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


def tls_context():
    """Use the host trust store even when Python/OpenSSL were built elsewhere."""
    import ssl
    from pathlib import Path
    # Explicit administrator overrides retain their normal priority.
    if os.environ.get('SSL_CERT_FILE') or os.environ.get('SSL_CERT_DIR'):
        return ssl.create_default_context()
    for path in ('/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt',
                 '/etc/ssl/cert.pem', '/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem'):
        if Path(path).is_file():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()
