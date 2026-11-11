"""Command layer: one function per command, shared by every frontend.

The standalone ``atspi`` CLI and composed harnesses (e.g. ``e2e-obs atspi
...``) resolve the application, print, and exit through these functions, so
output formats and exit codes are defined exactly once. Each command takes
the *application name* and resolves it against the accessibility bus
(:mod:`atspi.bridge`, imported lazily), so frontends never touch GObject
introspection themselves.
"""

from __future__ import annotations

import json
import sys
import typing as t

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


def emit(fmt: str, lines: list[str], doc: t.Any) -> None:
    """Print a result in the requested output format."""
    if fmt == "json":
        print(json.dumps(doc, ensure_ascii=False))
    else:
        for line in lines:
            print(line)


def _get_app(name: str) -> t.Any:
    from atspi import bridge  # lazy: pulls in GObject introspection

    return bridge.get_app(name)


def apps(fmt: str = "text") -> int:
    """List the applications on the accessibility bus."""
    from atspi import bridge  # lazy: pulls in GObject introspection

    names = bridge.list_app_names()
    if names or fmt == "json":
        emit(fmt, names, names)
    else:
        print("No applications on the accessibility bus.", file=sys.stderr)
    return 0


def tree(app_name: str, depth: int = 3, fmt: str = "text") -> int:
    """Dump the accessibility tree of *app_name*."""
    app = _get_app(app_name)
    if app is None:
        error(f'cannot find application "{app_name}" on the accessibility bus')
        return 1
    lines = []
    doc = []
    for node, d in walk(app):
        if d <= depth:
            entry = {
                "depth": d,
                "role": node.get_role_name(),
                "name": node.get_name() or "",
            }
            doc.append(entry)
            lines.append("  " * d + f"{entry['role']}: {entry['name'][:70]}")
    emit(fmt, lines, doc)
    return 0


def find(
    app_name: str, role: str, pattern: str, wait: float = 0.0, fmt: str = "text"
) -> int:
    """Print the first node with *role* whose name matches *pattern*."""
    app = _get_app(app_name)
    if app is None:
        error(f'cannot find application "{app_name}" on the accessibility bus')
        return 1
    node = find_first(app, role, pattern, wait)
    if node is None:
        error(f'no {role} matching "{pattern}"{timeout_suffix(wait)}')
        return 1
    emit(
        fmt,
        [f"{node.get_role_name()}: {node.get_name()}"],
        {"role": node.get_role_name(), "name": node.get_name()},
    )
    return 0


def click(
    app_name: str, role: str, pattern: str, wait: float = 0.0, fmt: str = "text"
) -> int:
    """Perform the first action on the first matching node."""
    from atspi import bridge  # lazy: pulls in GObject introspection

    app = _get_app(app_name)
    if app is None:
        error(f'cannot find application "{app_name}" on the accessibility bus')
        return 1
    node = find_first(app, role, pattern, wait)
    if node is None:
        error(f'no {role} matching "{pattern}"{timeout_suffix(wait)}')
        return 1
    if node.get_n_actions() < 1:
        error(
            f'cannot click {node.get_role_name()} "{node.get_name()}": no actions available'
        )
        return 1
    ok = node.do_action(0)
    # get_action_name is deprecated upstream but there is no replacement for
    # reading an action's name; silence just that one message.
    with bridge.silence_deprecation(r"Atspi\.Action\.get_action_name is deprecated"):
        action = node.get_action_name(0)
    emit(
        fmt,
        [f"clicked [{action}] {node.get_role_name()}: {node.get_name()}"],
        {
            "clicked": bool(ok),
            "action": action,
            "role": node.get_role_name(),
            "name": node.get_name(),
        },
    )
    return 0 if ok else 1


def text(
    app_name: str, role: str, pattern: str, wait: float = 0.0, fmt: str = "text"
) -> int:
    """Print the names of all nodes with *role* matching *pattern*."""
    app = _get_app(app_name)
    if app is None:
        error(f'cannot find application "{app_name}" on the accessibility bus')
        return 1
    hits = matching_names(app, role, pattern, wait)
    emit(fmt, hits, hits)
    return 0


def assert_cmd(
    app_name: str, pattern: str, wait: float = 0.0, fmt: str = "text"
) -> int:
    """Exit 0 if any accessible name matches *pattern*."""
    app = _get_app(app_name)
    if app is None:
        error(f'cannot find application "{app_name}" on the accessibility bus')
        return 1
    matched = any_name_matches(app, pattern, wait)
    if matched is None:
        error(f'no accessible name matching "{pattern}"{timeout_suffix(wait)}')
        return 1
    emit(fmt, [matched], {"matched": True, "name": matched})
    return 0
