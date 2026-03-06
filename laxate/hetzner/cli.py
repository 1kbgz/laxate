#!/usr/bin/env python3
"""CLI for running benchmarks on Hetzner Cloud.

Usage::

    laxate hetzner run --token $HCLOUD_TOKEN
    laxate hetzner cleanup --token $HCLOUD_TOKEN
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from ..config import load_config
from .runner import BenchmarkConfig, HetznerBenchmarkRunner
from .server import HetznerServerManager, ServerConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_benchmarks(args: argparse.Namespace) -> int:
    """Run benchmarks on a Hetzner Cloud server."""
    token = args.token or os.environ.get("HCLOUD_TOKEN")
    if not token:
        logger.error("Hetzner Cloud token required. Set HCLOUD_TOKEN or use --token")
        return 1

    # Load project-level config, CLI args override
    laxate_cfg = load_config(
        overrides={
            "benchmark_repo": args.benchmark_repo,
            "project_repo": args.project_repo,
            "asv_config": args.asv_config,
            "asv_machine_json": args.asv_machine_json,
            "server_name_prefix": args.server_name,
        }
    )

    server_config = ServerConfig(
        name=args.server_name or laxate_cfg.server_name_prefix,
        server_type=args.server_type,
        ssh_key_name=args.ssh_key_name,
        cloud_init_packages=laxate_cfg.cloud_init_packages,
    )

    benchmark_config = BenchmarkConfig.from_laxate_config(
        laxate_cfg,
        branches=args.branches.split(",") if args.branches else None,
        commit_range=args.commits,
    )

    manager = HetznerServerManager(token=token, config=server_config)
    server = None

    try:
        server = manager.get_server()
        if server and not args.reuse:
            logger.info("Server %s already exists. Use --reuse to reuse it.", server.name)
            return 1
        elif not server:
            server = manager.create_server()

        runner = HetznerBenchmarkRunner(
            server=server,
            config=benchmark_config,
            ssh_key_path=args.ssh_key,
        )

        results = runner.run_benchmarks()
        logger.info("Benchmarks completed. Results: %d files", len(results.get("results_files", [])))

        if args.push:
            github_token = args.github_token or os.environ.get("GITHUB_TOKEN")
            runner.push_results_to_repo(github_token=github_token)

        return 0

    except Exception as exc:
        logger.exception("Benchmark run failed: %s", exc)
        return 1

    finally:
        if not args.keep_server and server is not None:
            logger.info("Cleaning up server…")
            try:
                manager.delete_server(server)
            except Exception as cleanup_error:
                logger.error("Failed to clean up server: %s", cleanup_error)


def cleanup_servers(args: argparse.Namespace) -> int:
    """Clean up any leftover benchmark servers."""
    token = args.token or os.environ.get("HCLOUD_TOKEN")
    if not token:
        logger.error("Hetzner Cloud token required. Set HCLOUD_TOKEN or use --token")
        return 1

    laxate_cfg = load_config()
    prefix = args.prefix or laxate_cfg.server_name_prefix

    manager = HetznerServerManager(token=token)
    servers = manager.client.servers.get_all()
    deleted = 0

    for server in servers:
        if server.name.startswith(prefix):
            logger.info("Deleting server: %s", server.name)
            manager.delete_server(server)
            deleted += 1

    logger.info("Cleaned up %d servers", deleted)
    return 0


def add_hetzner_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``hetzner`` sub-commands on an existing argparse subparsers group."""
    hetzner_parser = subparsers.add_parser("hetzner", help="Hetzner Cloud benchmark operations")
    hetzner_sub = hetzner_parser.add_subparsers(dest="hetzner_command", required=True)

    # --- run ---
    run_parser = hetzner_sub.add_parser("run", help="Run benchmarks on Hetzner Cloud")
    run_parser.add_argument("--token", help="Hetzner Cloud API token")
    run_parser.add_argument("--server-name", help="Server name (default: from config)")
    run_parser.add_argument("--server-type", default="cx23", help="Hetzner server type")
    run_parser.add_argument("--ssh-key", help="Path to SSH private key")
    run_parser.add_argument("--ssh-key-name", help="Name of SSH key in Hetzner")
    run_parser.add_argument("--branches", default="main", help="Comma-separated branches")
    run_parser.add_argument("--commits", help="Commit range (e.g. HEAD~5..HEAD)")
    run_parser.add_argument("--reuse", action="store_true", help="Reuse existing server")
    run_parser.add_argument("--keep-server", action="store_true", help="Keep server after benchmarks")
    run_parser.add_argument("--push", action="store_true", help="Push results to repository")
    run_parser.add_argument("--github-token", help="GitHub token for pushing results")
    run_parser.add_argument("--benchmark-repo", help="Override benchmark_repo URL")
    run_parser.add_argument("--project-repo", help="Override project_repo URL")
    run_parser.add_argument("--asv-config", help="Override asv config path (relative to repo)")
    run_parser.add_argument("--asv-machine-json", help="Override asv-machine.json path (relative to repo)")
    run_parser.set_defaults(func=run_benchmarks)

    # --- cleanup ---
    cleanup_parser = hetzner_sub.add_parser("cleanup", help="Clean up benchmark servers")
    cleanup_parser.add_argument("--token", help="Hetzner Cloud API token")
    cleanup_parser.add_argument("--prefix", help="Server name prefix to match for deletion")
    cleanup_parser.set_defaults(func=cleanup_servers)


def main() -> int:
    """Standalone entry point (``python -m laxate.hetzner.cli``)."""
    parser = argparse.ArgumentParser(
        description="Run benchmarks on Hetzner Cloud",
        prog="laxate hetzner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Re-use the same sub-command definitions
    run_parser = subparsers.add_parser("run", help="Run benchmarks on Hetzner Cloud")
    run_parser.add_argument("--token", help="Hetzner Cloud API token")
    run_parser.add_argument("--server-name", help="Server name (default: from config)")
    run_parser.add_argument("--server-type", default="cx23", help="Hetzner server type")
    run_parser.add_argument("--ssh-key", help="Path to SSH private key")
    run_parser.add_argument("--ssh-key-name", help="Name of SSH key in Hetzner")
    run_parser.add_argument("--branches", default="main", help="Comma-separated branches")
    run_parser.add_argument("--commits", help="Commit range (e.g. HEAD~5..HEAD)")
    run_parser.add_argument("--reuse", action="store_true", help="Reuse existing server")
    run_parser.add_argument("--keep-server", action="store_true", help="Keep server after benchmarks")
    run_parser.add_argument("--push", action="store_true", help="Push results to repository")
    run_parser.add_argument("--github-token", help="GitHub token for pushing results")
    run_parser.add_argument("--benchmark-repo", help="Override benchmark_repo URL")
    run_parser.add_argument("--project-repo", help="Override project_repo URL")
    run_parser.add_argument("--asv-config", help="Override asv config path (relative to repo)")
    run_parser.add_argument("--asv-machine-json", help="Override asv-machine.json path (relative to repo)")
    run_parser.set_defaults(func=run_benchmarks)

    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up benchmark servers")
    cleanup_parser.add_argument("--token", help="Hetzner Cloud API token")
    cleanup_parser.add_argument("--prefix", help="Server name prefix to match for deletion")
    cleanup_parser.set_defaults(func=cleanup_servers)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
