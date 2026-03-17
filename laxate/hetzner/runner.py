"""Hetzner Cloud benchmark runner."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hcloud.servers import BoundServer

from ..remote import RemoteExecutor
from ..runner import BenchmarkConfig, BenchmarkRunner

logger = logging.getLogger(__name__)


class HetznerBenchmarkRunner(BenchmarkRunner):
    """Run ASV benchmarks on a Hetzner Cloud server.

    Handles:
    1. SSH connection to the server
    2. Setting up the benchmark environment
    3. Running ASV benchmarks
    4. Collecting and returning results
    """

    def __init__(
        self,
        server: BoundServer,
        config: BenchmarkConfig | None = None,
        ssh_key_path: str | None = None,
    ):
        super().__init__(config)
        self.server = server
        self.ssh_key_path = ssh_key_path
        self.server_ip = server.public_net.ipv4.ip
        self._remote = RemoteExecutor(
            host=self.server_ip,
            user="root",
            ssh_key_path=self.ssh_key_path,
        )
        self._machine_name: str | None = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run_benchmarks(self) -> dict:
        """Run the full benchmark suite on the remote server.

        Returns:
            Dictionary containing benchmark results and metadata.
        """
        logger.info("Starting benchmarks on %s", self.server_ip)
        self._setup_environment()
        asv_output = self._run_asv()
        return self._collect_results(asv_output)

    def push_results_to_repo(self, github_token: str | None = None) -> None:
        """Commit and push benchmark results back to the repository."""
        logger.info("Pushing results to repository…")

        repo_dir = "/root/benchmarks"
        results_path = f"{repo_dir}/{self.config.results_dir}"

        list_result = self._remote.run(
            f"find {results_path} -name '*.json' | head -50",
            check=False,
        )
        logger.debug("Result files on server:\n%s", list_result.stdout)

        commands = [
            f"cd {repo_dir} && git config user.email 'benchmark-bot@example.com'",
            f"cd {repo_dir} && git config user.name 'Benchmark Bot'",
            f"cd {repo_dir} && git add -f {self.config.results_dir}/",
            f"cd {repo_dir} && git status --short",
            f"cd {repo_dir} && git commit -m 'Add benchmark results' || true",
        ]

        if github_token:
            push_url = self.config.benchmark_repo.replace("https://", f"https://x-access-token:{github_token}@")
            commands.append(f"cd {repo_dir} && git push {push_url} HEAD:main")
        else:
            commands.append(f"cd {repo_dir} && git push origin main")

        for cmd in commands:
            result = self._remote.run(cmd, check=False)
            if "git status" in cmd:
                logger.info("Git status:\n%s", result.stdout)

        logger.info("Results pushed successfully")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _setup_environment(self) -> None:
        """Set up the benchmark environment on the remote server."""
        logger.info("Setting up benchmark environment…")

        self._remote.wait_for_ssh()

        server_type = self.server.server_type.name
        self._machine_name = f"hetzner-{server_type}"

        python_install = " ".join(self.config.python_versions)

        commands = [
            "cloud-init status --wait || true",
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "export PATH=$HOME/.local/bin:$PATH",
            f"$HOME/.local/bin/uv python install {python_install}",
            f"git clone {self.config.benchmark_repo} /root/benchmarks",
            f"cd /root/benchmarks && git checkout {self.config.branches[0]}",
            f"cd /root/benchmarks && $HOME/.local/bin/uv venv .venv --python {self.config.python_versions[0]}",
            "cd /root/benchmarks && PATH=$HOME/.local/bin:$PATH make develop",
            f"cp /root/benchmarks/{self.config.asv_machine_json} ~/.asv-machine.json",
            "cd /root/benchmarks && . .venv/bin/activate && make benchmark-init",
        ]

        for cmd in commands:
            self._remote.run(cmd)

        logger.info("Environment setup complete (machine: %s)", self._machine_name)

    def _run_asv(self) -> str:
        """Run ASV benchmarks and return combined stdout+stderr."""
        logger.info("Running ASV benchmarks…")

        machine_arg = f"MACHINE={self._machine_name}" if self._machine_name else ""

        # Use Makefile target which handles --python=same and --set-commit-hash
        cmd = f"cd /root/benchmarks && . .venv/bin/activate && make benchmark {machine_arg}"
        result = self._remote.run(cmd, check=False)

        asv_output = result.stdout + result.stderr

        if result.returncode != 0:
            logger.warning("ASV exited with code %d", result.returncode)
        logger.info("ASV output (last 2000 chars):\n%s", asv_output[-2000:])

        if self._machine_name:
            results_path = f"/root/benchmarks/{self.config.results_dir}/{self._machine_name}/"
            list_result = self._remote.run(
                f"ls -la {results_path} || echo 'No results directory'",
                check=False,
            )
            logger.info("Machine results directory contents:\n%s", list_result.stdout)

        return asv_output

    def _collect_results(self, asv_output: str) -> dict:
        """Download and return benchmark results from the remote server."""
        logger.info("Collecting benchmark results…")

        results_path = f"/root/benchmarks/{self.config.results_dir}/"

        check_result = self._remote.run(
            f"ls -la {results_path} 2>&1 || echo 'NO_RESULTS'",
            check=False,
        )
        if "NO_RESULTS" in check_result.stdout or "No such file" in check_result.stdout:
            logger.warning("No results directory found — ASV may have failed")
            return {
                "server": self._server_meta(),
                "asv_output": asv_output,
                "results_files": [],
                "error": "No results directory found",
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            local_results = Path(tmpdir) / "results"
            local_results.mkdir()

            self._remote.download(results_path, str(local_results))

            results = {
                "server": self._server_meta(),
                "asv_output": asv_output,
                "results_files": [],
            }

            for result_file in local_results.rglob("*.json"):
                results["results_files"].append(
                    {
                        "name": result_file.name,
                        "content": result_file.read_text(),
                    }
                )

            return results

    def _server_meta(self) -> dict:
        return {
            "name": self.server.name,
            "id": self.server.id,
            "type": self.server.server_type.name,
            "ip": self.server_ip,
        }
