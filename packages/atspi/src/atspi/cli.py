"""Command-line interface for ``atspi``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from atspi.tree import (
    any_name_matches,
    find_first,
    matching_names,
    timeout_suffix,
    walk,
)


def error(message: str) -> None:
    """Print a lowercase, succinct error message in snap style."""
    print(f"error: {message}", file=sys.stderr)


def emit(args: argparse.Namespace, lines: list[str], doc: Any) -> None:
    """Print a result in the requested output format."""
    if args.format == "json":
        print(json.dumps(doc, ensure_ascii=False))
    else:
        for line in lines:
            print(line)


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
    """Parse arguments and run the requested AT-SPI query or action."""
    args = build_parser().parse_args(argv)
    # Imported lazily: pulls in GObject introspection and needs a session bus
    # only when actually querying the registry.
    from atspi import bridge

    if args.command == "apps":
        names = bridge.list_app_names()
        if names or args.format == "json":
            emit(args, names, names)
        else:
            print("No applications on the accessibility bus.", file=sys.stderr)
        return 0

    app = bridge.get_app(args.app)
    if app is None:
        error(f'cannot find application "{args.app}" on the accessibility bus')
        return 1

    if args.command == "tree":
        lines = []
        doc = []
        for node, depth in walk(app):
            if depth <= args.depth:
                entry = {
                    "depth": depth,
                    "role": node.get_role_name(),
                    "name": node.get_name() or "",
                }
                doc.append(entry)
                lines.append("  " * depth + f"{entry['role']}: {entry['name'][:70]}")
        emit(args, lines, doc)
        return 0

    if args.command == "find":
        node = find_first(app, args.role, args.pattern, args.wait)
        if node is None:
            error(
                f'no {args.role} matching "{args.pattern}"{timeout_suffix(args.wait)}'
            )
            return 1
        emit(
            args,
            [f"{node.get_role_name()}: {node.get_name()}"],
            {"role": node.get_role_name(), "name": node.get_name()},
        )
        return 0

    if args.command == "click":
        node = find_first(app, args.role, args.pattern, args.wait)
        if node is None:
            error(
                f'no {args.role} matching "{args.pattern}"{timeout_suffix(args.wait)}'
            )
            return 1
        if node.get_n_actions() < 1:
            error(
                f'cannot click {node.get_role_name()} "{node.get_name()}": no actions available'
            )
            return 1
        ok = node.do_action(0)
        action = node.get_action_name(0)
        emit(
            args,
            [f"clicked [{action}] {node.get_role_name()}: {node.get_name()}"],
            {
                "clicked": bool(ok),
                "action": action,
                "role": node.get_role_name(),
                "name": node.get_name(),
            },
        )
        return 0 if ok else 1

    if args.command == "text":
        hits = matching_names(app, args.role, args.pattern, args.wait)
        emit(args, hits, hits)
        return 0

    if args.command == "assert":
        matched = any_name_matches(app, args.pattern, args.wait)
        if matched is None:
            error(
                f'no accessible name matching "{args.pattern}"{timeout_suffix(args.wait)}'
            )
            return 1
        emit(args, [matched], {"matched": True, "name": matched})
        return 0

    return 2  # unreachable: argparse rejects unknown commands
