"""Tests for laxate.docker module — DockerBenchmarkRunner."""

from unittest.mock import patch

from laxate.config import LaxateConfig
from laxate.docker import DockerBenchmarkRunner


class TestDockerBenchmarkRunnerInit:
    def test_defaults(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        assert runner.image == "python:3.11"
        assert runner.engine == "docker"
        assert runner.network == "host"
        assert runner.init_commands == []
        assert runner.mounts == []
        assert runner.container_name == "laxate-bench"
        assert runner.quick is False
        assert runner.machine is None

    def test_custom_image(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, image="ubuntu:22.04")
        assert runner.image == "ubuntu:22.04"

    def test_podman_engine(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, engine="podman")
        assert runner.engine == "podman"

    def test_custom_network(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, network="bridge")
        assert runner.network == "bridge"

    def test_init_commands(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        cmds = ["apt-get update", "apt-get install -y git"]
        runner = DockerBenchmarkRunner(laxate_config=lcfg, init_commands=cmds)
        assert runner.init_commands == cmds

    def test_mounts(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, mounts=["/data:/data:ro"])
        assert runner.mounts == ["/data:/data:ro"]

    def test_container_name(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, container_name="my-bench")
        assert runner.container_name == "my-bench"

    def test_quick_and_machine(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, quick=True, machine="ci")
        assert runner.quick is True
        assert runner.machine == "ci"

    def test_reads_from_laxate_config(self, tmp_path):
        lcfg = LaxateConfig(
            project_root=tmp_path,
            docker_image="python:3.13",
            docker_engine="podman",
            docker_network="bridge",
            docker_init_commands=["pip install uv"],
            docker_mounts=["/cache:/cache"],
            docker_container_name="bench-x",
        )
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        assert runner.image == "python:3.13"
        assert runner.engine == "podman"
        assert runner.network == "bridge"
        assert runner.init_commands == ["pip install uv"]
        assert runner.mounts == ["/cache:/cache"]
        assert runner.container_name == "bench-x"

    def test_cli_overrides_config(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path, docker_image="python:3.11")
        runner = DockerBenchmarkRunner(laxate_config=lcfg, image="python:3.13")
        assert runner.image == "python:3.13"


class TestDockerBenchmarkRunnerBuildCommand:
    def test_basic_command(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        cmd = runner._build_run_command(str(tmp_path), "echo hello")

        assert cmd[0] == "docker"
        assert cmd[1] == "run"
        assert "--name" in cmd
        assert "laxate-bench" in cmd
        assert "--network" in cmd
        assert "host" in cmd
        # Check project root bind mount
        mount_str = f"{tmp_path}:{tmp_path}"
        assert mount_str in cmd
        # Working directory
        assert "-w" in cmd
        idx = cmd.index("-w")
        assert cmd[idx + 1] == str(tmp_path)
        # Image and command
        assert "python:3.11" in cmd
        assert "bash" in cmd
        assert "echo hello" in cmd

    def test_podman_engine(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, engine="podman")
        cmd = runner._build_run_command(str(tmp_path), "echo")
        assert cmd[0] == "podman"

    def test_extra_mounts(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(
            laxate_config=lcfg,
            mounts=["/data:/data:ro", "/cache:/cache"],
        )
        cmd = runner._build_run_command(str(tmp_path), "echo")
        # Should have -v for project root, plus two extra
        v_indices = [i for i, x in enumerate(cmd) if x == "-v"]
        assert len(v_indices) == 3
        assert "/data:/data:ro" in cmd
        assert "/cache:/cache" in cmd

    def test_custom_network(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg, network="none")
        cmd = runner._build_run_command(str(tmp_path), "echo")
        idx = cmd.index("--network")
        assert cmd[idx + 1] == "none"


class TestDockerBenchmarkRunnerRun:
    @patch("laxate.docker.subprocess.call")
    def test_basic_run(self, mock_call, tmp_path):
        # First call: docker run → 0, second call: docker rm → 0
        mock_call.side_effect = [0, 0]
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        result = runner.run_benchmarks()

        assert result == {"returncode": 0}
        # Should have called docker run then docker rm
        assert mock_call.call_count == 2
        run_cmd = mock_call.call_args_list[0][0][0]
        assert run_cmd[0] == "docker"
        assert run_cmd[1] == "run"
        rm_cmd = mock_call.call_args_list[1][0][0]
        assert rm_cmd[:3] == ["docker", "rm", "-f"]

    @patch("laxate.docker.subprocess.call")
    def test_run_with_init_commands(self, mock_call, tmp_path):
        mock_call.side_effect = [0, 0]
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(
            laxate_config=lcfg,
            init_commands=["pip install uv", "uv pip install -e ."],
        )
        runner.run_benchmarks()

        run_cmd = mock_call.call_args_list[0][0][0]
        shell_script = run_cmd[-1]  # last arg is the bash -c script
        assert "pip install uv" in shell_script
        assert "uv pip install -e ." in shell_script
        assert "asv" in shell_script

    @patch("laxate.docker.subprocess.call")
    def test_quick_mode(self, mock_call, tmp_path):
        mock_call.side_effect = [0, 0]
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(laxate_config=lcfg, quick=True)
        runner.run_benchmarks()

        shell_script = mock_call.call_args_list[0][0][0][-1]
        assert "--quick" in shell_script

    @patch("laxate.docker.subprocess.call")
    def test_machine_name(self, mock_call, tmp_path):
        mock_call.side_effect = [0, 0]
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(laxate_config=lcfg, machine="docker-ci")
        runner.run_benchmarks()

        shell_script = mock_call.call_args_list[0][0][0][-1]
        assert "--machine" in shell_script
        assert "docker-ci" in shell_script

    @patch("laxate.docker.subprocess.call")
    def test_nonzero_returncode(self, mock_call, tmp_path):
        mock_call.side_effect = [2, 0]
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        result = runner.run_benchmarks()
        assert result == {"returncode": 2}

    @patch("laxate.docker.subprocess.call")
    def test_container_removed_on_failure(self, mock_call, tmp_path):
        """Container is removed even when docker run fails."""
        mock_call.side_effect = [1, 0]
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        runner.run_benchmarks()

        # rm should still be called
        rm_cmd = mock_call.call_args_list[1][0][0]
        assert rm_cmd[:3] == ["docker", "rm", "-f"]

    @patch("laxate.docker.subprocess.call")
    def test_container_removed_on_exception(self, mock_call, tmp_path):
        """Container is removed even if docker run raises."""
        mock_call.side_effect = [OSError("docker not found"), 0]
        lcfg = LaxateConfig(project_root=tmp_path, asv_config="asv.conf.json")
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        try:
            runner.run_benchmarks()
        except OSError:
            pass

        # rm should still be called
        assert mock_call.call_count == 2


class TestDockerBenchmarkRunnerPush:
    def test_push_is_noop(self, tmp_path):
        lcfg = LaxateConfig(project_root=tmp_path)
        runner = DockerBenchmarkRunner(laxate_config=lcfg)
        # Should not raise
        runner.push_results_to_repo()
        runner.push_results_to_repo(github_token="tok")


class TestDockerFromPyprojectConfig:
    """Test that docker settings flow from pyproject.toml through LaxateConfig."""

    def test_docker_fields_loaded(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.laxate]\n"
            'docker_image = "ubuntu:24.04"\n'
            'docker_engine = "podman"\n'
            'docker_network = "bridge"\n'
            'docker_container_name = "my-bench"\n'
            'docker_init_commands = ["apt-get update", "apt-get install -y git"]\n'
            'docker_mounts = ["/data:/data:ro"]\n'
        )
        from laxate.config import load_config

        cfg = load_config(project_root=tmp_path)
        assert cfg.docker_image == "ubuntu:24.04"
        assert cfg.docker_engine == "podman"
        assert cfg.docker_network == "bridge"
        assert cfg.docker_container_name == "my-bench"
        assert cfg.docker_init_commands == ["apt-get update", "apt-get install -y git"]
        assert cfg.docker_mounts == ["/data:/data:ro"]

        runner = DockerBenchmarkRunner(laxate_config=cfg)
        assert runner.image == "ubuntu:24.04"
        assert runner.engine == "podman"
        assert runner.network == "bridge"
        assert runner.container_name == "my-bench"
        assert runner.init_commands == ["apt-get update", "apt-get install -y git"]
        assert runner.mounts == ["/data:/data:ro"]
