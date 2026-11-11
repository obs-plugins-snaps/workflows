"""Connection to the AT-SPI registry over the session bus.

This is the only module in the package that touches GObject introspection;
everything else works on plain objects, which keeps it testable without a
running session bus. The bus is taken from ``$DBUS_SESSION_BUS_ADDRESS`` (or
the default user bus).
"""

from __future__ import annotations

import contextlib
import time
import typing as t
import warnings

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi, GLib  # noqa: E402  (require_version must precede the import) # ty: ignore[import-not-found]

from atspi.tree import POLL_INTERVAL  # noqa: E402


@contextlib.contextmanager
def silence_deprecation(message: str) -> t.Generator[None]:
    """Surgically ignore a single deprecation message from the Atspi API.

    ``warnings.catch_warnings`` is process-global (not thread-safe), so keep
    the guarded region as small as possible and never widen *message*.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning, message=message)
        yield


def _resolve_app(name: str) -> Atspi.Accessible | None:
    """Single-shot lookup of *name* on the accessibility bus."""
    desktop = Atspi.get_desktop(0)
    apps: dict[str, Atspi.Accessible] = {}
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app:
            apps[app.get_name().lower()] = app
    return apps.get(name) or next((v for k, v in apps.items() if name in k), None)


def get_app(name: str, wait: float = 0.0) -> Atspi.Accessible | None:
    """Return the accessibility application called *name*, if present.

    With *wait* > 0, poll until the application registers or the deadline
    passes: freshly launched applications register on the accessibility bus
    asynchronously, so a single check races their startup (and bus activation
    itself may still be in flight, hence the tolerated GLib errors).
    """
    deadline = time.monotonic() + wait
    while True:
        try:
            app = _resolve_app(name)
        except GLib.Error:
            if time.monotonic() >= deadline:
                raise
            app = None
        if app is not None or time.monotonic() >= deadline:
            return app
        time.sleep(POLL_INTERVAL)


def list_app_names() -> list[str]:
    """Return the names of every application on the accessibility bus."""
    desktop = Atspi.get_desktop(0)
    names = []
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app:
            names.append(app.get_name())
    return names
