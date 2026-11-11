"""Tests for driver logic that does not need a live compositor."""

from __future__ import annotations

import pytest

from e2e_obs import driver, session

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


def test_atspi_injects_app(monkeypatch, home):
    seen = {}

    def fake_main(argv):
        seen["argv"] = argv
        return 0

    monkeypatch.setattr(driver, "atspi_main", fake_main)
    assert driver.atspi(["click", "menu item", "About"]) == 0
    assert seen["argv"] == ["click", "obs", "menu item", "About"]
    assert driver.atspi(["apps"]) == 0
    assert seen["argv"] == ["apps"]


def test_obslog_missing(capsys):
    # No OBS snap logs on this machine (or none readable): clean error.
    rc = driver.obslog()
    if rc != 0:
        assert capsys.readouterr().err == "error: no OBS log file found\n"
