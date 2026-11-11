"""Shared fakes and fixtures for atspi tests (no session bus needed)."""

from __future__ import annotations

import contextlib
import dataclasses
import sys

import pytest


@dataclasses.dataclass
class FakeNode:
    """Duck-typed stand-in for an ``Atspi.Accessible`` node."""

    name: str | None
    role: str
    children: list[FakeNode] = dataclasses.field(default_factory=list)
    n_actions: int = 1
    actions_done: list[int] = dataclasses.field(default_factory=list)

    @classmethod
    def with_children(
        cls, name: str | None, role: str, *children: FakeNode, n_actions: int = 1
    ) -> FakeNode:
        """Convenience constructor: a node with its children attached."""
        return cls(name=name, role=role, children=list(children), n_actions=n_actions)

    def get_child_count(self) -> int:
        return len(self.children)

    def get_child_at_index(self, i: int) -> FakeNode | None:
        return self.children[i] if i < len(self.children) else None

    def get_name(self) -> str | None:
        return self.name

    def get_role_name(self) -> str:
        return self.role

    def get_n_actions(self) -> int:
        return self.n_actions

    def get_action_name(self, i: int) -> str:
        return "click"

    def do_action(self, i: int) -> bool:
        self.actions_done.append(i)
        return True


@dataclasses.dataclass
class FakeBridge:
    """Stub for ``atspi.bridge``; never touches GObject introspection."""

    app: FakeNode | None = None
    about: FakeNode | None = None

    def get_app(self, name: str) -> FakeNode | None:
        return self.app if self.app and name.lower() in ("obs", "o") else None

    def list_app_names(self) -> list[str]:
        return [self.app.get_name() or ""] if self.app else []

    @contextlib.contextmanager
    def silence_deprecation(self, message: str):
        """No-op stand-in for ``bridge.silence_deprecation``."""
        yield


def make_app() -> tuple[FakeNode, FakeNode]:
    """A small tree resembling OBS: app > window > menubar > menu > item."""
    about = FakeNode("About", "menu item")
    help_menu = FakeNode.with_children("Help", "menu", about)
    menubar = FakeNode.with_children("", "menu bar", help_menu)
    window = FakeNode.with_children("OBS 32.2.0 - Profile", "frame", menubar)
    app = FakeNode.with_children("obs", "application", window)
    return app, about


@pytest.fixture
def app() -> FakeNode:
    return make_app()[0]


@pytest.fixture
def fake_bridge(monkeypatch):
    """Inject a bridge stub so the CLI never touches GObject introspection.

    Returns the stub; ``stub.app`` is the root node and ``stub.about`` the
    About menu item (the only deeply named node worth clicking in tests).
    """
    app, about = make_app()
    stub = FakeBridge(app=app, about=about)
    monkeypatch.setitem(sys.modules, "atspi.bridge", stub)
    return stub


@pytest.fixture
def empty_bridge(monkeypatch):
    """Bridge stub reporting an empty accessibility bus."""
    stub = FakeBridge()
    monkeypatch.setitem(sys.modules, "atspi.bridge", stub)
    return stub
