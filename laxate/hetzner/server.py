"""Hetzner Cloud server management for benchmarks."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hcloud.servers import BoundServer

from ..config import DEFAULT_CLOUD_INIT_PACKAGES

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Configuration for a Hetzner benchmark server."""

    name: str = "benchmark-runner"
    server_type: str = "cx23"  # 2 vCPU, 4GB RAM
    image: str = "ubuntu-24.04"
    location: str = "nbg1"  # Nuremberg, Germany
    ssh_key_name: str | None = None
    cloud_init_packages: list[str] = field(default_factory=lambda: list(DEFAULT_CLOUD_INIT_PACKAGES))


class HetznerServerManager:
    """Manages Hetzner Cloud servers for running benchmarks.

    Usage::

        manager = HetznerServerManager(token="your-hcloud-token")
        server = manager.create_server()
        # … run benchmarks …
        manager.delete_server(server)
    """

    def __init__(self, token: str, config: ServerConfig | None = None):
        from hcloud import Client

        self.client = Client(
            token=token,
            application_name="laxate",
            application_version="1.0.0",
        )
        self.config = config or ServerConfig()

    def create_server(self, wait_for_ready: bool = True) -> BoundServer:
        """Create a new Hetzner server for benchmarking."""
        from hcloud.images import Image
        from hcloud.locations import Location
        from hcloud.server_types import ServerType

        logger.info("Creating Hetzner server: %s", self.config.name)

        ssh_keys = []
        if self.config.ssh_key_name:
            ssh_key = self.client.ssh_keys.get_by_name(self.config.ssh_key_name)
            if ssh_key:
                ssh_keys.append(ssh_key)

        response = self.client.servers.create(
            name=self.config.name,
            server_type=ServerType(name=self.config.server_type),
            image=Image(name=self.config.image),
            location=Location(name=self.config.location),
            ssh_keys=ssh_keys if ssh_keys else None,
            user_data=self._get_cloud_init_script(),
        )

        server = response.server
        logger.info("Server created: %s (ID: %s)", server.name, server.id)

        if wait_for_ready:
            self._wait_for_server_ready(server)

        return server

    def delete_server(self, server: BoundServer) -> None:
        """Delete a Hetzner server."""
        logger.info("Deleting server: %s (ID: %s)", server.name, server.id)
        server.delete()
        logger.info("Server deleted successfully")

    def get_server(self, name: str | None = None) -> BoundServer | None:
        """Get an existing server by name."""
        name = name or self.config.name
        return self.client.servers.get_by_name(name)

    def _wait_for_server_ready(self, server: BoundServer, timeout: int = 300) -> None:
        """Wait for the server to be running."""
        logger.info("Waiting for server to be ready…")

        start_time = time.time()
        while time.time() - start_time < timeout:
            server = self.client.servers.get_by_id(server.id)

            if server.status == "running":
                logger.info("Server is running at %s", server.public_net.ipv4.ip)
                time.sleep(30)
                return

            logger.debug("Server status: %s", server.status)
            time.sleep(10)

        raise TimeoutError(f"Server did not become ready within {timeout} seconds")

    def _get_cloud_init_script(self) -> str:
        """Build a cloud-init script from configured packages."""
        packages = "\n".join(f"  - {p}" for p in self.config.cloud_init_packages)
        return f"""#cloud-config
package_update: true
package_upgrade: true

packages:
{packages}

runcmd:
  - python3 -m pip install --upgrade pip
  - python3 -m pip install uv
"""
