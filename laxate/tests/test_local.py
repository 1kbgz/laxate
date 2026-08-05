"""Tests for laxate.local module — LocalBenchmarkRunner."""

from unittest.mock import patch

from laxate.config import LaxateConfig
from laxate.local import LocalBenchmarkRunner
from laxate.runner import BenchmarkConfig


class TestLocalBenchmarkRunnerInit:
    def test_defaults(self):
        runner = LocalBenchmarkRunner()
        assert runner.quick is False
        assert runner.machine is None
        assert isinstance(runner.config, BenchmarkConfig)
        assert isinstance(runner.laxate_config, LaxateConfig)

    def test_with_config(self):
        cfg = BenchmarkConfig(branch="dev")
        runner = LocalBenchmarkRunner(config=cfg, quick=True, machine="ci")
        assert runner.quick is True
        assert runner.machine == "ci"
        assert runner.config.branch == "dev"

    def test_with_laxate_config(self, tmp_path):
        lcfg = LaxateConfig(benched_config="config/pyproject.toml", project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg)
        assert runner.laxate_config.benched_config == "config/pyproject.toml"


class TestLocalBenchmarkRunnerRun:
    @patch("laxate.local.subprocess.call", return_value=0)
    def test_basic_run(self, mock_call, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg)
        result = runner.run_benchmarks()

        assert result == {"returncode": 0}
        mock_call.assert_called_once()
        cmd = mock_call.call_args[0][0]
        assert "benched" in cmd
        assert "run" in cmd
        assert "--pyproject" in cmd
        assert str(tmp_path / "pyproject.toml") in cmd

    @patch("laxate.local.subprocess.call", return_value=0)
    def test_quick_mode(self, mock_call, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg, quick=True)
        runner.run_benchmarks()

        cmd = mock_call.call_args[0][0]
        assert "--quick" in cmd

    @patch("laxate.local.subprocess.call", return_value=0)
    def test_machine_name(self, mock_call, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg, machine="github-actions")
        runner.run_benchmarks()

        cmd = mock_call.call_args[0][0]
        assert "--machine" in cmd
        assert "github-actions" in cmd

    @patch("laxate.local.subprocess.call", return_value=0)
    def test_quick_and_machine(self, mock_call, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg, quick=True, machine="my-box")
        runner.run_benchmarks()

        cmd = mock_call.call_args[0][0]
        assert "--quick" in cmd
        assert "--machine" in cmd
        assert "my-box" in cmd

    @patch("laxate.local.subprocess.call", return_value=1)
    def test_nonzero_returncode(self, mock_call, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg)
        result = runner.run_benchmarks()
        assert result == {"returncode": 1}

    @patch("laxate.local.subprocess.call", return_value=0)
    def test_custom_benched_config(self, mock_call, tmp_path):
        lcfg = LaxateConfig(benched_config="bench/pyproject.toml", project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg)
        runner.run_benchmarks()

        cmd = mock_call.call_args[0][0]
        assert str(tmp_path / "bench" / "pyproject.toml") in cmd


class TestLocalBenchmarkRunnerPush:
    def test_push_is_noop(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = LocalBenchmarkRunner(laxate_config=lcfg)
        # Should not raise
        runner.push_results_to_repo()
        runner.push_results_to_repo(github_token="tok")
