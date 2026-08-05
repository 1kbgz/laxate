# CLI and configuration reference

Laxate invokes Benched in a prepared local, container, or Hetzner Cloud environment.
Configuration is loaded from `[tool.laxate]` in `pyproject.toml`. Command-line values
override configured scalar values. Repeated container initialization and mount options
append to configured lists.

## `laxate run local`

Runs `python -m benched run` in the current Python environment.

```text
laxate run local [--config PATH] [--quick] [--machine NAME]
```

| Option           | Configuration key | Description                           |
| ---------------- | ----------------- | ------------------------------------- |
| `--config`       | `benched_config`  | Path to target `pyproject.toml`       |
| `--quick`, `-q`  | `quick`           | Enables Benched quick mode            |
| `--machine NAME` | `machine`         | Stable machine identifier for the run |

## `laxate run docker`

Runs Benched in a Docker or Podman container. The project root is bind-mounted at the
same absolute path and used as container working directory.

```text
laxate run docker [--image IMAGE] [--engine {docker,podman}] [--network NETWORK]
                  [--init-command COMMAND] [--mount MOUNT]
                  [--container-name NAME] [--config PATH]
                  [--quick] [--machine NAME]
```

| Option                   | Configuration key       | Description                                      |
| ------------------------ | ----------------------- | ------------------------------------------------ |
| `--image IMAGE`          | `docker_image`          | Container image                                  |
| `--engine ENGINE`        | `docker_engine`         | `docker` or `podman`                             |
| `--network NETWORK`      | `docker_network`        | Container network mode                           |
| `--init-command COMMAND` | `docker_init_commands`  | Repeatable shell command executed before Benched |
| `--mount MOUNT`          | `docker_mounts`         | Repeatable bind mount in Docker `-v` format      |
| `--container-name NAME`  | `docker_container_name` | Container name                                   |
| `--config PATH`          | `benched_config`        | Path to target `pyproject.toml`                  |
| `--quick`, `-q`          | `quick`                 | Enables Benched quick mode                       |
| `--machine NAME`         | `machine`               | Stable machine identifier                        |

The default image is `python:3.11`. The default engine is `docker`, network is
`host`, and container name is `laxate-bench`. Container removal is attempted after
successful, failed, or interrupted execution.

## `laxate run hetzner`

Creates or reuses a Hetzner Cloud server, clones the benchmark repository, prepares a
Python environment, invokes `make benchmark`, and downloads the configured results
directory.

```text
laxate run hetzner [--token TOKEN] [--server-name NAME] [--server-type TYPE]
                   [--ssh-key PATH] [--ssh-key-name NAME] [--branch BRANCH]
                   [--python-version VERSION]
                   [--reuse] [--keep-server] [--push] [--github-token TOKEN]
                   [--benchmark-repo URL] [--project-repo URL]
                   [--benched-config PATH]
```

| Option                  | Configuration key    | Description                                            |
| ----------------------- | -------------------- | ------------------------------------------------------ |
| `--token TOKEN`         | —                    | Hetzner token; defaults to `HCLOUD_TOKEN`              |
| `--server-name NAME`    | `server_name_prefix` | Server name                                            |
| `--server-type TYPE`    | —                    | Hetzner server type                                    |
| `--ssh-key PATH`        | —                    | SSH private-key path                                   |
| `--ssh-key-name NAME`   | —                    | SSH public-key name registered with Hetzner            |
| `--branch BRANCH`       | `branch`             | Benchmark-suite branch                                 |
| `--python-version VER`  | `python_version`     | Python version used for the benchmark environment      |
| `--reuse`               | —                    | Reuses a matching existing server                      |
| `--keep-server`         | —                    | Retains server after command completion                |
| `--push`                | —                    | Commits and pushes collected result documents          |
| `--github-token TOKEN`  | —                    | Push token; defaults to `GITHUB_TOKEN`                 |
| `--benchmark-repo URL`  | `benchmark_repo`     | Benchmark-suite repository URL                         |
| `--project-repo URL`    | `project_repo`       | Code-under-test repository metadata                    |
| `--benched-config PATH` | `benched_config`     | Target `pyproject.toml` path within benchmark checkout |

The selected Python version creates the active virtual environment. Machine IDs use
`hetzner-{server_type}`.

## `laxate publish`

Generates a static Benched HTML report.

```text
laxate publish [--config PATH] [--output DIRECTORY]
```

| Option               | Configuration key | Description                    |
| -------------------- | ----------------- | ------------------------------ |
| `--config PATH`      | `benched_config`  | Target `pyproject.toml`        |
| `--output DIRECTORY` | `report_output`   | Static report output directory |

## `laxate preview`

Serves an existing static report on loopback and opens a browser.

```text
laxate preview [--output DIRECTORY]
```

`--output` overrides `report_output`.

## `laxate compare`

Compares two Benched run selectors. Defaults are `previous` and `latest`.

```text
laxate compare [--config PATH] [BASE] [HEAD]
```

`--config` overrides `benched_config`. `BASE` and `HEAD` accept Benched run IDs,
revisions, versions, branches, labels, `previous`, or `latest`.

## `laxate cleanup hetzner`

Deletes Hetzner servers whose names start with the configured prefix.

```text
laxate cleanup hetzner [--token TOKEN] [--prefix PREFIX]
```

`--token` defaults to `HCLOUD_TOKEN`. `--prefix` defaults to
`server_name_prefix`.

## `[tool.laxate]`

```toml
[tool.laxate]
benched_config = "pyproject.toml"
report_output = "docs/benchmarks"
results_dir = "benched-results"
benchmark_repo = "https://github.com/example/benchmarks.git"
project_repo = "https://github.com/example/subject.git"
server_name_prefix = "benchmark-runner"
branch = "main"
python_version = "3.11"
cloud_init_packages = ["git", "python3", "python3-pip", "python3-venv", "build-essential"]
machine = ""
quick = false
docker_image = "python:3.11"
docker_engine = "docker"
docker_network = "host"
docker_container_name = ""
docker_init_commands = []
docker_mounts = []
```

| Key                     | Type          | Default              |
| ----------------------- | ------------- | -------------------- |
| `benched_config`        | string        | `"pyproject.toml"`   |
| `report_output`         | string        | `"docs/benchmarks"`  |
| `results_dir`           | string        | `"results"`          |
| `benchmark_repo`        | string        | `""`                 |
| `project_repo`          | string        | `""`                 |
| `server_name_prefix`    | string        | `"benchmark-runner"` |
| `branch`                | string        | `"main"`             |
| `python_version`        | string        | `"3.11"`             |
| `cloud_init_packages`   | array[string] | system package list  |
| `machine`               | string        | `""`                 |
| `quick`                 | boolean       | `false`              |
| `docker_image`          | string        | `"python:3.11"`      |
| `docker_engine`         | string        | `"docker"`           |
| `docker_network`        | string        | `"host"`             |
| `docker_container_name` | string        | `""`                 |
| `docker_init_commands`  | array[string] | `[]`                 |
| `docker_mounts`         | array[string] | `[]`                 |
