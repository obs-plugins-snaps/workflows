"""Command-line interface for ``atspi``."""

from __future__ import annotations

import argparse

from atspi import commands


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the ``atspi`` CLI."""
    parser = argparse.ArgumentParser(
        prog="atspi",
        description="Inspect and drive GUI applications over AT-SPI (accessibility).",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("apps", parents=[common], help="list accessibility applications")
    p_tree = sub.add_parser("tree", parents=[common], help="dump the application tree")
    p_tree.add_argument("app")
    p_tree.add_argument("depth", nargs="?", type=int, default=3)
    wait_help = "poll until a match appears, up to SECONDS (default: single check)"
    for name, help_text in (
        ("find", "print the first matching node"),
        ("click", "perform the first action on the first matching node"),
        ("text", "print names of all matching nodes"),
    ):
        p = sub.add_parser(name, parents=[common], help=help_text)
        p.add_argument("app")
        p.add_argument("role")
        p.add_argument("pattern")
        p.add_argument(
            "--wait", type=float, default=0.0, metavar="SECONDS", help=wait_help
        )
    p_assert = sub.add_parser(
        "assert", parents=[common], help="exit 0 if any accessible name matches"
    )
    p_assert.add_argument("app")
    p_assert.add_argument("pattern")
    p_assert.add_argument(
        "--wait", type=float, default=0.0, metavar="SECONDS", help=wait_help
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested AT-SPI command."""
    args = build_parser().parse_args(argv)
    if args.command == "apps":
        return commands.apps(args.format)
    if args.command == "tree":
        return commands.tree(args.app, args.depth, args.format)
    if args.command == "find":
        return commands.find(args.app, args.role, args.pattern, args.wait, args.format)
    if args.command == "click":
        return commands.click(args.app, args.role, args.pattern, args.wait, args.format)
    if args.command == "text":
        return commands.text(args.app, args.role, args.pattern, args.wait, args.format)
    if args.command == "assert":
        return commands.assert_cmd(args.app, args.pattern, args.wait, args.format)
    return 2  # unreachable: argparse rejects unknown commands
