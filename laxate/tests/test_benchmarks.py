"""Tests for Laxate's native pytest benchmark suite."""

from pathlib import Path

from benched.config import load_config
from benched.runner import collect_benchmarks

PROJECT_ROOT = Path(__file__).parents[2]


def test_collects_all_parameterized_benchmarks():
    config = load_config(PROJECT_ROOT / "pyproject.toml", environ={})

    exit_code, nodeids = collect_benchmarks(config)

    assert exit_code == 0
    assert len(nodeids) == 18
    assert any("test_config_operation[parse-10]" in nodeid for nodeid in nodeids)
    assert any("test_compute_operation[math-100]" in nodeid for nodeid in nodeids)
