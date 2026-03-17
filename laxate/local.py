"""Local benchmark runner — executes ASV in the current environment."""

from __future__ import annotations

import logging
import subprocess

from .config import LaxateConfig, load_config
from .runner import BenchmarkConfig, BenchmarkRunner

logger = logging.getLogger(__name__)


class LocalBenchmarkRunner(BenchmarkRunner):
    """Run ASV benchmarks locally using the current Python environment."""

    def __init__(
        self,
        config: BenchmarkConfig | None = None,
        laxate_config: LaxateConfig | None = None,
        *,
        quick: bool = False,
        machine: str | None = None,
    ):
        super().__init__(config)
        self.laxate_config = laxate_config or load_config()
        self.quick = quick
        self.machine = machine

    def run_benchmarks(self) -> dict:
        """Run ASV benchmarks locally.

        Returns:
            Dictionary with ``returncode`` and ``asv_output``.
        """
        config_path = self.laxate_config.resolve_path(self.laxate_config.asv_config)

        cmd = [
            "python",
            "-m",
            "asv",
            "run",
            "--python=same",
            "--config",
            str(config_path),
            "--verbose",
            "--set-commit-hash",
            "HEAD",
        ]
        if self.quick:
            cmd.append("--quick")
        if self.machine:
            cmd.extend(["--machine", self.machine])

        logger.info("Running: %s", " ".join(cmd))
        returncode = subprocess.call(cmd)
        return {"returncode": returncode}

    def push_results_to_repo(self, github_token: str | None = None) -> None:
        """Not applicable for local runs — results are already on disk."""
        logger.info("Local runner: results are in %s", self.laxate_config.results_dir)
