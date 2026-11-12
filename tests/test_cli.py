"""Tests for the e2e-obs CLI surface."""

from __future__ import annotations

import pytest

from e2e_obs import driver as driver_mod
from e2e_obs.cli import build_parser, main


def test_parse_start():
    args = build_parser().parse_args(["start", "--", "extra"])
    assert args.command == "start"
    assert args.app_args == ["extra"]
    assert args.dismiss_wizard is True


def test_parse_start_no_dismiss_wizard(monkeypatch):
    args = build_parser().parse_args(
        ["start", "--no-dismiss-wizard", "--", "--startdb"]
    )
    assert args.dismiss_wizard is False
    assert args.app_args == ["--startdb"]


def test_main_start_forwards_app_args(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        driver_mod,
        "start",
        lambda app_args, dismiss_wizard: (
            seen.update(app_args=app_args, dismiss_wizard=dismiss_wizard) or 0
        ),
    )
    assert main(["start", "--no-dismiss-wizard", "--", "--startdb"]) == 0
    assert seen == {"app_args": ["--startdb"], "dismiss_wizard": False}


def test_start_app_args_require_separator(capsys):
    # OBS flags are option-like: without -- they would be ambiguous with
    # harness flags, so the separator is required (Canonical CLI standard).
    with pytest.raises(SystemExit):
        build_parser().parse_args(["start", "--startdb"])
    assert "--startdb" in capsys.readouterr().err


def test_parse_wait():
    args = build_parser().parse_args(["wait", "OBS", "30"])
    assert args.command == "wait"
    assert args.pattern == "OBS"
    assert args.timeout == 30.0


def test_parse_wait_default():
    args = build_parser().parse_args(["wait", "OBS"])
    assert args.timeout == 60.0


def test_parse_windows():
    args = build_parser().parse_args(["windows", "--format", "json", "OBS"])
    assert args.command == "windows"
    assert args.pattern == "OBS"
    assert args.format == "json"


def test_parse_windows_default():
    args = build_parser().parse_args(["windows"])
    assert args.pattern is None
    assert args.format == "text"


def test_parse_atspi():
    args = build_parser().parse_args(["atspi", "click", "menu item", "About"])
    assert args.command == "atspi"
    assert args.atspi_command == "click"
    assert args.role == "menu item"
    assert args.pattern == "About"
    assert args.wait == 0.0


def test_parse_atspi_wait():
    args = build_parser().parse_args(
        ["atspi", "find", "frame", "OBS.*", "--wait", "10"]
    )
    assert args.atspi_command == "find"
    assert args.wait == 10.0


def test_parse_atspi_tree_depth():
    args = build_parser().parse_args(["atspi", "tree", "2"])
    assert args.atspi_command == "tree"
    assert args.depth == 2


def test_parse_save_default():
    args = build_parser().parse_args(["save"])
    assert args.command == "save"
    assert args.name is None


def test_missing_command_is_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2


def test_unknown_command_is_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["explode"])
    assert excinfo.value.code == 2


def test_help_exit_code(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0


def test_save_without_session(home, monkeypatch, capsys):
    # save requires a session; without one it dies with exit 1
    with pytest.raises(SystemExit) as excinfo:
        main(["save"])
    assert excinfo.value.code == 1
    assert "no harness session" in capsys.readouterr().err
