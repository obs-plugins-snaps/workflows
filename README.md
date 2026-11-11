# workflows

Shared reusable GitHub Actions workflows for the OBS Studio plugin snaps in
the `obs-plugins-snaps` organization. The individual plugin snap
repositories call these workflows from their own CI, so each plugin repo
only contains a small caller workflow instead of a full copy of the build
logic.

GitHub requires reusable workflows to live in the `.github/workflows/`
directory of the repository that hosts them, hence the nested path here.

## Available workflows

### `build-snap.yml`

Packs the snap in the calling repository and uploads it as a build
artifact. The artifact name is prefixed with the `plugin_name` input so
that artifacts from several plugin snaps can be told apart.

Intended to run on pull requests and pushes to branches other than
`main`; for releases from `main`, use `release-to-edge.yml` instead, which
reuses this workflow to pack the snap.

Inputs:

| Input             | Required | Description                                                          |
| ----------------- | -------- | -------------------------------------------------------------------- |
| `plugin_name`     | yes      | Upstream plugin project name, used in the artifact name              |
| `timeout-minutes` | no       | Pack job runtime cap in minutes (default 60); raise it for slow builds |

### `release-to-edge.yml`

Builds the snap by calling `build-snap.yml`, then releases the packed snap
to the `latest/edge` channel of the Snap Store. Intended to be called on
every push to `main`, so that edge always tracks the current development
state. Prints the uploaded revisions in the workflow summary.

Inputs:

| Input             | Required | Description                                                                                   |
| ----------------- | -------- | --------------------------------------------------------------------------------------------- |
| `plugin_name`     | yes      | Upstream plugin project name; the snap name is `<plugin_name>-obs-studio`                     |
| `timeout-minutes` | no       | Build and release job runtime cap in minutes (default 60); raise it for slow builds           |

Secrets:

| Secret                  | Description                                                                                     |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| `SNAPCRAFT_STORE_EDGE`  | Snap Store credentials with permission to upload and release to `latest/edge` for the snap.      |

### `promote.yml`

Promotes already uploaded revisions of the snap to a risk level chosen by
the maintainer (`beta`, `candidate`, or `stable`). Intended to be called
on `workflow_dispatch` events: the caller declares a `workflow_dispatch`
trigger with matching inputs and forwards them to this reusable workflow.
GitHub requires write access to dispatch a workflow, so no extra
permission check is needed. The outcome is printed in the workflow
summary.

Inputs:

| Input         | Required | Description                                                                        |
| ------------- | -------- | ---------------------------------------------------------------------------------- |
| `plugin_name` | yes      | Upstream plugin project name; the snap name is `<plugin_name>-obs-studio`          |
| `revision`    | no       | Revision to promote: a store revision number, a comma-separated list of them, or `latest` (default; the newest revision currently in `latest/edge`) |
| `channel`     | yes      | Target risk level: `beta`, `candidate`, or `stable`                                 |

Secrets:

| Secret                          | Description                                                                                              |
| ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `SNAPCRAFT_STORE_CREDENTIALS`   | Snap Store credentials with permission to release the snap to `beta`, `candidate`, and `stable`.          |

## e2e tooling

This repository is also a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
hosting the Python packages that implement end-to-end GUI testing for the
plugin snaps, Wayland-native (no X server involved):

| Package | Entry point | Purpose |
| ------- | ----------- | ------- |
| `sway-windows` | `sway-windows` | List windows on a running sway compositor, or find one by title (`swaymsg -t get_tree`). |
| `atspi` | `atspi` | Inspect and drive any accessibility-enabled application over AT-SPI: click by role and name, assert on accessible text. |
| `e2e-obs-plugins-snaps` | `e2e-obs` | The harness itself: starts a headless sway session, launches the `obs-studio` snap with its accessibility bridge forced on, and drives/asserts via the two libraries above. |

Harness commands:

```
e2e-obs start [APPARGS...]   # sway + launch OBS + wait for the window + save
e2e-obs save [NAME]          # screenshot -> shots/NAME.png
e2e-obs windows [ARGS...]    # list windows (forwards to sway-windows)
e2e-obs wait REGEX [SECS]    # poll the compositor for a window title
e2e-obs atspi ARGS...        # forward to atspi, injecting the app name
e2e-obs stop                 # graceful shutdown + cleanup
e2e-obs obslog               # path of the newest OBS log file
```

State lives under `$E2E_OBS_HOME/.state` (default: the working directory);
screenshots go to `shots/`, logs to `logs/`. Environment overrides:
`OBS_TITLE_RE` (main window title regex, default `OBS`), `ATSPI_APP`
(application name on the accessibility bus, default `obs`). Install with uv
(`uv sync --all-packages`); the reusable `e2e-smoke` workflow consumes these
packages from its own checkout.

## Usage

From a plugin snap repository (as generated by the copier template in
`obs-plugins-snaps/template`):

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
    inputs:
      revision:
        description: "Revision (number or 'latest')"
        required: false
        default: latest
      channel:
        description: "beta, candidate or stable"
        required: true

jobs:
  # Pull requests: build only.
  build:
    if: github.event_name == 'pull_request'
    uses: obs-plugins-snaps/workflows/.github/workflows/build-snap.yml@main
    with:
      plugin_name: "source-record"

  # Every commit to main: release to latest/edge.
  release:
    if: github.event_name == 'push'
    uses: obs-plugins-snaps/workflows/.github/workflows/release-to-edge.yml@main
    with:
      plugin_name: "source-record"
    secrets: inherit

  # Maintainers promote by running this workflow from the Actions tab.
  promote:
    if: github.event_name == 'workflow_dispatch'
    uses: obs-plugins-snaps/workflows/.github/workflows/promote.yml@main
    with:
      plugin_name: "source-record"
      revision: ${{ inputs.revision }}
      channel: ${{ inputs.channel }}
    secrets: inherit
```

Reusable workflows must be referenced with a full ref (`@main` above), and
callers cannot add `runs-on` or `steps` to the calling job. Because the
workflows above reference store credentials directly, callers must pass
`secrets: inherit`.

