#!/usr/bin/env python3
"""Main CLI entry point for laxate.

Usage::

    laxate hetzner run --token $HCLOUD_TOKEN
    laxate hetzner cleanup --token $HCLOUD_TOKEN
    laxate benchmark run --config asv.conf.json
    laxate benchmark publish --config asv.publish.conf.json
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
# benchmark sub-commands (thin wrappers around asv)
# ------------------------------------------------------------------ #


def _benchmark_run(args: argparse.Namespace) -> int:
    """Run ASV benchmarks locally."""
    cfg = load_config(overrides={"asv_config": args.config})
    config_path = cfg.resolve_path(cfg.asv_config)

    cmd = ["python", "-m", "asv", "run", "--config", str(config_path), "--verbose"]
    if args.quick:
        cmd.append("--quick")
    if args.machine:
        cmd.extend(["--machine", args.machine])
    if args.python:
        cmd.extend(["--python", args.python])
    if args.commits:
        cmd.extend(args.commits.split())
    else:
        cmd.append("HEAD^!")

    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def _benchmark_publish(args: argparse.Namespace) -> int:
    """Generate HTML report from ASV results."""
    cfg = load_config(overrides={"asv_publish_config": args.config})
    config_path = cfg.resolve_path(cfg.asv_publish_config)

    cmd = ["python", "-m", "asv", "publish", "--config", str(config_path)]
    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def _benchmark_preview(args: argparse.Namespace) -> int:
    """Launch a local HTTP server to view ASV results."""
    cfg = load_config(overrides={"asv_publish_config": args.config})
    config_path = cfg.resolve_path(cfg.asv_publish_config)

    cmd = ["python", "-m", "asv", "preview", "--config", str(config_path)]
    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def _benchmark_compare(args: argparse.Namespace) -> int:
    """Compare benchmarks between two commits."""
    cfg = load_config(overrides={"asv_config": args.config})
    config_path = cfg.resolve_path(cfg.asv_config)

    cmd = ["python", "-m", "asv", "compare", "--config", str(config_path)]
    if args.base and args.head:
        cmd.extend([args.base, args.head])
    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


# ------------------------------------------------------------------ #
# top-level CLI
# ------------------------------------------------------------------ #


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="laxate",
        description="laxate — cloud-based ASV benchmark runner",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- hetzner ---
    from .hetzner.cli import add_hetzner_subparser

    add_hetzner_subparser(subparsers)

    # --- benchmark ---
    bench_parser = subparsers.add_parser("benchmark", help="Run ASV benchmarks locally")
    bench_sub = bench_parser.add_subparsers(dest="bench_command", required=True)

    run_p = bench_sub.add_parser("run", help="Run benchmarks")
    run_p.add_argument("--config", help="Path to asv.conf.json(c)")
    run_p.add_argument("--quick", "-q", action="store_true", help="Quick mode")
    run_p.add_argument("--machine", help="Machine name")
    run_p.add_argument("--python", help="Python executable (e.g. 'same')")
    run_p.add_argument("--commits", help="Commit spec (default: HEAD^!)")
    run_p.set_defaults(func=_benchmark_run)

    pub_p = bench_sub.add_parser("publish", help="Generate HTML report")
    pub_p.add_argument("--config", help="Path to asv.publish.conf.json(c)")
    pub_p.set_defaults(func=_benchmark_publish)

    preview_p = bench_sub.add_parser("preview", help="Preview HTML report locally")
    preview_p.add_argument("--config", help="Path to asv.publish.conf.json(c)")
    preview_p.set_defaults(func=_benchmark_preview)

    cmp_p = bench_sub.add_parser("compare", help="Compare two commits")
    cmp_p.add_argument("--config", help="Path to asv.conf.json(c)")
    cmp_p.add_argument("base", nargs="?", help="Base commit")
    cmp_p.add_argument("head", nargs="?", help="Head commit")
    cmp_p.set_defaults(func=_benchmark_compare)

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
