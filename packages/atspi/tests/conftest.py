"""Shared fakes and fixtures for atspi tests (no session bus needed)."""

from __future__ import annotations

import sys

import pytest
from atspi.tree import walk


class FakeNode:
    """Duck-typed stand-in for an ``Atspi.Accessible`` node."""

    def __init__(
        self,
        name: str | None,
        role: str,
        children: tuple[FakeNode, ...] = (),
        n_actions: int = 1,
    ):
        self._name = name
        self._role = role
        self._children = list(children)
        self._n_actions = n_actions
        self.actions_done: list[int] = []

    def get_child_count(self) -> int:
        return len(self._children)

    def get_child_at_index(self, i: int) -> FakeNode | None:
        return self._children[i] if i < len(self._children) else None

    def get_name(self) -> str | None:
        return self._name

    def get_role_name(self) -> str:
        return self._role

    def get_n_actions(self) -> int:
        return self._n_actions

    def get_action_name(self, i: int) -> str:
        return "click"

    def do_action(self, i: int) -> bool:
        self.actions_done.append(i)
        return True


def make_app() -> tuple[FakeNode, FakeNode]:
    """A small tree resembling OBS: app > window > menubar > menu > item."""
    about = FakeNode("About", "menu item")
    help_menu = FakeNode("Help", "menu", children=(about,))
    menubar = FakeNode("", "menu bar", children=(help_menu,))
    window = FakeNode("OBS 32.2.0 - Profile", "frame", children=(menubar,))
    app = FakeNode("obs", "application", children=(window,))
    return app, about


class FakeBridge:
    """Stub for ``atspi.bridge``; never touches GObject introspection."""

    def __init__(self, app: FakeNode | None, about: FakeNode | None = None):
        self._app = app
        self._about = about

    def get_app(self, name: str) -> FakeNode | None:
        return self._app if self._app and name.lower() in ("obs", "o") else None

    def list_app_names(self) -> list[str]:
        return [self._app.get_name() or ""] if self._app else []


@pytest.fixture
def app() -> FakeNode:
    return make_app()[0]


@pytest.fixture
def fake_bridge(monkeypatch):
    """Inject a bridge stub so the CLI never touches GObject introspection.

    Returns the stub; ``stub._app`` is the root node and ``stub._about`` the
    About menu item (the only deeply named node worth clicking in tests).
    """
    app, about = make_app()
    stub = FakeBridge(app, about)
    monkeypatch.setitem(sys.modules, "atspi.bridge", stub)
    return stub


@pytest.fixture
def empty_bridge(monkeypatch):
    """Bridge stub reporting an empty accessibility bus."""
    stub = FakeBridge(None)
    monkeypatch.setitem(sys.modules, "atspi.bridge", stub)
    return stub


def test_walk_depth_first(app):
    seen = [(node.get_name(), depth) for node, depth in walk(app)]
    assert ("obs", 0) in seen
    assert ("OBS 32.2.0 - Profile", 1) in seen
    assert ("About", 4) in seen
