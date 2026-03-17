#!/usr/bin/env python3
"""Hetzner Cloud benchmark helpers.

These functions are called from the main ``laxate`` CLI via
``laxate run hetzner`` and ``laxate cleanup hetzner``.
"""

from __future__ import annotations

import argparse
import logging
import os

from ..config import load_config
from ..runner import BenchmarkConfig
from .runner import HetznerBenchmarkRunner
from .server import HetznerServerManager, ServerConfig

logger = logging.getLogger(__name__)


def run_benchmarks(args: argparse.Namespace) -> int:
    """Run benchmarks on a Hetzner Cloud server."""
    token = args.token or os.environ.get("HCLOUD_TOKEN")
    if not token:
        logger.error("Hetzner Cloud token required. Set HCLOUD_TOKEN or use --token")
        return 1

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
