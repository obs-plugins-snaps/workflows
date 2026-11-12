# atspi

Inspect and drive GUI applications over
[AT-SPI](https://www.freedesktop.org/wiki/Accessibility/AT-SPI2/)
(accessibility): pressing buttons and menus by role and name, asserting on
accessible text — no screen coordinates involved. Works with any
accessibility-enabled application on the session bus, Wayland or X11.

Useful as a CLI or as a small library for semantic GUI testing.

## CLI

```
atspi apps                   # list accessibility applications
atspi tree APP [DEPTH]       # dump the application tree (default 3)
atspi find APP ROLE NAME     # first node with ROLE whose name matches regex NAME
atspi click APP ROLE NAME    # perform the first action on that node
atspi text APP ROLE REGEX    # names of all matching nodes
atspi assert APP REGEX       # exit 0 if any accessible name matches
```

Options: `--format text|json` (default: text); `--wait SECONDS` polls until a
match appears. `ROLE` uses AT-SPI role names (`push button`, `menu item`,
`frame`...); `NAME` is a Python regular expression.

```
$ atspi click obs 'menu item' About --wait 10
clicked [click] menu item: About

$ atspi assert obs 'OBS 32\.2\.0' && echo matches
matches
```

## Library

```python
from atspi import find_first, walk
from atspi.bridge import get_app

app = get_app("obs")
for node, depth in walk(app):
    print("  " * depth, node.get_role_name(), node.get_name())
```

Requires a session bus (`$DBUS_SESSION_BUS_ADDRESS` or the default user bus)
on which the target application is running with its accessibility bridge
enabled, and GObject introspection data for AT-SPI (Debian/Ubuntu:
`gir1.2-atspi-2.0`).

Exit codes: 0 on success/match, 1 on no match/action failure, 2 on usage
error.
