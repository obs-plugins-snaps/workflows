"""Compositor tree access: read ``swaymsg -t get_tree`` and extract windows.

The socket is taken from ``$SWAYSOCK`` when set, falling back to sway's
default. Every layout container that has a title counts as a window;
containers are visited depth-first.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any


def get_tree() -> dict[str, Any]:
    """Return the full compositor tree as parsed JSON."""
    cmd = ["swaymsg", "-t", "get_tree", "--raw"]
    if sock := os.environ.get("SWAYSOCK"):
        cmd += ["-s", sock]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def named_windows(node: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every layout container that has a title, in depth-first order."""
    found: list[dict[str, Any]] = []
    if node.get("type") == "con" and node.get("name"):
        found.append(node)
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        found.extend(named_windows(child))
    return found


def window_doc(w: dict[str, Any]) -> dict[str, Any]:
    """Return the JSON document for one window."""
    r = w["rect"]
    return {
        "title": w["name"],
        "x": r["x"],
        "y": r["y"],
        "width": r["width"],
        "height": r["height"],
    }


def list_windows(windows: list[dict[str, Any]], fmt: str = "text") -> None:
    """Print every window, one per line, in *fmt* format."""
    if fmt == "json":
        print(json.dumps([window_doc(w) for w in windows], ensure_ascii=False))
        return
    for w in windows:
        r = w["rect"]
        print(f"{w['name']} | {r['width']}x{r['height']}+{r['x']}+{r['y']}")


def find_window(windows: list[dict[str, Any]], pattern: str, fmt: str = "text") -> int:
    """Print the first window whose title matches *pattern*; exit 1 if none.

    Silent exit 1 on no match: callers poll this in a loop, so stderr must
    stay quiet.
    """
    for w in windows:
        if re.search(pattern, str(w["name"])):
            if fmt == "json":
                print(json.dumps(window_doc(w), ensure_ascii=False))
            else:
                r = w["rect"]
                print(f"{r['x']} {r['y']} {r['width']} {r['height']} {w['name']}")
            return 0
    return 1
