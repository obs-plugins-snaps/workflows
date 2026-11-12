"""Tests for session state helpers."""

from __future__ import annotations

import os

import pytest

from e2e_obs import session


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("E2E_OBS_HOME", str(tmp_path))
    return tmp_path


def test_base_dir_env(home):
    assert session.base_dir() == home.resolve()


def test_dirs_created(home):
    assert session.state_dir() == home / ".state"
    assert session.shots_dir() == home / "shots"
    assert session.logs_dir() == home / "logs"
    assert (home / ".state").is_dir()
    assert (home / "shots").is_dir()
    assert (home / "logs").is_dir()


def test_sway_sock_under_state(home):
    assert session.sway_sock() == home / ".state" / "sway.sock"


def test_session_env(home):
    (session.state_dir() / "wayland-display").write_text("wayland-3\n")
    env = session.session_env()
    assert env["SWAYSOCK"] == str(home / ".state" / "sway.sock")
    assert env["WAYLAND_DISPLAY"] == "wayland-3"
    assert env["DBUS_SESSION_BUS_ADDRESS"].startswith("unix:path=/run/user/")


def test_apply_session_env(home, monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    (session.state_dir() / "wayland-display").write_text("wayland-3\n")
    session.apply_session_env()

    assert os.environ["WAYLAND_DISPLAY"] == "wayland-3"
    assert os.environ["SWAYSOCK"] == str(home / ".state" / "sway.sock")
    assert os.environ["XDG_RUNTIME_DIR"] == f"/run/user/{os.getuid()}"


def test_require_session_without_state(home, capsys):
    with pytest.raises(SystemExit) as excinfo:
        session.require_session()
    assert excinfo.value.code == 1
    assert capsys.readouterr().err == "error: no harness session (run 'start' first)\n"


def test_require_session_with_state(home):
    (session.state_dir() / "wayland-display").write_text("wayland-1\n")
    session.require_session()  # must not exit


def test_runtime_dir_default(monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert session.runtime_dir() == f"/run/user/{session.os.getuid()}"
