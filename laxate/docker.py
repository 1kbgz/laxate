"""Docker/Podman benchmark runner — executes ASV inside a container."""

from __future__ import annotations

import logging
import shlex
import subprocess

from .config import (
    DEFAULT_DOCKER_ENGINE,
    DEFAULT_DOCKER_IMAGE,
    DEFAULT_DOCKER_NETWORK,
    LaxateConfig,
    load_config,
)
from .runner import BenchmarkConfig, BenchmarkRunner

logger = logging.getLogger(__name__)


class DockerBenchmarkRunner(BenchmarkRunner):
    """Run ASV benchmarks inside a Docker or Podman container.

    The runner:
    1. Starts a container from the chosen image
    2. Mounts the project directory into the container
    3. Runs optional initialisation commands
    4. Executes ASV benchmarks
    5. Results are written back via the bind mount
    """

    def __init__(
        self,
        config: BenchmarkConfig | None = None,
        laxate_config: LaxateConfig | None = None,
        *,
        image: str | None = None,
        engine: str | None = None,
        network: str | None = None,
        init_commands: list[str] | None = None,
        mounts: list[str] | None = None,
        container_name: str | None = None,
        quick: bool = False,
        machine: str | None = None,
    ):
        super().__init__(config)
        self.laxate_config = laxate_config or load_config()

        self.image = image or self.laxate_config.docker_image or DEFAULT_DOCKER_IMAGE
        self.engine = engine or self.laxate_config.docker_engine or DEFAULT_DOCKER_ENGINE
        self.network = network or self.laxate_config.docker_network or DEFAULT_DOCKER_NETWORK
        self.init_commands = init_commands if init_commands is not None else list(self.laxate_config.docker_init_commands)
        self.mounts = mounts if mounts is not None else list(self.laxate_config.docker_mounts)
        self.container_name = container_name or self.laxate_config.docker_container_name or "laxate-bench"

        self.quick = quick
        self.machine = machine

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run_benchmarks(self) -> dict:
        """Run ASV benchmarks inside a container.

        Returns:
            Dictionary with ``returncode``.
        """
        project_root = str(self.laxate_config.project_root)
        config_path = self.laxate_config.resolve_path(self.laxate_config.asv_config)

        # Build the in-container benchmark command
        asv_cmd_parts = [
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
            asv_cmd_parts.append("--quick")
        if self.machine:
            asv_cmd_parts.extend(["--machine", self.machine])

        # Combine init commands + benchmark command into a single shell script
        script_parts: list[str] = []
        script_parts.append("set -e")
        for cmd in self.init_commands:
            script_parts.append(cmd)
        script_parts.append(shlex.join(asv_cmd_parts))
        shell_script = " && ".join(script_parts)

        # Assemble docker/podman run command
        cmd = self._build_run_command(project_root, shell_script)

        logger.info("Running: %s", " ".join(cmd))
        try:
            returncode = subprocess.call(cmd)
        finally:
            self._remove_container()

        return {"returncode": returncode}

    def push_results_to_repo(self, github_token: str | None = None) -> None:
        """Not applicable for docker runs — results are on host via bind mount."""
        logger.info("Docker runner: results are available on the host via bind mount")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_run_command(self, project_root: str, shell_script: str) -> list[str]:
        """Build the ``docker run`` / ``podman run`` command list."""
        cmd: list[str] = [
            self.engine,
            "run",
            "--name",
            self.container_name,
            "--network",
            self.network,
            "-v",
            f"{project_root}:{project_root}",
            "-w",
            project_root,
        ]

        for mount in self.mounts:
            cmd.extend(["-v", mount])

        cmd.extend([self.image, "bash", "-c", shell_script])
        return cmd

    def _remove_container(self) -> None:
        """Remove the container (ignore errors if it doesn't exist)."""
        subprocess.call(
            [self.engine, "rm", "-f", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
