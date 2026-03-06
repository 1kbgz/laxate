"""Tests for laxate.hetzner module."""

import importlib.util
from unittest.mock import MagicMock, patch

import pytest

HAS_HCLOUD = importlib.util.find_spec("hcloud") is not None


class TestServerConfig:
    def test_default_config(self):
        from laxate.hetzner.server import ServerConfig

        config = ServerConfig()
        assert config.name == "benchmark-runner"
        assert config.server_type == "cx23"
        assert config.image == "ubuntu-24.04"
        assert config.location == "nbg1"
        assert config.ssh_key_name is None
        assert len(config.cloud_init_packages) > 0

    def test_custom_config(self):
        from laxate.hetzner.server import ServerConfig

        config = ServerConfig(
            name="custom-runner",
            server_type="cpx51",
            image="ubuntu-22.04",
            location="nbg1",
            ssh_key_name="my-key",
        )
        assert config.name == "custom-runner"
        assert config.server_type == "cpx51"


class TestBenchmarkConfig:
    def test_default_config(self):
        from laxate.hetzner.runner import BenchmarkConfig

        config = BenchmarkConfig()
        assert config.branches == ["main"]
        assert config.commit_range is None
        assert config.asv_config == "asv.conf.json"
        assert config.asv_machine_json == "asv-machine.json"

    def test_custom_config(self):
        from laxate.hetzner.runner import BenchmarkConfig

        config = BenchmarkConfig(
            branches=["main", "develop"],
            commit_range="HEAD~5..HEAD",
            benchmark_repo="https://example.com/bench.git",
        )
        assert config.branches == ["main", "develop"]
        assert config.commit_range == "HEAD~5..HEAD"
        assert config.benchmark_repo == "https://example.com/bench.git"

    def test_from_laxate_config(self):
        from laxate.config import LaxateConfig
        from laxate.hetzner.runner import BenchmarkConfig

        laxate_cfg = LaxateConfig(
            benchmark_repo="https://example.com/bench.git",
            project_repo="https://example.com/proj.git",
            asv_config="my/asv.conf.json",
        )
        bc = BenchmarkConfig.from_laxate_config(laxate_cfg, commit_range="HEAD^!")
        assert bc.benchmark_repo == "https://example.com/bench.git"
        assert bc.asv_config == "my/asv.conf.json"
        assert bc.commit_range == "HEAD^!"


@pytest.mark.skipif(not HAS_HCLOUD, reason="hcloud not installed")
class TestHetznerServerManager:
    @patch("hcloud.Client")
    def test_init(self, mock_client_class):
        from laxate.hetzner.server import HetznerServerManager

        manager = HetznerServerManager(token="test-token")
        mock_client_class.assert_called_once_with(
            token="test-token",
            application_name="laxate",
            application_version="1.0.0",
        )
        assert manager.config.name == "benchmark-runner"

    @patch("hcloud.Client")
    def test_get_cloud_init_script(self, mock_client_class):
        from laxate.hetzner.server import HetznerServerManager

        manager = HetznerServerManager(token="test-token")
        script = manager._get_cloud_init_script()
        assert "#cloud-config" in script
        assert "package_update: true" in script
        assert "git" in script
        assert "python3" in script


class TestHetznerBenchmarkRunner:
    def test_init(self):
        from laxate.hetzner.runner import HetznerBenchmarkRunner

        mock_server = MagicMock()
        mock_server.public_net.ipv4.ip = "1.2.3.4"

        runner = HetznerBenchmarkRunner(server=mock_server)
        assert runner.server == mock_server
        assert runner.server_ip == "1.2.3.4"
        assert runner.config.branches == ["main"]

    def test_init_with_config(self):
        from laxate.hetzner.runner import BenchmarkConfig, HetznerBenchmarkRunner

        mock_server = MagicMock()
        mock_server.public_net.ipv4.ip = "1.2.3.4"

        config = BenchmarkConfig(commit_range="HEAD~3..HEAD")
        runner = HetznerBenchmarkRunner(
            server=mock_server,
            config=config,
            ssh_key_path="/path/to/key",
        )
        assert runner.config.commit_range == "HEAD~3..HEAD"
        assert runner.ssh_key_path == "/path/to/key"


class TestHetznerCLI:
    def test_cli_module_importable(self):
        from laxate.hetzner import cli

        assert hasattr(cli, "main")
        assert hasattr(cli, "run_benchmarks")
        assert hasattr(cli, "cleanup_servers")

    @patch("laxate.hetzner.cli.HetznerServerManager")
    @patch("laxate.hetzner.cli.HetznerBenchmarkRunner")
    def test_run_benchmarks_no_token(self, mock_runner, mock_manager):
        from laxate.hetzner.cli import run_benchmarks

        args = MagicMock()
        args.token = None
        args.server_name = "test"
        args.server_type = "cx23"
        args.ssh_key_name = None
        args.branches = "main"
        args.commits = None
        args.reuse = False
        args.keep_server = False
        args.push = False
        args.ssh_key = None
        args.github_token = None
        args.benchmark_repo = None
        args.project_repo = None
        args.asv_config = None
        args.asv_machine_json = None

        with patch.dict("os.environ", {}, clear=True):
            result = run_benchmarks(args)

        assert result == 1
