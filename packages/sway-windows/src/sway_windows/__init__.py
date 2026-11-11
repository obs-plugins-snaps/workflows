"""List windows on a running sway compositor, or find one by title.

The compositor tree is read via ``swaymsg -t get_tree``; the socket is taken
from ``$SWAYSOCK`` when set, falling back to sway's default.

CLI::

    sway-windows [--format text|json]        list every named window
    sway-windows [--format text|json] REGEX  print the first window whose
                                             title matches REGEX as
                                             "x y width height title"

Options: ``--format text|json`` (default: text).

Exit codes: 0 on success, 1 when nothing matches or sway is unreachable,
2 on usage error.

Example::

    sway-windows --format json OBS
"""

from sway_windows.cli import build_parser, main
from sway_windows.tree import (
    find_window,
    get_tree,
    list_windows,
    named_windows,
    window_doc,
)

__all__ = [
    "build_parser",
    "find_window",
    "get_tree",
    "list_windows",
    "main",
    "named_windows",
    "window_doc",
]
