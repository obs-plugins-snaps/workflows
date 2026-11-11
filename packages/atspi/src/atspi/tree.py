"""Tree traversal and matching over accessibility nodes.

These helpers are pure logic over *any* object exposing the small AT-SPI
surface they need (``get_child_count``, ``get_child_at_index``, ``get_name``,
``get_role_name``), which keeps them testable without a session bus or
GObject introspection. The real nodes come from :mod:`atspi.bridge`.
"""

from __future__ import annotations

import re
import time
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gi.repository import Atspi  # ty: ignore[import-not-found]  (dynamic introspection module)

MAX_DEPTH = 30
POLL_INTERVAL = 0.2


def walk(
    node: Atspi.Accessible, depth: int = 0
) -> Generator[tuple[Any, int], None, None]:
    """Yield every accessible node under *node*, depth-first."""
    yield node, depth
    if depth >= MAX_DEPTH:
        return
    for i in range(node.get_child_count()):
        child = node.get_child_at_index(i)
        if child:
            yield from walk(child, depth + 1)


def find_first(
    app: Atspi.Accessible, role: str, pattern: str, wait: float = 0.0
) -> Atspi.Accessible | None:
    """Return the first matching node, polling for up to *wait* seconds."""
    deadline = time.monotonic() + wait
    while True:
        for node, _ in walk(app):
            if node.get_role_name() == role and re.fullmatch(
                pattern, node.get_name() or ""
            ):
                return node
        if time.monotonic() >= deadline:
            return None
        time.sleep(POLL_INTERVAL)


def matching_names(
    app: Atspi.Accessible, role: str, pattern: str, wait: float = 0.0
) -> list[str]:
    """Return all matching names, polling until one appears or *wait* expires."""
    deadline = time.monotonic() + wait
    while True:
        hits = [
            node.get_name() or ""
            for node, _ in walk(app)
            if node.get_role_name() == role
            and re.search(pattern, node.get_name() or "")
        ]
        if hits or time.monotonic() >= deadline:
            return hits
        time.sleep(POLL_INTERVAL)


def any_name_matches(
    app: Atspi.Accessible, pattern: str, wait: float = 0.0
) -> str | None:
    """Return the first matching accessible name, polling for up to *wait* seconds."""
    deadline = time.monotonic() + wait
    while True:
        for node, _ in walk(app):
            if re.search(pattern, node.get_name() or ""):
                return node.get_name()
        if time.monotonic() >= deadline:
            return None
        time.sleep(POLL_INTERVAL)


def timeout_suffix(wait: float) -> str:
    """Return the error-message suffix for a timed-out ``--wait``."""
    return f" after {wait:g}s" if wait else ""
