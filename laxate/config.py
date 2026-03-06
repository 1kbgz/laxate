"""Configuration loading for laxate.

Configuration is read from `[tool.laxate]` in pyproject.toml, with CLI
arguments taking precedence over file-based config.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_ASV_CONFIG = "asv.conf.json"
DEFAULT_ASV_PUBLISH_CONFIG = "asv.publish.conf.json"
DEFAULT_ASV_MACHINE_JSON = "asv-machine.json"
DEFAULT_SERVER_NAME_PREFIX = "benchmark-runner"
DEFAULT_PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]
DEFAULT_CLOUD_INIT_PACKAGES = [
    "git",
    "python3",
    "python3-pip",
    "python3-venv",
    "build-essential",
]


@dataclass
class LaxateConfig:
    """Top-level configuration for laxate."""

    # Paths (relative to project root or absolute)
    asv_config: str = DEFAULT_ASV_CONFIG
    asv_publish_config: str = DEFAULT_ASV_PUBLISH_CONFIG
    asv_machine_json: str = DEFAULT_ASV_MACHINE_JSON

    # Repository URLs
    benchmark_repo: str = ""
    project_repo: str = ""

    # Server / runner
    server_name_prefix: str = DEFAULT_SERVER_NAME_PREFIX
    python_versions: list[str] = field(default_factory=lambda: list(DEFAULT_PYTHON_VERSIONS))
    cloud_init_packages: list[str] = field(default_factory=lambda: list(DEFAULT_CLOUD_INIT_PACKAGES))

    # Results
    results_dir: str = "results"

    # Project root (where pyproject.toml lives)
    project_root: Path = field(default_factory=lambda: Path.cwd())

    def resolve_path(self, path: str) -> Path:
        """Resolve a path relative to the project root."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.project_root / p


def load_pyproject_config(project_root: Path | None = None) -> dict[str, Any]:
    """Load the `[tool.laxate]` section from pyproject.toml.

    Args:
        project_root: Directory containing pyproject.toml. Defaults to cwd.

    Returns:
        Dictionary of config values, empty if not found.
    """
    root = project_root or Path.cwd()
    pyproject_path = root / "pyproject.toml"

    if not pyproject_path.exists():
        logger.debug("No pyproject.toml found at %s", pyproject_path)
        return {}

    try:
        # Python 3.11+ has tomllib in stdlib
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        return data.get("tool", {}).get("laxate", {})
    except Exception:
        logger.debug("Failed to parse pyproject.toml", exc_info=True)
        return {}


def load_config(
    project_root: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> LaxateConfig:
    """Build a LaxateConfig from pyproject.toml + optional overrides.

    CLI arguments should be passed as *overrides*; they take precedence
    over values read from pyproject.toml.
    """
    root = project_root or Path.cwd()
    file_cfg = load_pyproject_config(root)

    # Merge: file_cfg is base, overrides win
    merged: dict[str, Any] = {**file_cfg}
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                merged[k] = v

    merged["project_root"] = root
    # Convert project_root from str if needed
    if isinstance(merged.get("project_root"), str):
        merged["project_root"] = Path(merged["project_root"])

    return LaxateConfig(**{k: v for k, v in merged.items() if k in LaxateConfig.__dataclass_fields__})


def load_asv_config(config_path: Path) -> dict[str, Any]:
    """Load and parse an ASV config file (JSON or JSONC).

    Strips single-line ``//`` comments before parsing so that
    ``asv.conf.jsonc`` files are supported.
    """
    text = config_path.read_text()

    # Strip single-line // comments (not inside strings — good-enough heuristic)
    import re

    text = re.sub(r"(?m)^\s*//.*$", "", text)
    # Also strip trailing // comments
    text = re.sub(r"//[^\n]*", "", text)

    return json.loads(text)
