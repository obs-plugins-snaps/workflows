"""Command-line interface for the harness (``e2e-obs``)."""

from __future__ import annotations

import argparse
import sys

from e2e_obs import driver

# Pass-through commands whose trailing arguments are forwarded verbatim to
# the app or to a library CLI. Argparse's REMAINDER cannot capture leading
# option-like tokens (e.g. "e2e-obs windows --format json"); gh-61252
# (bpo-17050) is still open and this reproduces on 3.12, 3.13 and 3.14, so
# these are tokenized manually in main() before argparse sees them; they are
# declared in build_parser() for the help surface only.
PASSTHROUGH = ("start", "windows", "atspi")


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ``e2e-obs`` CLI."""
    parser = argparse.ArgumentParser(
        prog="e2e-obs",
        description="Wayland-native headless GUI harness for the obs-studio snap.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    p_start = sub.add_parser("start", help="start a headless session and launch OBS")
    p_start.add_argument(
        "app_args",
        nargs=argparse.REMAINDER,
        metavar="APPARGS",
        help="arguments passed to obs-studio",
    )
    sub.add_parser("stop", help="stop the session and clean up")
    p_save = sub.add_parser("save", help="screenshot the session")
    p_save.add_argument(
        "name", nargs="?", help="screenshot name (default: shot-HHMMSS)"
    )
    p_windows = sub.add_parser("windows", help="list windows (title, geometry)")
    p_windows.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        metavar="ARGS",
        help="arguments forwarded to sway-windows",
    )
    p_wait = sub.add_parser("wait", help="poll the compositor for a window title")
    p_wait.add_argument("pattern", metavar="REGEX")
    p_wait.add_argument(
        "timeout", nargs="?", type=float, default=60.0, metavar="SECONDS"
    )
    p_atspi = sub.add_parser("atspi", help="drive OBS over AT-SPI (accessibility)")
    p_atspi.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        metavar="ARGS",
        help="atspi subcommand and arguments; APP is injected",
    )
    sub.add_parser("obslog", help="print the path of the newest OBS log file")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested harness command."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in PASSTHROUGH:
        cmd, rest = argv[0], argv[1:]
        if cmd == "start":
            return driver.start(rest)
        if cmd == "windows":
            return driver.windows(rest)
        return driver.atspi(rest)
    args = build_parser().parse_args(argv)
    if args.command == "start":
        return driver.start(args.app_args)
    if args.command == "stop":
        return driver.stop()
    if args.command == "save":
        return driver.save(args.name)
    if args.command == "windows":
        return driver.windows(args.args)
    if args.command == "wait":
        return driver.wait_cmd(args.pattern, args.timeout)
    if args.command == "atspi":
        return driver.atspi(args.args)
    if args.command == "obslog":
        return driver.obslog()
    return 2  # unreachable: argparse rejects unknown commands
