"""Tests for driver logic that does not need a live compositor."""

from __future__ import annotations

import atspi
import atspi.commands
import pytest
from gi.repository import GLib  # ty: ignore[import-not-found]  (dynamic introspection module)

from e2e_obs import driver, session
from e2e_obs.cli import main

TREE = {
    "type": "root",
    "name": "root",
    "nodes": [
        {
            "type": "workspace",
            "name": "1",
            "nodes": [
                {
                    "type": "con",
                    "name": "OBS 32.2.0",
                    "rect": {"x": 0, "y": 27, "width": 1920, "height": 1053},
                }
            ],
            "floating_nodes": [],
        }
    ],
    "floating_nodes": [],
}


def test_find_window_rect_match(monkeypatch):
    monkeypatch.setattr(driver, "get_tree", lambda: TREE)
    assert driver.find_window_rect("OBS") == "0 27 1920 1053 OBS 32.2.0"


def test_find_window_rect_no_match(monkeypatch):
    monkeypatch.setattr(driver, "get_tree", lambda: TREE)
    assert driver.find_window_rect("nothing") is None


def test_find_window_rect_compositor_down(monkeypatch):
    def boom():
        raise FileNotFoundError("swaymsg")

    monkeypatch.setattr(driver, "get_tree", boom)
    assert driver.find_window_rect("OBS") is None


def test_start_already_running(home, monkeypatch, capsys):
    (session.state_dir() / "obs.pid").write_text(f"{driver.os.getpid()}\n")
    assert driver.start([]) == 0
    assert capsys.readouterr().out.startswith("OBS already running (pid ")


def test_wait_immediate_match(home, monkeypatch, capsys):
    (session.state_dir() / "wayland-display").write_text("wayland-1\n")
    monkeypatch.setattr(driver, "find_window_rect", lambda p: "0 0 1 1 OBS")
    assert driver.wait_cmd("OBS", timeout=1.0) == 0
    assert capsys.readouterr().out == "0 0 1 1 OBS\n"


class _Node:
    """Duck-typed AT-SPI node: tree walking plus action support."""

    def __init__(
        self,
        name: str,
        role: str,
        children: list[_Node] | None = None,
        n_actions: int = 1,
    ) -> None:
        self._name = name
        self._role = role
        self.children = children or []
        self._n_actions = n_actions
        self.actions_done: list[int] = []

    def get_child_count(self) -> int:
        return len(self.children)

    def get_child_at_index(self, i: int) -> _Node | None:
        return self.children[i] if i < len(self.children) else None

    def get_name(self) -> str:
        return self._name

    def get_role_name(self) -> str:
        return self._role

    def get_n_actions(self) -> int:
        return self._n_actions

    def do_action(self, i: int) -> bool:
        self.actions_done.append(i)
        return True


def _wizard_app(cancel: bool = True, closes: bool = True) -> _Node:
    """A wizard dialog; its Cancel button closes it unless *closes* is off."""
    dialog = _Node(
        "Auto-Configuration Wizard",
        "dialog",
        children=[_Node("Cancel", "push button")] if cancel else [],
    )
    app = _Node("obs", "application", children=[dialog])
    if cancel and closes:
        button = dialog.children[0]
        original_do_action = button.do_action

        def dismiss(i: int) -> bool:
            app.children.remove(dialog)
            return bool(original_do_action(i))

        button.do_action = dismiss  # type: ignore[method-assign]
    return app


def _bridge_stub(app: _Node | None):
    class _Bridge:
        @staticmethod
        def get_app(name: str, wait: float = 0.0) -> _Node | None:
            return app

    return _Bridge


def test_dismiss_wizard_clicks_cancel(home, monkeypatch):
    monkeypatch.setattr(driver, "WIZARD_DISMISS_SETTLE", 0.1)
    app = _wizard_app()
    monkeypatch.setattr(atspi, "bridge", _bridge_stub(app), raising=False)
    assert driver.dismiss_first_run_wizard() is True
    dialog = app.children
    assert dialog == []  # the fake click removed the dialog, as the real one


def test_dismiss_wizard_false_when_dialog_sticks(home, monkeypatch):
    monkeypatch.setattr(driver, "WIZARD_DISMISS_SETTLE", 0.1)
    monkeypatch.setattr(
        atspi,
        "bridge",
        _bridge_stub(_wizard_app(closes=False)),
        raising=False,
    )
    assert driver.dismiss_first_run_wizard() is False


def test_dismiss_wizard_none_when_no_dialog(home, monkeypatch):
    monkeypatch.setattr(
        atspi,
        "bridge",
        _bridge_stub(_Node("obs", "application")),
        raising=False,
    )
    assert driver.dismiss_first_run_wizard() is None


