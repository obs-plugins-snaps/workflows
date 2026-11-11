"""Shared fixtures for driver tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Point the harness at a temporary state directory."""
    monkeypatch.setenv("E2E_OBS_HOME", str(tmp_path))
    return tmp_path
