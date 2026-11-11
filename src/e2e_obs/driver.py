"""Session lifecycle and OBS-driving commands for the harness.

Stack (no X server involved anywhere):

- sway (wlroots) running headless: ``WLR_BACKENDS=headless``
- screenshots via grim (wlr-screencopy protocol)
- window discovery/readiness via sway IPC (``swaymsg -t get_tree``)
- interaction and assertions via AT-SPI accessibility (semantic tree:
  press buttons, open menus, read widget text — no screen coordinates)

Why no raw keyboard/mouse injection: a pure headless wlroots seat reports
capabilities=0 (no libinput devices exist), so uinput-based tools (ydotool)
and one-shot virtual-pointer clients (wlrctl) cannot deliver events to
clients. AT-SPI actions are the supported interaction path; on sessions with
real input devices (e.g. a desktop VM) raw input would work.
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import time
import typing as t
from pathlib import Path

from atspi import commands as atspi_commands
from sway_windows import (
    find_window,
    get_tree,
    list_windows,
    named_windows,
)

from e2e_obs.session import (
    OBS_UNIT,
    SWAY_UNIT,
    apply_session_env,
    die,
    error,
    logs_dir,
    require_session,
    runtime_dir,
    session_env,
    shots_dir,
    state_dir,
    sway_sock,
)

DEFAULT_TITLE_RE = "OBS"
DEFAULT_ATSPI_APP = "obs"
START_TIMEOUT = 90.0
START_DRAW_SETTLE = 3.0
COMPOSITOR_START_TIMEOUT = 10.0


def title_re() -> str:
    """Regex matching the main OBS window title (``$OBS_TITLE_RE``)."""
    return os.environ.get("OBS_TITLE_RE") or DEFAULT_TITLE_RE


def atspi_app() -> str:
    """Application name on the accessibility bus (``$ATSPI_APP``)."""
    return os.environ.get("ATSPI_APP") or DEFAULT_ATSPI_APP


A11Y_WARMUP_TIMEOUT = 10.0
A11Y_WARMUP_RETRY = 0.5


def warmup_accessibility() -> None:
    """Make the AT-SPI registry available before OBS starts.

    Qt 6.4's accessibility bridge only activates when the registry is already
    running at application startup (QT_LINUX_ACCESSIBILITY_ALWAYS_ON does not
    change that), so OBS must never be the first accessibility client on the
    bus: the very first query activates the a11y bus and its registry, and
    this best-effort wait makes sure that happens before the OBS unit.
    """
    from atspi import bridge  # noqa: PLC0415
    from gi.repository import GLib  # noqa: PLC0415 # ty: ignore[import-not-found]  (dynamic introspection module)

    deadline = time.monotonic() + A11Y_WARMUP_TIMEOUT
    while True:
        try:
            bridge.list_app_names()
        except GLib.Error:
            if time.monotonic() >= deadline:
                error("accessibility registry did not come up; continuing")
                return
            time.sleep(A11Y_WARMUP_RETRY)
            continue
        print("accessibility registry: ready")
        return


def compositor_alive() -> bool:
    """Return True if the harness compositor answers on its IPC socket."""
    return (
        subprocess.run(
            ["swaymsg", "-s", str(sway_sock()), "-t", "get_version"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def start_compositor() -> None:
    """Start sway headless as a systemd user unit, or reuse a live one."""
    if compositor_alive():
        return
    xdg = runtime_dir()
    bus = Path(xdg) / "bus"
    if not bus.exists():
        # AT-SPI and OBS both need a session bus. Use the default user bus
        # when present; otherwise bootstrap a private one at the same path.
        subprocess.run(
            [
                "dbus-daemon",
                "--session",
                "--fork",
                "--print-address=0",
                "--address",
                f"unix:path={bus}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    cfg = state_dir() / "sway-config"
    cfg.write_text("output HEADLESS-1 resolution 1920x1080\nseat * hide_cursor 2000\n")
    subprocess.run(
        ["systemctl", "--user", "stop", SWAY_UNIT],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Both long-lived processes run as user-manager units: survives the
    # calling shell, and gives snap run a proper cgroup (systemd-run is the
    # portable path; launching from transient shell scopes is rejected by
    # snapd).
    with (logs_dir() / "sway.log").open("wb") as fh:
        subprocess.Popen(
            [
                "systemd-run",
                "--user",
                "--collect",
                "--pipe",
                f"--unit={SWAY_UNIT}",
                f"--setenv=SWAYSOCK={sway_sock()}",
                "--setenv=WLR_BACKENDS=headless",
                "--setenv=WLR_RENDERER=pixman",
                "--setenv=WLR_LIBINPUT_NO_DEVICES=1",
                "--",
                "env",
                "-u",
                "WAYLAND_DISPLAY",
                "-u",
                "QT_QPA_PLATFORM",
                "sway",
                "-c",
                str(cfg),
            ],
            stdout=fh,
            stderr=fh,
        )
    # Discover the Wayland socket name (dynamic, usually wayland-N).
    deadline = time.monotonic() + COMPOSITOR_START_TIMEOUT
    while time.monotonic() < deadline:
        for path in Path(xdg).glob("wayland-*"):
            if re.fullmatch(r"wayland-[0-9]+", path.name):
                (state_dir() / "wayland-display").write_text(path.name)
                return
        time.sleep(0.5)
    die("sway produced no Wayland socket")


def find_window_rect(pattern: str) -> str | None:
    """Return "x y width height title" of the first window matching *pattern*.

    Titles are matched with ``re.search``; returns None when nothing matches.
    """
    try:
        windows = named_windows(get_tree())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    for w in windows:
        if re.search(pattern, str(w["name"])):
            r = w["rect"]
            return f"{r['x']} {r['y']} {r['width']} {r['height']} {w['name']}"
    return None


def start(app_args: list[str]) -> int:
    """Start a headless session, launch OBS and wait for its main window."""
    pid_file = state_dir() / "obs.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
        except ValueError:
            pid = None
        if pid is not None and _alive(pid):
            print(f"OBS already running (pid {pid})")
            return 0
    start_compositor()
    # Polling and follow-up helpers must talk to the same compositor and bus
    # the session was started with.
    apply_session_env()
    # Qt only wires OBS into the accessibility bus if the registry already
    # exists at OBS startup; activate it first (see warmup_accessibility).
    warmup_accessibility()
    env = session_env()
    subprocess.run(
        ["systemctl", "--user", "stop", OBS_UNIT],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    obs_log = logs_dir() / "obs-stdout.log"
    with obs_log.open("wb") as fh:
        proc = subprocess.Popen(
            [
                "systemd-run",
                "--user",
                "--collect",
                "--pipe",
                f"--unit={OBS_UNIT}",
                f"--setenv=WAYLAND_DISPLAY={env['WAYLAND_DISPLAY']}",
                "--setenv=QT_QPA_PLATFORM=wayland",
                "--setenv=QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1",
                "--",
                "snap",
                "run",
                "obs-studio",
                *app_args,
            ],
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    pid_file.write_text(f"{proc.pid}\n")
    (state_dir() / "obs-unit").write_text(f"{OBS_UNIT}\n")
    time.sleep(2)
    if "is not a snap cgroup" in obs_log.read_text(errors="replace"):
        # Fallback: launch from this shell directly (works when the caller's
        # cgroup is accepted by snapd; systemd-run is the portable path).
        proc = subprocess.Popen(
            ["snap", "run", "obs-studio", *app_args],
            env={
                **os.environ,
                "QT_QPA_PLATFORM": "wayland",
                "QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1",
                **env,
            },
            stdout=obs_log.open("wb"),
            stderr=subprocess.STDOUT,
        )
        pid_file.write_text(f"{proc.pid}\n")
        (state_dir() / "obs-unit").unlink(missing_ok=True)
    deadline = time.monotonic() + START_TIMEOUT
    while True:
        rect = find_window_rect(title_re())
        if rect is not None:
            break
        if time.monotonic() >= deadline:
            die(f"no OBS window after {START_TIMEOUT:g}s (see {obs_log})")
        if pid_file.exists() and not _alive(int(pid_file.read_text().strip())):
            die(f"OBS exited during startup (see {obs_log})")
        time.sleep(1.0)
    time.sleep(START_DRAW_SETTLE)  # let it finish drawing
    save("00-initial")
    print(f"OBS window: {rect}")
    return 0


def stop() -> int:
    """Stop OBS and the compositor, and clean up state."""
    unit_file = state_dir() / "obs-unit"
    if unit_file.exists():
        subprocess.run(
            ["systemctl", "--user", "stop", unit_file.read_text().strip()],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        unit_file.unlink(missing_ok=True)
    subprocess.run(
        ["systemctl", "--user", "stop", SWAY_UNIT],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid_file = state_dir() / "obs.pid"
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        # The snap wrapper (pid file) is not the app; signal the whole tree,
        # and signal the real 'obs' process by name as well.
        _terminate(pid)
        subprocess.run(
            ["pkill", "-x", "obs"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):
            if (
                subprocess.run(
                    ["pgrep", "-x", "obs"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ).returncode
                != 0
            ):
                break
            time.sleep(0.5)
        else:
            subprocess.run(
                ["pkill", "-9", "-x", "obs"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        pid_file.unlink(missing_ok=True)
    if compositor_alive() and (
        subprocess.run(
            ["swaymsg", "-s", str(sway_sock()), "exit"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        != 0
    ):
        subprocess.run(
            ["pkill", "-x", "sway"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    sway_sock().unlink(missing_ok=True)
    (state_dir() / "wayland-display").unlink(missing_ok=True)
    print("stopped")
    return 0


def save(name: str | None = None) -> int:
    """Screenshot the headless output to ``shots/NAME.png``."""
    require_session()
    apply_session_env()
    name = name or f"shot-{time.strftime('%H%M%S')}"
    target = shots_dir() / f"{name}.png"
    rc = subprocess.run(
        ["grim", "-o", "HEADLESS-1", str(target)], check=False
    ).returncode
    if rc != 0:
        return rc
    print(target)
    return 0


def windows(pattern: str | None = None, fmt: str = "text") -> int:
    """List windows, or print the first one whose title matches *pattern*."""
    require_session()
    apply_session_env()
    windows_ = named_windows(get_tree())
    if pattern is not None:
        return find_window(windows_, pattern, fmt)
    list_windows(windows_, fmt)
    return 0


def wait_cmd(pattern: str, timeout: float = 60.0) -> int:
    """Poll the compositor until a window title matches *pattern*."""
    require_session()
    apply_session_env()
    deadline = time.monotonic() + timeout
    while True:
        rect = find_window_rect(pattern)
        if rect is not None:
            print(rect)
            return 0
        if time.monotonic() >= deadline:
            die(f"no window matching '{pattern}' after {timeout:g}s")
        time.sleep(1.0)


def atspi(args: argparse.Namespace) -> int:
    """Drive the configured application over AT-SPI, in-process.

    The application name comes from ``$ATSPI_APP``; the subcommand and its
    arguments are already parsed by the CLI. Only the session environment
    is applied here — the atspi command layer does the rest.
    """
    apply_session_env()
    app = atspi_app()
    handlers: dict[str, t.Callable[[], int]] = {
        "apps": lambda: atspi_commands.apps(args.format),
        "tree": lambda: atspi_commands.tree(app, args.depth, args.format),
        "find": lambda: atspi_commands.find(
            app, args.role, args.pattern, args.wait, args.format
        ),
        "click": lambda: atspi_commands.click(
            app, args.role, args.pattern, args.wait, args.format
        ),
        "text": lambda: atspi_commands.text(
            app, args.role, args.pattern, args.wait, args.format
        ),
        "assert": lambda: atspi_commands.assert_cmd(
            app, args.pattern, args.wait, args.format
        ),
    }
    return handlers[args.atspi_command]()


def obslog() -> int:
    """Print the path of the newest OBS log file."""
    snap_base = Path.home() / "snap" / "obs-studio"
    bases = [
        snap_base / "common" / ".config" / "obs-studio" / "logs",
        snap_base / "current" / ".config" / "obs-studio" / "logs",
        *sorted(snap_base.glob("*/.config/obs-studio/logs")),
    ]
    for base in bases:
        files = sorted(
            base.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if files:
            print(files[0])
            return 0
    error("no OBS log file found")
    return 1
