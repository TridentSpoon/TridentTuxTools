"""Read GameMode status without registering this application as a game."""
import ctypes


def active():
    try:
        library = ctypes.CDLL("libgamemode.so.0")
        query = library.real_gamemode_query_status
        query.argtypes = []
        query.restype = ctypes.c_int
        result = query()
        return result in (1, 2) if result >= 0 else None
    except (OSError, AttributeError):
        return None
