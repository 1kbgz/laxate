# laxate

Run [Benched](https://github.com/1kbgz/benched) benchmark suites in an existing local
environment, Docker or Podman container, or ephemeral Hetzner Cloud server.

[![Build Status](https://github.com/1kbgz/laxate/actions/workflows/build.yaml/badge.svg?branch=main&event=push)](https://github.com/1kbgz/laxate/actions/workflows/build.yaml)
[![codecov](https://codecov.io/gh/1kbgz/laxate/branch/main/graph/badge.svg)](https://codecov.io/gh/1kbgz/laxate)
[![License](https://img.shields.io/github/license/1kbgz/laxate)](https://github.com/1kbgz/laxate)
[![PyPI](https://img.shields.io/pypi/v/laxate.svg)](https://pypi.python.org/pypi/laxate)

Laxate owns environment and machine orchestration. Benched owns pytest-benchmark
execution, durable history, comparison, and static reports. Neither tool constructs a
matrix implicitly: select or prepare one environment, then record it.

## Install

```bash
pip install laxate
pip install "laxate[hetzner]"  # optional cloud provider
```

## Run locally

Add `[tool.benched]` configuration and pytest-benchmark tests to the target project,
then run:

```bash
laxate run local
laxate run local --quick --machine workstation
laxate compare previous latest
laxate publish
laxate preview
```

## Run in a container

The project directory is bind-mounted at the same absolute path. Initialization
commands must install the project and Benched into the container:

```bash
laxate run docker \
  --image python:3.12 \
  --init-command "pip install -e ." \
  --machine docker-3.12
```

Use `--engine podman` for Podman and repeat `--mount` for additional bind mounts.

## Run on Hetzner

Configure `benchmark_repo` in `[tool.laxate]`, export `HCLOUD_TOKEN`, and register the
SSH public key named by `--ssh-key-name`:

```bash
laxate run hetzner \
  --server-type cx23 \
  --ssh-key ~/.ssh/hetzner_key \
  --ssh-key-name benchmarks \
  --branch main \
  --python-version 3.12 \
  --push
```

The runner clones the selected benchmark-suite branch, creates its Python environment,
runs the repository's `make benchmark` target, and collects the configured results
directory.

See [CLI and configuration reference](docs/src/usage.md) for every option.

Historical ASV files are not executed. Projects migrating old results can call
`benched import-asv` once before using Laxate's Benched workflow.
