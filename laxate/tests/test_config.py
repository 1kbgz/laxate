"""Tests for laxate.config module."""

from pathlib import Path

from laxate.config import (
    DEFAULT_BENCHED_CONFIG,
    DEFAULT_CLOUD_INIT_PACKAGES,
    DEFAULT_DOCKER_ENGINE,
    DEFAULT_DOCKER_IMAGE,
    DEFAULT_DOCKER_NETWORK,
    DEFAULT_PYTHON_VERSION,
    DEFAULT_REPORT_OUTPUT,
    DEFAULT_SERVER_NAME_PREFIX,
    LaxateConfig,
    load_config,
    load_pyproject_config,
)


class TestLaxateConfig:
    def test_defaults(self):
        cfg = LaxateConfig()
        assert cfg.benched_config == DEFAULT_BENCHED_CONFIG
        assert cfg.report_output == DEFAULT_REPORT_OUTPUT
        assert cfg.server_name_prefix == DEFAULT_SERVER_NAME_PREFIX
        assert cfg.branch == "main"
        assert cfg.python_version == DEFAULT_PYTHON_VERSION
        assert cfg.cloud_init_packages == list(DEFAULT_CLOUD_INIT_PACKAGES)
        assert cfg.benchmark_repo == ""
        assert cfg.project_repo == ""
        assert cfg.results_dir == "results"
        # Local
        assert cfg.machine == ""
        assert cfg.quick is False
        # Docker
        assert cfg.docker_image == DEFAULT_DOCKER_IMAGE
        assert cfg.docker_engine == DEFAULT_DOCKER_ENGINE
        assert cfg.docker_network == DEFAULT_DOCKER_NETWORK
        assert cfg.docker_init_commands == []
        assert cfg.docker_mounts == []
        assert cfg.docker_container_name == ""

    def test_custom(self):
        cfg = LaxateConfig(
            benched_config="config/pyproject.toml",
            benchmark_repo="https://example.com/bench.git",
            server_name_prefix="my-runner",
        )
        assert cfg.benched_config == "config/pyproject.toml"
        assert cfg.benchmark_repo == "https://example.com/bench.git"
        assert cfg.server_name_prefix == "my-runner"

    def test_resolve_path_relative(self, tmp_path):
        cfg = LaxateConfig(project_root=tmp_path)
        assert cfg.resolve_path("pyproject.toml") == tmp_path / "pyproject.toml"

    def test_resolve_path_absolute(self, tmp_path):
        cfg = LaxateConfig(project_root=tmp_path)
        assert cfg.resolve_path("/etc/foo") == Path("/etc/foo")


class TestLoadPyprojectConfig:
    def test_no_pyproject(self, tmp_path):
        result = load_pyproject_config(tmp_path)
        assert result == {}

    def test_pyproject_without_tool_laxate(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "foo"\n')
        result = load_pyproject_config(tmp_path)
        assert result == {}

    def test_pyproject_with_tool_laxate(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.laxate]\nbenched_config = "bench/pyproject.toml"\nbenchmark_repo = "https://example.com/bench.git"\n'
        )
        result = load_pyproject_config(tmp_path)
        assert result["benched_config"] == "bench/pyproject.toml"
        assert result["benchmark_repo"] == "https://example.com/bench.git"


class TestLoadConfig:
    def test_defaults_no_pyproject(self, tmp_path):
        cfg = load_config(project_root=tmp_path)
        assert isinstance(cfg, LaxateConfig)
        assert cfg.benched_config == DEFAULT_BENCHED_CONFIG

    def test_overrides_win(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[tool.laxate]\nbenched_config = "from_file.toml"\n')
        cfg = load_config(project_root=tmp_path, overrides={"benched_config": "from_cli.toml"})
        assert cfg.benched_config == "from_cli.toml"

    def test_none_overrides_ignored(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[tool.laxate]\nbenched_config = "from_file.toml"\n')
        cfg = load_config(project_root=tmp_path, overrides={"benched_config": None})
        assert cfg.benched_config == "from_file.toml"
