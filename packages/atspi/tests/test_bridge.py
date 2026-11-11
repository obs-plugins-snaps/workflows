"""Tests for get_app's registration polling (no session bus needed)."""

from __future__ import annotations

import pytest
from atspi import bridge
from gi.repository import GLib  # ty: ignore[import-not-found]  (dynamic introspection module)


class _StubApp:
    """Minimal accessible stand-in; only get_name is ever called."""

    def get_name(self) -> str:
        return "obs"


def _flaky_app_resolver(calls: dict[str, int], register_on: int, fail_first: int = 0):
    """Return a resolver that yields no app until *register_on* calls in."""
    app = _StubApp()

    def resolver(name: str) -> _StubApp | None:
        calls["n"] += 1
        if calls["n"] <= fail_first:
            raise GLib.Error(GLib.quark_from_string("test"), 0, "bus not ready")
        return app if calls["n"] >= register_on else None

    return resolver


def test_get_app_polls_until_app_registers(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(bridge, "_resolve_app", _flaky_app_resolver(calls, 3))
    monkeypatch.setattr(bridge, "POLL_INTERVAL", 0.0)
    app = bridge.get_app("obs", wait=5.0)
    assert app is not None and app.get_name() == "obs"
    assert calls["n"] == 3


def test_get_app_polls_through_bus_errors(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(
        bridge, "_resolve_app", _flaky_app_resolver(calls, register_on=3, fail_first=2)
    )
    monkeypatch.setattr(bridge, "POLL_INTERVAL", 0.0)
    assert bridge.get_app("obs", wait=5.0) is not None
    assert calls["n"] == 3


def test_get_app_times_out_when_app_never_registers(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(bridge, "_resolve_app", _flaky_app_resolver(calls, 10**9))
    monkeypatch.setattr(bridge, "POLL_INTERVAL", 0.0)
    assert bridge.get_app("obs", wait=0.05) is None


def test_get_app_reraises_bus_errors_without_wait(monkeypatch):
    calls = {"n": 0}

    def resolver(name: str):
        calls["n"] += 1
        raise GLib.Error(GLib.quark_from_string("test"), 0, "bus not ready")

    monkeypatch.setattr(bridge, "_resolve_app", resolver)
    with pytest.raises(GLib.Error):
        bridge.get_app("obs")
    assert calls["n"] == 1


def test_get_app_returns_immediately_when_present(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(bridge, "_resolve_app", _flaky_app_resolver(calls, 1))
    monkeypatch.setattr(bridge, "POLL_INTERVAL", 0.0)
    assert bridge.get_app("obs", wait=5.0) is not None
    assert calls["n"] == 1
