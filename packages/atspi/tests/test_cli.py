"""Tests for the atspi CLI surface, dispatching through a fake bridge."""

from __future__ import annotations

import json

import pytest
from atspi.cli import main


def test_apps(fake_bridge, capsys):
    assert main(["apps"]) == 0
    assert capsys.readouterr().out == "obs\n"


def test_apps_empty_bus_json(empty_bridge, capsys):
    assert main(["apps", "--format", "json"]) == 0
    assert capsys.readouterr().out == "[]\n"


def test_apps_empty_bus_text(empty_bridge, capsys):
    assert main(["apps"]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "No applications on the accessibility bus.\n"


def test_tree_text(fake_bridge, capsys):
    assert main(["tree", "obs", "2"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "application: obs",
        "  frame: OBS 32.2.0 - Profile",
        "    menu bar: ",
    ]  # depth limit respected


def test_tree_json(fake_bridge, capsys):
    assert main(["tree", "obs", "3", "--format", "json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc[0] == {"depth": 0, "role": "application", "name": "obs"}
    assert doc[-1] == {"depth": 3, "role": "menu", "name": "Help"}


def test_unknown_app(fake_bridge, capsys):
    assert main(["tree", "nosuchapp"]) == 1
    assert capsys.readouterr().err == (
        'error: cannot find application "nosuchapp" on the accessibility bus\n'
    )


def test_find(fake_bridge, capsys):
    # find uses fullmatch semantics: the pattern must match the whole name
    assert main(["find", "obs", "frame", "OBS 32\\.2\\.0.*"]) == 0
    assert capsys.readouterr().out == "frame: OBS 32.2.0 - Profile\n"


def test_find_no_match(fake_bridge, capsys):
    assert main(["find", "obs", "push button", "Nothing"]) == 1
    assert capsys.readouterr().err == ('error: no push button matching "Nothing"\n')


def test_find_wait_timeout(fake_bridge, capsys):
    assert main(["find", "obs", "push button", "Nothing", "--wait", "0.4"]) == 1
    assert capsys.readouterr().err == (
        'error: no push button matching "Nothing" after 0.4s\n'
    )


def test_click(fake_bridge, capsys):
    assert main(["click", "obs", "menu item", "About"]) == 0
    out = capsys.readouterr().out
    assert out == "clicked [click] menu item: About\n"
    assert fake_bridge._about.actions_done == [0]


def test_click_json(fake_bridge, capsys):
    assert main(["click", "obs", "menu item", "About", "--format", "json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc == {
        "clicked": True,
        "action": "click",
        "role": "menu item",
        "name": "About",
    }


def test_click_no_actions(fake_bridge, capsys):
    fake_bridge._app._n_actions = 0
    assert main(["click", "obs", "application", "obs"]) == 1
    assert capsys.readouterr().err == (
        'error: cannot click application "obs": no actions available\n'
    )


def test_text(fake_bridge, capsys):
    assert main(["text", "obs", "menu", "Hel"]) == 0
    assert capsys.readouterr().out == "Help\n"


def test_text_empty_json(fake_bridge, capsys):
    assert main(["text", "obs", "menu", "zzz", "--format", "json"]) == 0
    assert capsys.readouterr().out == "[]\n"


def test_assert_match(fake_bridge, capsys):
    assert main(["assert", "obs", "OBS 32"]) == 0
    assert capsys.readouterr().out == "OBS 32.2.0 - Profile\n"


def test_assert_no_match(fake_bridge, capsys):
    assert main(["assert", "obs", "never-there"]) == 1
    assert capsys.readouterr().err == (
        'error: no accessible name matching "never-there"\n'
    )


def test_help_exit_code(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0


def test_missing_command_is_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2
