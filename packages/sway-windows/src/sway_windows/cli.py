"""Command-line interface for ``sway-windows``."""

from __future__ import annotations

import argparse
import subprocess
import sys

from sway_windows.tree import find_window, get_tree, list_windows, named_windows


def error(message: str) -> None:
    """Print a lowercase, succinct error message in snap style."""
    print(f"error: {message}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ``sway-windows`` CLI."""
    parser = argparse.ArgumentParser(
        prog="sway-windows",
        description="List windows on a running sway compositor, or find one by title.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "pattern",
        nargs="?",
        metavar="REGEX",
        help="print the first window whose title matches this regex; "
        "without it, list all named windows",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested window query."""
    args = build_parser().parse_args(argv)
    try:
        windows = named_windows(get_tree())
    except (subprocess.CalledProcessError, FileNotFoundError):
        error("cannot connect to the sway compositor")
        return 1
    if args.pattern is not None:
        return find_window(windows, args.pattern, args.format)
    list_windows(windows, args.format)
    return 0
