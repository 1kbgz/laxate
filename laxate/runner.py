"""Base runner and configuration for benchmark execution."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .config import DEFAULT_PYTHON_VERSIONS, LaxateConfig

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    benchmark_repo: str = ""
    project_repo: str = ""
    branches: list[str] = field(default_factory=lambda: ["main"])
    python_versions: list[str] = field(default_factory=lambda: list(DEFAULT_PYTHON_VERSIONS))
    commit_range: str | None = None  # e.g. "HEAD~5..HEAD"

    # Paths inside the benchmark repo (relative to repo root)
    asv_config: str = "asv.conf.json"
    asv_machine_json: str = "asv-machine.json"
    results_dir: str = "results"

    # Extra install groups (e.g. "develop", "hetzner")
    install_extras: list[str] = field(default_factory=lambda: ["develop"])

    @classmethod
    def from_laxate_config(cls, cfg: LaxateConfig, **overrides) -> BenchmarkConfig:
        """Build a BenchmarkConfig from the top-level LaxateConfig."""
        vals = {
            "benchmark_repo": cfg.benchmark_repo,
            "project_repo": cfg.project_repo,
            "python_versions": cfg.python_versions,
            "asv_config": cfg.asv_config,
            "asv_machine_json": cfg.asv_machine_json,
            "results_dir": cfg.results_dir,
        }
        vals.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**{k: v for k, v in vals.items() if k in cls.__dataclass_fields__})


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
