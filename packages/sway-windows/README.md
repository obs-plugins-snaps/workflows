# sway-windows

List windows on a running [sway](https://swaywm.org/) compositor, or find one
by title, via `swaymsg -t get_tree`. The socket is taken from `$SWAYSOCK` when
set, falling back to sway's default.

Useful as a CLI or as a small library to inspect a Wayland session managed by
sway (or another wlroots compositor speaking the sway IPC protocol).

## CLI

```
sway-windows [--format text|json]        # list every named window
sway-windows [--format text|json] REGEX  # first matching window as
                                         # "x y width height title"
```

`REGEX` is a Python regular expression matched against window titles
(`re.search`). Silent exit 1 when nothing matches (so callers can poll).

```
$ sway-windows
OBS 32.2.0 | 1920x1053+0+27

$ sway-windows --format json OBS
{"title": "OBS 32.2.0", "x": 0, "y": 27, "width": 1920, "height": 1053}
```

## Library

```python
from sway_windows import get_tree, named_windows

for window in named_windows(get_tree()):
    print(window["name"], window["rect"])
```

Exit codes: 0 on success, 1 when nothing matches or sway is unreachable,
2 on usage error.
