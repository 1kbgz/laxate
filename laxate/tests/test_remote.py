"""Tests for laxate.remote module."""

from unittest.mock import MagicMock, patch

from laxate.remote import RemoteExecutor


class TestRemoteExecutor:
    def test_init(self):
        r = RemoteExecutor(host="1.2.3.4", user="root", ssh_key_path="/tmp/key")
        assert r.host == "1.2.3.4"
        assert r.user == "root"
        assert r.ssh_key_path == "/tmp/key"

    def test_init_defaults(self):
        r = RemoteExecutor(host="1.2.3.4")
        assert r.user == "root"
        assert r.ssh_key_path is None

    @patch("laxate.remote.subprocess.run")
    def test_run(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        r = RemoteExecutor(host="1.2.3.4")
        _ = r.run("echo hello")
        assert mock_run.called
        args = mock_run.call_args[0][0]
        assert "ssh" in args
        assert "root@1.2.3.4" in args
        assert "echo hello" in args

    @patch("laxate.remote.subprocess.run")
    def test_run_with_key(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        r = RemoteExecutor(host="1.2.3.4", ssh_key_path="/tmp/key")
        r.run("ls")
        args = mock_run.call_args[0][0]
        assert "-i" in args
        assert "/tmp/key" in args

    @patch("laxate.remote.subprocess.run")
    def test_upload(self, mock_run):
        r = RemoteExecutor(host="1.2.3.4")
        r.upload("/local/file", "/remote/file")
        args = mock_run.call_args[0][0]
        assert "scp" in args
        assert "/local/file" in args
        assert "root@1.2.3.4:/remote/file" in args

    @patch("laxate.remote.subprocess.run")
    def test_download(self, mock_run):
        r = RemoteExecutor(host="1.2.3.4")
        r.download("/remote/dir", "/local/dir")
        args = mock_run.call_args[0][0]
        assert "scp" in args
        assert "-r" in args
        assert "root@1.2.3.4:/remote/dir" in args
        assert "/local/dir" in args
