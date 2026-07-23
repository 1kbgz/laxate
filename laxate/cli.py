#!/usr/bin/env python3
"""Main CLI entry point for laxate.

Usage::

    laxate run local                              # run benchmarks locally
    laxate run local --quick                      # quick mode
    laxate run docker --image python:3.12         # run in a Docker container
    laxate run docker --engine podman             # run via Podman
    laxate run hetzner --token $HCLOUD_TOKEN      # run on Hetzner
    laxate publish                                # generate HTML report
    laxate preview                                # preview report locally
    laxate compare [base] [head]                  # compare two commits
    laxate cleanup hetzner --token $HCLOUD_TOKEN  # cleanup servers
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

from .config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# run sub-commands
# ------------------------------------------------------------------ #


def _run_local(args: argparse.Namespace) -> int:
    """Run ASV benchmarks locally."""
    from .local import LocalBenchmarkRunner
    from .runner import BenchmarkConfig

    cfg = load_config(overrides={"asv_config": args.config, "machine": args.machine, "quick": args.quick or None})
    benchmark_config = BenchmarkConfig.from_laxate_config(cfg)

    runner = LocalBenchmarkRunner(
        config=benchmark_config,
        laxate_config=cfg,
        quick=args.quick or cfg.quick,
        machine=args.machine or cfg.machine or None,
    )
    result = runner.run_benchmarks()
    return result.get("returncode", 0)


def _run_docker(args: argparse.Namespace) -> int:
    """Run ASV benchmarks inside a Docker/Podman container."""
    from .docker import DockerBenchmarkRunner
    from .runner import BenchmarkConfig

    cfg = load_config(
        overrides={
            "asv_config": args.config,
            "docker_image": args.image,
            "docker_engine": args.engine,
            "docker_network": args.network,
            "docker_container_name": args.container_name,
        }
    )
    benchmark_config = BenchmarkConfig.from_laxate_config(cfg)

    # CLI --init-command flags append to (not replace) pyproject.toml list
    init_commands = list(cfg.docker_init_commands)
    if args.init_command:
        init_commands.extend(args.init_command)

    # CLI --mount flags append to pyproject.toml list
    mounts = list(cfg.docker_mounts)
    if args.mount:
        mounts.extend(args.mount)

    runner = DockerBenchmarkRunner(
        config=benchmark_config,
        laxate_config=cfg,
        image=args.image or cfg.docker_image,
        engine=args.engine or cfg.docker_engine,
        network=args.network or cfg.docker_network,
        init_commands=init_commands,
        mounts=mounts,
        container_name=args.container_name or cfg.docker_container_name or None,
        quick=args.quick or cfg.quick,
        machine=args.machine or cfg.machine or None,
    )
    result = runner.run_benchmarks()
    return result.get("returncode", 0)


def _run_hetzner(args: argparse.Namespace) -> int:
    """Run benchmarks on a Hetzner Cloud server."""
    from .hetzner.cli import run_benchmarks

    return run_benchmarks(args)


# ------------------------------------------------------------------ #
# top-level commands (publish, preview, compare, cleanup)
# ------------------------------------------------------------------ #


def _publish(args: argparse.Namespace) -> int:
    """Generate HTML report from ASV results."""
    cfg = load_config(overrides={"asv_publish_config": args.config})
    config_path = cfg.resolve_path(cfg.asv_publish_config)

    cmd = ["python", "-m", "asv", "publish", "--config", str(config_path)]
    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def _preview(args: argparse.Namespace) -> int:
    """Launch a local HTTP server to view ASV results."""
    cfg = load_config(overrides={"asv_publish_config": args.config})
    config_path = cfg.resolve_path(cfg.asv_publish_config)

    cmd = ["python", "-m", "asv", "preview", "--config", str(config_path)]
    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def _compare(args: argparse.Namespace) -> int:
    """Compare benchmarks between two commits."""
    cfg = load_config(overrides={"asv_config": args.config})
    config_path = cfg.resolve_path(cfg.asv_config)

    cmd = ["python", "-m", "asv", "compare", "--config", str(config_path)]
    if args.base and args.head:
        cmd.extend([args.base, args.head])
    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def _cleanup_hetzner(args: argparse.Namespace) -> int:
    """Clean up Hetzner benchmark servers."""
    from .hetzner.cli import cleanup_servers

    return cleanup_servers(args)


# ------------------------------------------------------------------ #
# CLI construction
# ------------------------------------------------------------------ #


def _add_hetzner_run_args(parser: argparse.ArgumentParser) -> None:
    """Add Hetzner-specific arguments to a run parser."""
    parser.add_argument("--token", help="Hetzner Cloud API token")
    parser.add_argument("--server-name", help="Server name (default: from config)")
    parser.add_argument("--server-type", default="cx23", help="Hetzner server type")
    parser.add_argument("--ssh-key", help="Path to SSH private key")
    parser.add_argument("--ssh-key-name", help="Name of SSH key in Hetzner")
    parser.add_argument("--branches", default="main", help="Comma-separated branches")
    parser.add_argument("--commits", help="Commit range (e.g. HEAD~5..HEAD)")
    parser.add_argument("--reuse", action="store_true", help="Reuse existing server")
    parser.add_argument("--keep-server", action="store_true", help="Keep server after benchmarks")
    parser.add_argument("--push", action="store_true", help="Push results to repository")
    parser.add_argument("--github-token", help="GitHub token for pushing results")
    parser.add_argument("--benchmark-repo", help="Override benchmark_repo URL")
    parser.add_argument("--project-repo", help="Override project_repo URL")
    parser.add_argument("--asv-config", help="Override asv config path (relative to repo)")
    parser.add_argument("--asv-machine-json", help="Override asv-machine.json path (relative to repo)")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="laxate",
        description="laxate — cloud-based ASV benchmark runner",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- run ---
    run_parser = subparsers.add_parser("run", help="Run benchmarks")
    run_sub = run_parser.add_subparsers(dest="provider", required=True)

    # run local
    local_p = run_sub.add_parser("local", help="Run benchmarks locally")
    local_p.add_argument("--config", help="Path to asv.conf.json(c)")
    local_p.add_argument("--quick", "-q", action="store_true", help="Quick mode")
    local_p.add_argument("--machine", help="Machine name")
    local_p.set_defaults(func=_run_local)

    # run docker
    docker_p = run_sub.add_parser("docker", help="Run benchmarks in a Docker/Podman container")
    docker_p.add_argument("--config", help="Path to asv.conf.json(c)")
    docker_p.add_argument("--quick", "-q", action="store_true", help="Quick mode")
    docker_p.add_argument("--machine", help="Machine name")
    docker_p.add_argument("--image", help="Container image (default: python:3.11)")
    docker_p.add_argument("--engine", choices=["docker", "podman"], help="Container engine (default: docker)")
    docker_p.add_argument("--network", help="Container network mode (default: host)")
    docker_p.add_argument("--init-command", action="append", help="Initialisation command to run before benchmarks (repeatable)")
    docker_p.add_argument("--mount", action="append", help="Extra bind mount in docker -v format (repeatable)")
    docker_p.add_argument("--container-name", help="Container name (default: laxate-bench)")
    docker_p.set_defaults(func=_run_docker)

    # run hetzner
    hetzner_p = run_sub.add_parser("hetzner", help="Run benchmarks on Hetzner Cloud")
    _add_hetzner_run_args(hetzner_p)
    hetzner_p.set_defaults(func=_run_hetzner)

    # --- publish ---
    pub_p = subparsers.add_parser("publish", help="Generate HTML report")
    pub_p.add_argument("--config", help="Path to asv.publish.conf.json(c)")
    pub_p.set_defaults(func=_publish)

    # --- preview ---
    preview_p = subparsers.add_parser("preview", help="Preview HTML report locally")
    preview_p.add_argument("--config", help="Path to asv.publish.conf.json(c)")
    preview_p.set_defaults(func=_preview)

    # --- compare ---
    cmp_p = subparsers.add_parser("compare", help="Compare two commits")
    cmp_p.add_argument("--config", help="Path to asv.conf.json(c)")
    cmp_p.add_argument("base", nargs="?", help="Base commit")
    cmp_p.add_argument("head", nargs="?", help="Head commit")
    cmp_p.set_defaults(func=_compare)

    # --- cleanup ---
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up cloud resources")
    cleanup_sub = cleanup_parser.add_subparsers(dest="cleanup_provider", required=True)

    cleanup_hetzner_p = cleanup_sub.add_parser("hetzner", help="Clean up Hetzner servers")
    cleanup_hetzner_p.add_argument("--token", help="Hetzner Cloud API token")
    cleanup_hetzner_p.add_argument("--prefix", help="Server name prefix to match for deletion")
    cleanup_hetzner_p.set_defaults(func=_cleanup_hetzner)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
