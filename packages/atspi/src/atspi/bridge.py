"""Connection to the AT-SPI registry over the session bus.

This is the only module in the package that touches GObject introspection;
everything else works on plain objects, which keeps it testable without a
running session bus. The bus is taken from ``$DBUS_SESSION_BUS_ADDRESS`` (or
the default user bus).
"""

from __future__ import annotations

import contextlib
import typing as t
import warnings

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # ty: ignore[import-not-found]  (dynamic introspection module)


@contextlib.contextmanager
def silence_deprecation(message: str) -> t.Generator[None]:
    """Surgically ignore a single deprecation message from the Atspi API.

    ``warnings.catch_warnings`` is process-global (not thread-safe), so keep
    the guarded region as small as possible and never widen *message*.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning, message=message)
        yield


def get_app(name: str) -> Atspi.Accessible | None:
    """Return the accessibility application called *name*, if present."""
    desktop = Atspi.get_desktop(0)
    apps: dict[str, Atspi.Accessible] = {}
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app:
            apps[app.get_name().lower()] = app
    return apps.get(name) or next((v for k, v in apps.items() if name in k), None)


def list_app_names() -> list[str]:
    """Return the names of every application on the accessibility bus."""
    desktop = Atspi.get_desktop(0)
    names = []
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app:
            names.append(app.get_name())
    return names
