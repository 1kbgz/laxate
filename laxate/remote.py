"""SSH and SCP utilities for remote benchmark execution."""

from __future__ import annotations

import logging
import subprocess
import time

logger = logging.getLogger(__name__)


class RemoteExecutor:
    """Execute commands and transfer files on a remote host over SSH."""

    def __init__(self, host: str, user: str = "root", ssh_key_path: str | None = None):
        self.host = host
        self.user = user
        self.ssh_key_path = ssh_key_path

    # --------------------------------------------------------------------- #
    # SSH
    # --------------------------------------------------------------------- #

    def run(self, command: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run *command* on the remote host via SSH."""
        ssh_args = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]

        if self.ssh_key_path:
            ssh_args.extend(["-i", self.ssh_key_path])

        ssh_args.extend([f"{self.user}@{self.host}", command])

        logger.debug("Running SSH command: %s", command)
        result = subprocess.run(ssh_args, capture_output=True, text=True, check=check)

        if result.stdout:
            logger.debug("stdout: %s", result.stdout)
        if result.stderr:
            logger.debug("stderr: %s", result.stderr)

        return result

    # --------------------------------------------------------------------- #
    # SCP
    # --------------------------------------------------------------------- #

    def upload(self, local_path: str, remote_path: str) -> None:
        """Copy a local file to the remote host."""
        scp_args = [
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]

        if self.ssh_key_path:
            scp_args.extend(["-i", self.ssh_key_path])

        scp_args.extend([local_path, f"{self.user}@{self.host}:{remote_path}"])
        subprocess.run(scp_args, check=True)

    def download(self, remote_path: str, local_path: str) -> None:
        """Copy a file (or directory tree) from the remote host."""
        scp_args = [
            "scp",
            "-r",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]

        if self.ssh_key_path:
            scp_args.extend(["-i", self.ssh_key_path])

        scp_args.extend([f"{self.user}@{self.host}:{remote_path}", local_path])
        subprocess.run(scp_args, check=True)

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #

    def wait_for_ssh(self, timeout: int = 300, interval: int = 15) -> None:
        """Block until the remote host accepts SSH connections."""
        logger.info("Waiting for SSH on %s …", self.host)
        start = time.time()
        last_error: str | None = None

        while time.time() - start < timeout:
            try:
                result = self.run("echo 'SSH ready'", check=False)
                if result.returncode == 0:
                    logger.info("SSH connection established")
                    return
                last_error = f"exit code {result.returncode}: {result.stderr}"
            except Exception as exc:
                last_error = str(exc)

            elapsed = int(time.time() - start)
            logger.info("SSH not ready after %ds, retrying… (last error: %s)", elapsed, last_error)
            time.sleep(interval)

        raise TimeoutError(f"SSH not available after {timeout}s. Last error: {last_error}")
