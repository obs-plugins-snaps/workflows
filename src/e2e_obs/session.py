"""Session state handling for the harness.

Long-lived processes (sway, OBS) are started by one invocation and driven by
later ones, so small state files carry the session between commands:

- ``.state/wayland-display`` — name of the compositor's Wayland socket
- ``.state/obs.pid`` — pid of the launched OBS snap process
- ``.state/obs-unit`` — systemd user unit running OBS, if any
- ``.state/sway-config`` — sway configuration for the headless output

State, screenshots and logs live under ``$E2E_OBS_HOME`` (default: the
working directory), in ``.state/``, ``shots/`` and ``logs/`` respectively.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn

SWAY_UNIT = "obs-harness-sway"
OBS_UNIT = "obs-harness-obs"


def base_dir() -> Path:
    """Directory holding state, screenshots and logs."""
    return Path(os.environ.get("E2E_OBS_HOME") or os.getcwd()).resolve()


def state_dir() -> Path:
    """Directory for session state files (created on demand)."""
    d = base_dir() / ".state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def shots_dir() -> Path:
    """Directory for screenshots (created on demand)."""
    d = base_dir() / "shots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def logs_dir() -> Path:
    """Directory for harness process logs (created on demand)."""
    d = base_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sway_sock() -> Path:
    """Path of the harness compositor's IPC socket."""
    return state_dir() / "sway.sock"


def runtime_dir() -> str:
    """The XDG runtime directory (``$XDG_RUNTIME_DIR`` or the uid default)."""
    return os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"


def wayland_display() -> str | None:
    """Name of the session's Wayland socket, if a session was started."""
    f = state_dir() / "wayland-display"
    return f.read_text().strip() if f.exists() else None


def session_env() -> dict[str, str]:
    """Environment variables attaching helpers to the running session."""
    return {
        "SWAYSOCK": str(sway_sock()),
        "WAYLAND_DISPLAY": wayland_display() or "",
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime_dir()}/bus",
    }


def apply_session_env() -> None:
    """Export the session environment into this process.

    Helpers run in-process (grim, swaymsg, AT-SPI via GObject introspection)
    must attach to the same session the harness started.
    """
    os.environ.setdefault("XDG_RUNTIME_DIR", runtime_dir())
    os.environ.update(session_env())


def error(message: str) -> None:
    """Print a lowercase, succinct error message in snap style."""
    print(f"error: {message}", file=sys.stderr)


def die(message: str) -> NoReturn:
    """Print *message* and exit with status 1."""
    error(message)
    raise SystemExit(1)


def require_session() -> None:
    """Die unless a harness session was started."""
    if wayland_display() is None:
        die("no harness session (run 'start' first)")
