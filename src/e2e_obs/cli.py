"""Command-line interface for the harness (``e2e-obs``)."""

from __future__ import annotations

import argparse
import sys
import typing as t

from e2e_obs import driver


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ``e2e-obs`` CLI."""
    parser = argparse.ArgumentParser(
        prog="e2e-obs",
        description="Wayland-native headless GUI harness for the obs-studio snap.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    p_start = sub.add_parser(
        "start",
        help="start a headless session, launch OBS and wait for its window",
        description="Start a headless session, launch OBS and wait for its main "
        "window. The first-run Auto-Configuration Wizard, when present, is "
        "dismissed by default.",
    )
    p_start.add_argument(
        "--dismiss-wizard",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="dismiss the first-run Auto-Configuration Wizard after launch, "
        "if present (default: dismiss)",
    )
    p_start.add_argument(
        "app_args",
        nargs="*",
        metavar="APPARGS",
        help="arguments passed to obs-studio; use -- to separate them from "
        "harness flags (e.g. 'start -- --startdb')",
    )
    sub.add_parser("stop", help="stop the session and clean up")
    p_save = sub.add_parser("save", help="screenshot the session")
    p_save.add_argument(
        "name", nargs="?", help="screenshot name (default: shot-HHMMSS)"
    )
    p_windows = sub.add_parser(
        "windows", help="list windows (title, geometry) or find one by title"
    )
    p_windows.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    p_windows.add_argument(
        "pattern",
        nargs="?",
        metavar="REGEX",
        help="print the first window whose title matches this regex; "
        "without it, list all named windows",
    )
    p_wait = sub.add_parser("wait", help="poll the compositor for a window title")
    p_wait.add_argument("pattern", metavar="REGEX")
    p_wait.add_argument(
        "timeout", nargs="?", type=float, default=60.0, metavar="SECONDS"
    )
    p_atspi = sub.add_parser(
        "atspi", help="drive the OBS application over AT-SPI (accessibility)"
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    atspi_sub = p_atspi.add_subparsers(
        dest="atspi_command", required=True, metavar="COMMAND"
    )
    atspi_sub.add_parser(
        "apps", parents=[common], help="list accessibility applications"
    )
    p_tree = atspi_sub.add_parser(
        "tree", parents=[common], help="dump the OBS accessibility tree"
    )
    p_tree.add_argument("depth", nargs="?", type=int, default=3)
    wait_help = "poll until a match appears, up to SECONDS (default: single check)"
    for name, help_text in (
        ("find", "print the first matching node"),
        ("click", "perform the first action on the first matching node"),
        ("text", "print names of all matching nodes"),
    ):
        p = atspi_sub.add_parser(name, parents=[common], help=help_text)
        p.add_argument("role")
        p.add_argument("pattern", metavar="REGEX")
        p.add_argument(
            "--wait", type=float, default=0.0, metavar="SECONDS", help=wait_help
        )
    p_assert = atspi_sub.add_parser(
        "assert", parents=[common], help="exit 0 if any accessible name matches"
    )
    p_assert.add_argument("pattern", metavar="REGEX")
    p_assert.add_argument(
        "--wait", type=float, default=0.0, metavar="SECONDS", help=wait_help
    )
    sub.add_parser("obslog", help="print the path of the newest OBS log file")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested harness command."""
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    handlers: dict[str, t.Callable[[], int]] = {
        "start": lambda: driver.start(
            args.app_args, dismiss_wizard=args.dismiss_wizard
        ),
        "stop": driver.stop,
        "save": lambda: driver.save(args.name),
        "windows": lambda: driver.windows(args.pattern, args.format),
        "wait": lambda: driver.wait_cmd(args.pattern, args.timeout),
        "atspi": lambda: driver.atspi(args),
        "obslog": driver.obslog,
    }
    return handlers[args.command]()
