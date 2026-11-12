"""Tests for the sway-windows CLI surface."""

from __future__ import annotations

import json

import pytest
import sway_windows.cli
from sway_windows.cli import main


def test_list_text(tree, capsys):
    assert main([]) == 0
    assert capsys.readouterr().out == "OBS 32.2.0 | 1920x1053+0+27\n"


def test_list_json(tree, capsys):
    assert main(["--format", "json"]) == 0
    (doc,) = json.loads(capsys.readouterr().out)
    assert doc["title"] == "OBS 32.2.0"


def test_find_match(tree, capsys):
    assert main(["OBS"]) == 0
    assert capsys.readouterr().out == "0 27 1920 1053 OBS 32.2.0\n"


def test_find_no_match_is_silent(tree, capsys):
    assert main(["nothing-matches"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_find_match_json(tree, capsys):
    assert main(["--format", "json", "OBS"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc == {
        "title": "OBS 32.2.0",
        "x": 0,
        "y": 27,
        "width": 1920,
        "height": 1053,
    }


def test_unreachable_compositor(monkeypatch, capsys):
    def boom():
        raise FileNotFoundError("swaymsg")

    monkeypatch.setattr(sway_windows.cli, "get_tree", boom)
    assert main([]) == 1
    assert capsys.readouterr().err == "error: cannot connect to the sway compositor\n"


def test_help_flag(tree, capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    assert "options:" in capsys.readouterr().out.lower()


def test_bad_format_is_usage_error(tree):
    with pytest.raises(SystemExit) as excinfo:
        main(["--format", "yaml"])
    assert excinfo.value.code == 2
