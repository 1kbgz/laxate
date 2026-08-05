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
        from laxate.runner import BenchmarkConfig

        config = BenchmarkConfig()
        assert config.branch == "main"
        assert config.python_version == "3.11"
        assert config.benched_config == "pyproject.toml"

    def test_custom_config(self):
        from laxate.runner import BenchmarkConfig

        config = BenchmarkConfig(
            branch="develop",
            python_version="3.12",
            benchmark_repo="https://example.com/bench.git",
        )
        assert config.branch == "develop"
        assert config.python_version == "3.12"
        assert config.benchmark_repo == "https://example.com/bench.git"

    def test_from_laxate_config(self):
        from laxate.config import LaxateConfig
        from laxate.runner import BenchmarkConfig

        laxate_cfg = LaxateConfig(
            benchmark_repo="https://example.com/bench.git",
            project_repo="https://example.com/proj.git",
            benched_config="config/pyproject.toml",
        )
        bc = BenchmarkConfig.from_laxate_config(laxate_cfg)
        assert bc.benchmark_repo == "https://example.com/bench.git"
        assert bc.benched_config == "config/pyproject.toml"


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
        assert runner.config.branch == "main"

    def test_init_with_config(self):
        from laxate.hetzner.runner import HetznerBenchmarkRunner
        from laxate.runner import BenchmarkConfig

        mock_server = MagicMock()
        mock_server.public_net.ipv4.ip = "1.2.3.4"

        config = BenchmarkConfig(branch="develop", python_version="3.12")
        runner = HetznerBenchmarkRunner(
            server=mock_server,
            config=config,
            ssh_key_path="/path/to/key",
        )
        assert runner.config.branch == "develop"
        assert runner.config.python_version == "3.12"
        assert runner.ssh_key_path == "/path/to/key"

    def test_setup_installs_project_without_asv_initialization(self):
        from laxate.hetzner.runner import HetznerBenchmarkRunner
        from laxate.runner import BenchmarkConfig

        mock_server = MagicMock()
        mock_server.public_net.ipv4.ip = "1.2.3.4"
        mock_server.server_type.name = "cx23"
        config = BenchmarkConfig(branch="develop", python_version="3.12")
        runner = HetznerBenchmarkRunner(server=mock_server, config=config)
        runner._remote = MagicMock()

        runner._setup_environment()

        commands = [call.args[0] for call in runner._remote.run.call_args_list]
        assert any("make develop" in command for command in commands)
        assert any("git checkout develop" in command for command in commands)
        assert any("uv python install 3.12" in command for command in commands)
        assert not any("asv" in command.lower() for command in commands)

    def test_runs_benched_make_target_with_machine(self):
        from laxate.hetzner.runner import HetznerBenchmarkRunner
        from laxate.runner import BenchmarkConfig

        mock_server = MagicMock()
        mock_server.public_net.ipv4.ip = "1.2.3.4"
        config = BenchmarkConfig(benched_config="config/pyproject.toml")
        runner = HetznerBenchmarkRunner(server=mock_server, config=config)
        runner._machine_name = "hetzner-cx23"
        runner._remote = MagicMock()
        runner._remote.run.return_value = MagicMock(returncode=0, stdout="done", stderr="")

        assert runner._run_benched() == "done"
        command = runner._remote.run.call_args_list[0].args[0]
        assert "make benchmark BENCHED_CONFIG=config/pyproject.toml MACHINE=hetzner-cx23" in command
        assert "asv" not in command.lower()

    def test_pushes_results_to_selected_branch(self):
        from laxate.hetzner.runner import HetznerBenchmarkRunner
        from laxate.runner import BenchmarkConfig

        mock_server = MagicMock()
        mock_server.public_net.ipv4.ip = "1.2.3.4"
        config = BenchmarkConfig(branch="develop", benchmark_repo="https://example.com/benchmarks.git")
        runner = HetznerBenchmarkRunner(server=mock_server, config=config)
        runner._remote = MagicMock()

        runner.push_results_to_repo(github_token="token")

        commands = [call.args[0] for call in runner._remote.run.call_args_list]
        assert any("git push https://x-access-token:token@example.com/benchmarks.git HEAD:develop" in command for command in commands)


class TestHetznerCLI:
    def test_cli_module_importable(self):
        from laxate.hetzner import cli

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
        args.branch = "main"
        args.python_version = "3.11"
        args.reuse = False
        args.keep_server = False
        args.push = False
        args.ssh_key = None
        args.github_token = None
        args.benchmark_repo = None
        args.project_repo = None
        args.benched_config = None

        with patch.dict("os.environ", {}, clear=True):
            result = run_benchmarks(args)

        assert result == 1
