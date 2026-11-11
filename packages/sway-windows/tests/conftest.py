"""Shared fixtures for sway-windows tests."""

from __future__ import annotations

import pytest
import sway_windows.cli

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
    ],
    "floating_nodes": [],
}


@pytest.fixture
def tree(monkeypatch):
    """Make the CLI read a fixed compositor tree instead of calling swaymsg."""
    monkeypatch.setattr(sway_windows.cli, "get_tree", lambda: TREE)
    return TREE
