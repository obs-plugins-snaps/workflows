"""Tests for matching over fake accessibility trees."""

from __future__ import annotations

from atspi.tree import (
    any_name_matches,
    find_first,
    matching_names,
    timeout_suffix,
    walk,
)


def test_find_first_fullmatch(app):
    node = find_first(app, "menu item", "About")
    assert node is not None
    assert node.get_role_name() == "menu item"


def test_find_first_fullmatch_is_anchored(app):
    # "Abou" must not match "About" under fullmatch semantics
    assert find_first(app, "menu item", "Abou") is None


def test_find_first_wrong_role(app):
    assert find_first(app, "push button", "About") is None


def test_matching_names_search(app):
    hits = matching_names(app, "menu item", "Ab")
    assert hits == ["About"]


def test_matching_names_no_hit(app):
    assert matching_names(app, "menu item", "zzz") == []


def test_any_name_matches(app):
    assert any_name_matches(app, "OBS") == "OBS 32.2.0 - Profile"


def test_any_name_matches_none(app):
    assert any_name_matches(app, "no-such-thing") is None


def test_walk_depth_first(app):
    seen = [(node.get_name(), depth) for node, depth in walk(app)]
    assert ("obs", 0) in seen
    assert ("OBS 32.2.0 - Profile", 1) in seen
    assert ("About", 4) in seen


def test_timeout_suffix():
    assert timeout_suffix(0) == ""
    assert timeout_suffix(0.5) == " after 0.5s"
    assert timeout_suffix(10) == " after 10s"
    assert timeout_suffix(2.4) == " after 2.4s"
