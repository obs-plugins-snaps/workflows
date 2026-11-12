"""Tests for tree extraction and window matching (no compositor needed)."""

from __future__ import annotations

import pytest
from sway_windows.tree import find_window, named_windows, window_doc

OBS_WINDOW = {
    "type": "con",
    "name": "OBS 32.2.0",
    "rect": {"x": 0, "y": 27, "width": 1920, "height": 1053},
}

TREE = {
    "type": "root",
    "name": "root",
    "nodes": [
        {
            "type": "output",
            "name": "HEADLESS-1",
            "nodes": [
                {
                    "type": "workspace",
                    "name": "1",
                    "nodes": [OBS_WINDOW],
                    "floating_nodes": [],
                }
            ],
            "floating_nodes": [],
        }
    ],
    "floating_nodes": [],
}


def test_named_windows_finds_titled_container():
    windows = named_windows(TREE)
    assert [w["name"] for w in windows] == ["OBS 32.2.0"]


def test_named_windows_skips_untitled_and_other_types():
    tree = {
        "type": "root",
        "name": None,
        "nodes": [
            {"type": "output", "name": "HEADLESS-1", "nodes": [], "floating_nodes": []}
        ],
        "floating_nodes": [],
    }
    assert named_windows(tree) == []


def test_window_doc():
    assert window_doc(OBS_WINDOW) == {
        "title": "OBS 32.2.0",
        "x": 0,
        "y": 27,
        "width": 1920,
        "height": 1053,
    }


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("OBS", True),
        ("^OBS 32", True),
        ("32\\.2\\.0$", True),
        ("obs", False),  # case-sensitive by design
        ("no-such-window", False),
    ],
)
def test_find_window_matching(pattern, expected, capsys):
    windows = named_windows(TREE)
    rc = find_window(windows, pattern)
    out = capsys.readouterr().out
    if expected:
        assert rc == 0
        assert out == "0 27 1920 1053 OBS 32.2.0\n"
    else:
        assert rc == 1
        assert out == ""


def test_find_window_json(capsys):
    rc = find_window(named_windows(TREE), "OBS", fmt="json")
    assert rc == 0
    assert capsys.readouterr().out == (
        '{"title": "OBS 32.2.0", "x": 0, "y": 27, "width": 1920, "height": 1053}\n'
    )


def test_find_window_first_match_wins(capsys):
    windows = [
        {
            "type": "con",
            "name": "first",
            "rect": {"x": 0, "y": 0, "width": 1, "height": 1},
        },
        {
            "type": "con",
            "name": "second",
            "rect": {"x": 2, "y": 0, "width": 1, "height": 1},
        },
    ]
    assert find_window(windows, "sec") == 0
    assert capsys.readouterr().out == "2 0 1 1 second\n"
