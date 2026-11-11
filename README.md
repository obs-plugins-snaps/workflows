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

### `e2e.yml`

Runs the end-to-end GUI tests for the plugin snap, on the artifact
built by `build-snap.yml` in the same run (so e2e always validates the
exact snap under review). Installs the store OBS Studio, sideloads the
plugin snap, connects the `obs-plugins` content interface, and runs
`pytest tests/e2e` from the calling repository using the harness
packages from this repository (see [e2e tooling](#e2e-tooling)). Tests
run in a headless Wayland session (sway) — no display server setup is
needed on the runner.

Scope: **amd64 only** for now — the tested artifact comes from the
calling repository's single-arch pack job. arm64 would additionally
need free arm64 runners, store arm64 builds of `obs-studio`, and
`snapcraft/pack` on arm64 runners; none verified yet.

Screenshots, harness state, and OBS logs are collected under `e2e-home/`
and uploaded as a `<plugin_name>-e2e` artifact, always, so failures can
be triaged from the artifact alone.

| Input             | Required | Description                                                                          |
| ----------------- | -------- | ------------------------------------------------------------------------------------ |
| `plugin_name`     | yes      | Upstream plugin project name; the snap name is `<plugin_name>-obs-studio`            |
| `pytest_args`     | no       | Extra pytest arguments passed through to the suite                                                 |
| `tests_path`      | no       | Path of the pytest e2e suite, relative to the repository root (default `tests/e2e`)  |
| `timeout-minutes` | no       | Job runtime cap in minutes (default 30); raise it at the call site for slow plugins  |

The calling repository must contain a `tests/e2e` pytest suite (as
generated by the copier template). While the suite soaks, keep the
check out of the required checks in branch protection — it reports on
every pull request without blocking merges — and promote it to a
required check once it proves stable:

```yaml
  e2e:
    if: github.event_name == 'pull_request'
    needs: build  # the e2e job tests the artifact built above
    uses: obs-plugins-snaps/workflows/.github/workflows/e2e.yml@main
    with:
      plugin_name: "source-record"
```

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
(`uv sync --all-packages`); the reusable `e2e` workflow consumes these
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

### Staging call sites (planned)

The meta repository's staging flow will call `e2e.yml` for draft
plugin snaps, before graduation (and therefore before the store name is
registered — the suite must never depend on store state, and it doesn't).
The planned contract, requiring no fork of the harness:

1. render the copier template over `staging/<name>/` (so
   `staging/<name>/tests/e2e` exists);
2. overlay the draft `snapcraft.yaml`;
3. build and upload the artifact under the standard
   `<plugin_name>-snap` name (`download-artifact` is run-scoped, so
   `needs:` preserves the built-in-the-same-run provenance);
4. call `e2e.yml` with `tests_path: staging/<name>/tests/e2e`.

Staging checks are blocking from the start (the soak exemption only
applies to the plugin repositories' own CI).

Note on build/test parity: the e2e environment installs
`obs-studio/latest/stable` from the store, matching the template's
`build-snaps:` entry. Plugins overriding `build-snaps:` silently
diverge from the tested runtime.

