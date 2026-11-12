"""Inspect and drive GUI applications over AT-SPI (accessibility).

Semantic interaction with any accessibility-enabled application: pressing
buttons and menus by role and name, and asserting on accessible text — no
screen coordinates involved.

CLI::

    atspi apps                   list accessibility applications
    atspi tree APP [DEPTH]       dump the application tree (default 3)
    atspi find APP ROLE NAME     print the first node with ROLE whose name
                                 matches the regex NAME
    atspi click APP ROLE NAME    perform the first action on that node
    atspi text APP ROLE REGEX    print names of all matching nodes
    atspi assert APP REGEX       exit 0 if any accessible name matches

Options: ``--format text|json`` (default: text); ``--wait SECONDS`` polls
until a match appears (``find``, ``click``, ``text``, ``assert``). ROLE uses
AT-SPI role names (``push button``, ``menu item``, ``frame``...); NAME is a
Python regular expression.

Example::

    atspi click obs 'menu item' About --wait 10

Exit codes: 0 on success/match, 1 on no match/action failure, 2 on usage
error. Requires a session bus (``$DBUS_SESSION_BUS_ADDRESS`` or the default
user bus) on which the target application is running with its accessibility
bridge enabled.
"""

from atspi.tree import (
    MAX_DEPTH,
    POLL_INTERVAL,
    any_name_matches,
    find_first,
    matching_names,
    timeout_suffix,
    walk,
)

__all__ = [
    "MAX_DEPTH",
    "POLL_INTERVAL",
    "any_name_matches",
    "find_first",
    "matching_names",
    "timeout_suffix",
    "walk",
]
