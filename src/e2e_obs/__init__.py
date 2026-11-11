"""Wayland-native headless GUI harness for the obs-studio snap.

Composes the ``atspi`` and ``sway-windows`` libraries into a session
manager: sway runs headless (``WLR_BACKENDS=headless``), OBS is launched
through the snap with its accessibility bridge forced on, and the harness
drives and asserts via AT-SPI. No X server involved anywhere; interaction is
semantic (no screen coordinates), screenshots go through grim.

CLI::

    e2e-obs start [APPARGS...]   # sway + launch OBS + wait + save
    e2e-obs save [NAME]          # screenshot -> shots/NAME.png
    e2e-obs windows [ARGS...]    # list windows (see sway-windows)
    e2e-obs wait REGEX [SECS]    # poll compositor for a window title
    e2e-obs atspi ARGS...        # forward to atspi, injecting the app name
    e2e-obs stop                 # graceful shutdown + cleanup
    e2e-obs obslog               # path of the newest OBS log file

State lives under ``$E2E_OBS_HOME/.state`` (default: the working directory);
screenshots in ``shots/``, logs in ``logs/``. Environment overrides:
``OBS_TITLE_RE`` (main window title regex, default "OBS") and ``ATSPI_APP``
(accessibility application name, default "obs").

Exit codes: 0 on success, 1 on failure, 2 on usage error.
"""

from e2e_obs.cli import build_parser, main

__all__ = ["build_parser", "main"]
