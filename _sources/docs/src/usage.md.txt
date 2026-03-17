# Usage

laxate is a tool for running [ASV (Airspeed Velocity)](https://asv.readthedocs.io/) benchmarks locally, in containers, or on cloud servers. It wraps ASV with a unified CLI and supports persistent configuration via `pyproject.toml`.

## Installation

```bash
pip install laxate

# For Hetzner Cloud support:
pip install "laxate[hetzner]"
```

## Quick start

```bash
# Run benchmarks locally
laxate run local

# Run benchmarks in a Docker container
laxate run docker --image python:3.12

# Generate and view an HTML report
laxate publish
laxate preview
```

## CLI reference

### `laxate run local`

Run ASV benchmarks in the current Python environment.

```bash
laxate run local [--config PATH] [--quick] [--machine NAME]
```

| Flag | pyproject.toml key | Description |
| --- | --- | --- |
| `--config` | `asv_config` | Path to `asv.conf.json` (relative to project root) |
| `--quick` / `-q` | `quick` | Run in ASV quick mode (fewer iterations) |
| `--machine` | `machine` | Machine name recorded in results |

### `laxate run docker`

Run ASV benchmarks inside a Docker or Podman container. The project directory is bind-mounted into the container so results are written back to the host.

```bash
laxate run docker [--image IMAGE] [--engine ENGINE] [--network NET]
                  [--init-command CMD ...] [--mount MOUNT ...]
                  [--container-name NAME]
                  [--config PATH] [--quick] [--machine NAME]
```

| Flag | pyproject.toml key | Description |
| --- | --- | --- |
| `--image` | `docker_image` | Container image (default: `python:3.11`) |
| `--engine` | `docker_engine` | `docker` or `podman` (default: `docker`) |
| `--network` | `docker_network` | Docker network mode (default: `host`) |
| `--init-command` | `docker_init_commands` | Shell command to run before benchmarks (repeatable). CLI values **append** to pyproject.toml list |
| `--mount` | `docker_mounts` | Extra bind mount in `-v` format, e.g. `/data:/data:ro` (repeatable). CLI values **append** to pyproject.toml list |
| `--container-name` | `docker_container_name` | Container name (default: `laxate-bench`) |
| `--config` | `asv_config` | Path to `asv.conf.json` |
| `--quick` / `-q` | `quick` | Quick mode |
| `--machine` | `machine` | Machine name |

Example with init commands and Podman:

```bash
laxate run docker \
  --engine podman \
  --image python:3.13 \
  --init-command "pip install uv" \
  --init-command "uv pip install -e .[develop]" \
  --mount /shared-cache:/cache:ro \
  --quick
```

### `laxate run hetzner`

Run ASV benchmarks on a Hetzner Cloud server. Requires the `hetzner` extra (`pip install "laxate[hetzner]"`).

```bash
laxate run hetzner [--token TOKEN] [--server-type TYPE] [--ssh-key PATH]
                   [--ssh-key-name NAME] [--branches BRANCHES]
                   [--commits RANGE] [--reuse] [--keep-server]
                   [--push] [--github-token TOKEN]
                   [--benchmark-repo URL] [--project-repo URL]
                   [--asv-config PATH] [--asv-machine-json PATH]
                   [--server-name NAME]
```

| Flag | pyproject.toml key | Description |
| --- | --- | --- |
| `--token` | — | Hetzner Cloud API token (or `HCLOUD_TOKEN` env var) |
| `--server-type` | — | Hetzner server type, e.g. `cx23`, `ccx33` |
| `--server-name` | `server_name_prefix` | Server name |
| `--ssh-key` | — | Path to SSH private key |
| `--ssh-key-name` | — | Name of SSH key registered in Hetzner |
| `--branches` | — | Comma-separated branches to benchmark (default: `main`) |
| `--commits` | — | Commit range, e.g. `HEAD~5..HEAD` |
| `--reuse` | — | Reuse an existing server instead of creating a new one |
| `--keep-server` | — | Don't delete the server after benchmarks |
| `--push` | — | Push results back to the repository |
| `--github-token` | — | GitHub token for pushing (or `GITHUB_TOKEN` env var) |
| `--benchmark-repo` | `benchmark_repo` | URL of the benchmark repository |
| `--project-repo` | `project_repo` | URL of the project repository |
| `--asv-config` | `asv_config` | ASV config path (relative to repo root) |
| `--asv-machine-json` | `asv_machine_json` | Path to `asv-machine.json` |

### `laxate publish`

Generate an HTML report from ASV results.

```bash
laxate publish [--config PATH]
```

| Flag | pyproject.toml key | Description |
| --- | --- | --- |
| `--config` | `asv_publish_config` | Path to the publish config (default: `asv.publish.conf.json`) |

### `laxate preview`

Start a local HTTP server to preview the HTML report.

```bash
laxate preview [--config PATH]
```

| Flag | pyproject.toml key | Description |
| --- | --- | --- |
| `--config` | `asv_publish_config` | Path to the publish config |

### `laxate compare`

Compare benchmark results between two commits.

```bash
laxate compare [--config PATH] [BASE] [HEAD]
```

| Flag | pyproject.toml key | Description |
| --- | --- | --- |
| `--config` | `asv_config` | Path to `asv.conf.json` |
| `BASE` | — | Base commit hash or ref |
| `HEAD` | — | Head commit hash or ref |

### `laxate cleanup hetzner`

Remove leftover Hetzner Cloud servers.

```bash
laxate cleanup hetzner [--token TOKEN] [--prefix PREFIX]
```

| Flag | pyproject.toml key | Description |
| --- | --- | --- |
| `--token` | — | Hetzner Cloud API token (or `HCLOUD_TOKEN` env var) |
| `--prefix` | `server_name_prefix` | Only delete servers whose names start with this prefix |

## Configuration via `pyproject.toml`

All persistent settings live under the `[tool.laxate]` table. CLI flags override these values. List fields (`docker_init_commands`, `docker_mounts`) are **appended** to when using CLI flags.

```toml
[tool.laxate]
# ASV paths (relative to project root)
asv_config = "laxate/asv.conf.json"
asv_publish_config = "laxate/asv.publish.conf.json"
asv_machine_json = "laxate/asv-machine.json"
results_dir = "laxate/results"

# Repository URLs (used by Hetzner runner for cloning)
benchmark_repo = "https://github.com/myorg/myrepo.git"
project_repo = "https://github.com/myorg/myrepo.git"

# Hetzner
server_name_prefix = "benchmark-runner"
python_versions = ["3.11", "3.12", "3.13"]
cloud_init_packages = ["git", "python3", "python3-pip", "python3-venv", "build-essential"]

# Local / shared
machine = "my-machine"
quick = false

# Docker / Podman
docker_image = "python:3.12"
docker_engine = "docker"          # or "podman"
docker_network = "host"           # or "bridge", "none", etc.
docker_container_name = "laxate-bench"
docker_init_commands = [
    "pip install uv",
    "uv pip install -e .[develop]",
]
docker_mounts = [
    "/shared/cache:/cache:ro",
]
```

### Full configuration key reference

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `asv_config` | string | `"asv.conf.json"` | Path to ASV run config |
| `asv_publish_config` | string | `"asv.publish.conf.json"` | Path to ASV publish config |
| `asv_machine_json` | string | `"asv-machine.json"` | Path to ASV machine definition |
| `results_dir` | string | `"results"` | Directory for benchmark results |
| `benchmark_repo` | string | `""` | Benchmark repository URL |
| `project_repo` | string | `""` | Project repository URL |
| `server_name_prefix` | string | `"benchmark-runner"` | Hetzner server name prefix |
| `python_versions` | list[string] | `["3.11", "3.12", "3.13"]` | Python versions for remote runners |
| `cloud_init_packages` | list[string] | `["git", ...]` | Packages installed via cloud-init on Hetzner |
| `machine` | string | `""` | Machine name for ASV results |
| `quick` | bool | `false` | Enable ASV quick mode |
| `docker_image` | string | `"python:3.11"` | Docker/Podman image |
| `docker_engine` | string | `"docker"` | Container engine (`docker` or `podman`) |
| `docker_network` | string | `"host"` | Container network mode |
| `docker_container_name` | string | `""` | Container name |
| `docker_init_commands` | list[string] | `[]` | Commands to run inside container before benchmarks |
| `docker_mounts` | list[string] | `[]` | Extra bind mounts in `-v` format |

## GitHub Actions

Example workflow using the laxate CLI:

```yaml
name: Benchmarks
on:
  workflow_dispatch:
  push:
    branches: [main]
    paths: ['benchmarks/**']

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - run: pip install -e ".[develop]"

      - name: Configure ASV
        run: |
          cp asv-machine.json ~/.asv-machine.json
          python -m asv machine --config asv.conf.json --verbose --yes

      - name: Run benchmarks
        run: laxate run local --machine github-actions

      - name: Publish report
        run: laxate publish

      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: docs/benchmarks
```