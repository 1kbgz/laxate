"""Tests for Benched report and comparison commands."""

import argparse
import sys
from unittest.mock import patch

from laxate.cli import _compare, _preview, _publish
from laxate.config import LaxateConfig


@patch("laxate.cli.subprocess.call", return_value=0)
@patch("laxate.cli.load_config")
def test_publish_builds_static_benched_report(mock_load_config, mock_call, tmp_path):
    mock_load_config.return_value = LaxateConfig(project_root=tmp_path, report_output="site")

    assert _publish(argparse.Namespace(config=None, output=None)) == 0
    assert mock_call.call_args[0][0] == [
        sys.executable,
        "-m",
        "benched",
        "report",
        "--pyproject",
        str(tmp_path / "pyproject.toml"),
        "--format",
        "html",
        "--output",
        str(tmp_path / "site"),
    ]


@patch("laxate.cli.subprocess.call", return_value=0)
@patch("laxate.cli.load_config")
def test_preview_serves_static_benched_report(mock_load_config, mock_call, tmp_path):
    mock_load_config.return_value = LaxateConfig(project_root=tmp_path, report_output="site")

    assert _preview(argparse.Namespace(output=None)) == 0
    assert mock_call.call_args[0][0] == [sys.executable, "-m", "benched", "serve", str(tmp_path / "site"), "--open"]


@patch("laxate.cli.subprocess.call", return_value=0)
@patch("laxate.cli.load_config")
def test_compare_forwards_benched_run_selectors(mock_load_config, mock_call, tmp_path):
    mock_load_config.return_value = LaxateConfig(project_root=tmp_path)

    assert _compare(argparse.Namespace(config=None, base="previous", head="latest")) == 0
    assert mock_call.call_args[0][0] == [
        sys.executable,
        "-m",
        "benched",
        "compare",
        "previous",
        "latest",
        "--pyproject",
        str(tmp_path / "pyproject.toml"),
    ]
