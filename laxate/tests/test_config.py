"""Tests for laxate.config module."""

from pathlib import Path

from laxate.config import (
    DEFAULT_ASV_CONFIG,
    DEFAULT_ASV_MACHINE_JSON,
    DEFAULT_ASV_PUBLISH_CONFIG,
    DEFAULT_CLOUD_INIT_PACKAGES,
    DEFAULT_DOCKER_ENGINE,
    DEFAULT_DOCKER_IMAGE,
    DEFAULT_DOCKER_NETWORK,
    DEFAULT_PYTHON_VERSIONS,
    DEFAULT_SERVER_NAME_PREFIX,
    LaxateConfig,
    load_config,
    load_pyproject_config,
)


class TestLaxateConfig:
    def test_defaults(self):
        cfg = LaxateConfig()
        assert cfg.asv_config == DEFAULT_ASV_CONFIG
        assert cfg.asv_publish_config == DEFAULT_ASV_PUBLISH_CONFIG
        assert cfg.asv_machine_json == DEFAULT_ASV_MACHINE_JSON
        assert cfg.server_name_prefix == DEFAULT_SERVER_NAME_PREFIX
        assert cfg.python_versions == list(DEFAULT_PYTHON_VERSIONS)
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
            asv_config="my/asv.conf.json",
            benchmark_repo="https://example.com/bench.git",
            server_name_prefix="my-runner",
        )
        assert cfg.asv_config == "my/asv.conf.json"
        assert cfg.benchmark_repo == "https://example.com/bench.git"
        assert cfg.server_name_prefix == "my-runner"

    def test_resolve_path_relative(self, tmp_path):
        cfg = LaxateConfig(project_root=tmp_path)
        assert cfg.resolve_path("asv.conf.json") == tmp_path / "asv.conf.json"

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
            '[tool.laxate]\nasv_config = "bench/asv.conf.json"\nbenchmark_repo = "https://example.com/bench.git"\n'
        )
        result = load_pyproject_config(tmp_path)
        assert result["asv_config"] == "bench/asv.conf.json"
        assert result["benchmark_repo"] == "https://example.com/bench.git"


class TestLoadConfig:
    def test_defaults_no_pyproject(self, tmp_path):
        cfg = load_config(project_root=tmp_path)
        assert isinstance(cfg, LaxateConfig)
        assert cfg.asv_config == DEFAULT_ASV_CONFIG

    def test_overrides_win(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[tool.laxate]\nasv_config = "from_file.json"\n')
        cfg = load_config(project_root=tmp_path, overrides={"asv_config": "from_cli.json"})
        assert cfg.asv_config == "from_cli.json"

    def test_none_overrides_ignored(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[tool.laxate]\nasv_config = "from_file.json"\n')
        cfg = load_config(project_root=tmp_path, overrides={"asv_config": None})
        assert cfg.asv_config == "from_file.json"