def test_dismiss_wizard_none_when_no_app(home, monkeypatch):
    monkeypatch.setattr(atspi, "bridge", _bridge_stub(None), raising=False)
    assert driver.dismiss_first_run_wizard() is None


def test_dismiss_wizard_false_when_cancel_missing(home, monkeypatch):
    monkeypatch.setattr(
        atspi, "bridge", _bridge_stub(_wizard_app(cancel=False)), raising=False
    )
    assert driver.dismiss_first_run_wizard() is False


def test_warmup_accessibility_ready(home, monkeypatch, capsys):
    calls = {"n": 0}

    class _Bridge:
        @staticmethod
        def list_app_names():
            calls["n"] += 1
            return []

    monkeypatch.setattr(atspi, "bridge", _Bridge, raising=False)
    driver.warmup_accessibility()
    assert calls["n"] == 1
    assert capsys.readouterr().out == "accessibility registry: ready\n"


def _bus_down_bridge() -> type:
    """Stub whose a11y bus never comes up (GLib.Error on every query)."""

    class _Bridge:
        @staticmethod
        def list_app_names():
            raise GLib.Error(GLib.quark_from_string("test"), 0, "bus not ready")

    return _Bridge


def test_warmup_accessibility_retries_then_warns(home, monkeypatch, capsys):
    monkeypatch.setattr(atspi, "bridge", _bus_down_bridge(), raising=False)
    monkeypatch.setattr(driver, "A11Y_WARMUP_TIMEOUT", 0.1)
    monkeypatch.setattr(driver, "A11Y_WARMUP_RETRY", 0.0)
    driver.warmup_accessibility()  # best-effort: returns instead of dying
    assert capsys.readouterr().err.endswith(
        "accessibility registry did not come up; continuing\n"
    )


def test_wait_timeout(home, monkeypatch, capsys):
    (session.state_dir() / "wayland-display").write_text("wayland-1\n")
    monkeypatch.setattr(driver, "find_window_rect", lambda p: None)
    with pytest.raises(SystemExit) as excinfo:
        driver.wait_cmd("OBS", timeout=0.3)
    assert excinfo.value.code == 1
    assert capsys.readouterr().err == "error: no window matching 'OBS' after 0.3s\n"


def test_defaults(monkeypatch, home):
    assert driver.title_re() == "OBS"
    assert driver.atspi_app() == "obs"
    monkeypatch.setenv("OBS_TITLE_RE", "my plugin")
    monkeypatch.setenv("ATSPI_APP", "source-record")
    assert driver.title_re() == "my plugin"
    assert driver.atspi_app() == "source-record"


def test_atspi_dispatch(home, monkeypatch):
    seen = []
    monkeypatch.setattr(
        atspi.commands, "apps", lambda fmt: seen.append(("apps", fmt)) or 0
    )
    monkeypatch.setattr(
        atspi.commands,
        "click",
        lambda app, role, pattern, wait, fmt: (
            seen.append(("click", app, role, pattern, wait, fmt)) or 0
        ),
    )
    monkeypatch.setattr(
        atspi.commands,
        "assert_cmd",
        lambda app, pattern, wait, fmt: seen.append(("assert", app, pattern)) or 0,
    )
    assert main(["atspi", "apps", "--format", "json"]) == 0
    assert main(["atspi", "click", "menu item", "About"]) == 0
    assert main(["atspi", "assert", "OBS"]) == 0
    assert seen == [
        ("apps", "json"),
        ("click", "obs", "menu item", "About", 0.0, "text"),
        ("assert", "obs", "OBS"),
    ]


def test_atspi_app_from_env(home, monkeypatch):
    seen = {}
    monkeypatch.setenv("ATSPI_APP", "source-record")
    monkeypatch.setattr(
        atspi.commands,
        "find",
        lambda app, role, pattern, wait, fmt: seen.update(app=app) or 0,
    )
    assert main(["atspi", "find", "frame", "OBS"]) == 0
    assert seen["app"] == "source-record"


def test_windows_dispatch(home, monkeypatch, capsys):
    seen = {}

    def fake_windows(pattern=None, fmt="text"):
        seen.update(pattern=pattern, fmt=fmt)
        return 0

    monkeypatch.setattr(driver, "windows", fake_windows)
    assert main(["windows"]) == 0
    assert seen == {"pattern": None, "fmt": "text"}
    assert main(["windows", "--format", "json", "OBS"]) == 0
    assert seen == {"pattern": "OBS", "fmt": "json"}


def test_obslog_missing(capsys):
    # No OBS snap logs on this machine (or none readable): clean error.
    rc = driver.obslog()
    if rc != 0:
        assert capsys.readouterr().err == "error: no OBS log file found\n"
