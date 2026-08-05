"""Base runner and configuration for benchmark execution."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .config import DEFAULT_PYTHON_VERSION, LaxateConfig

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    benchmark_repo: str = ""
    project_repo: str = ""
    branch: str = "main"
    python_version: str = DEFAULT_PYTHON_VERSION

    # Paths inside the benchmark repo (relative to repo root)
    benched_config: str = "pyproject.toml"
    results_dir: str = "results"

    # Extra install groups (e.g. "develop", "hetzner")
    install_extras: list[str] = field(default_factory=lambda: ["develop"])

    @classmethod
    def from_laxate_config(cls, cfg: LaxateConfig) -> BenchmarkConfig:
        """Build a BenchmarkConfig from the top-level LaxateConfig."""
        return cls(
            benchmark_repo=cfg.benchmark_repo,
            project_repo=cfg.project_repo,
            branch=cfg.branch,
            python_version=cfg.python_version,
            benched_config=cfg.benched_config,
            results_dir=cfg.results_dir,
        )


class BenchmarkRunner(ABC):
    """Abstract base class for benchmark runners.

    Subclasses implement provider-specific logic (local, Hetzner, AWS, etc.)
    while sharing the same configuration and result format.
    """

    def __init__(self, config: BenchmarkConfig | None = None):
        self.config = config or BenchmarkConfig()

    @abstractmethod
    def run_benchmarks(self) -> dict:
        """Run benchmarks and return a results dictionary."""

    @abstractmethod
    def push_results_to_repo(self, github_token: str | None = None) -> None:
        """Commit and push benchmark results back to the repository."""
