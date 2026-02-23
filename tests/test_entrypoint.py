"""Tests for entrypoint: get_input, get_registry_host, and main (login + push)."""
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

# Import after potential env setup so we can patch before import if needed
import entrypoint as ep


class TestGetInput:
    """Tests for get_input()."""

    def test_reads_input_from_env_uppercase_dashes_to_underscores(self):
        with patch.dict(os.environ, {"INPUT_REGISTRY_URL": "oci://registry.example.com"}, clear=False):
            assert ep.get_input("registry-url") == "oci://registry.example.com"

    def test_returns_default_when_env_missing(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in ("INPUT_CHART_FOLDER", "INPUT_chart_folder"):
                if key in os.environ:
                    del os.environ[key]
            assert ep.get_input("chart-folder", "chart") == "chart"

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"INPUT_ACCESS_TOKEN": "  token123  "}, clear=False):
            assert ep.get_input("access-token") == "token123"


class TestGetRegistryHost:
    """Tests for get_registry_host()."""

    def test_oci_url_returns_netloc(self):
        assert ep.get_registry_host("oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com") == "123456789123.dkr.ecr.eu-west-1.amazonaws.com"

    def test_oci_url_with_path_returns_host_only(self):
        assert ep.get_registry_host("oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com/repo") == "123456789123.dkr.ecr.eu-west-1.amazonaws.com"

    def test_https_url_returns_netloc(self):
        assert ep.get_registry_host("https://h.cfcr.io/user_or_org/reponame") == "h.cfcr.io"

    def test_invalid_url_exits_with_1(self):
        with pytest.raises(SystemExit):
            ep.get_registry_host("not-a-valid-url-without-netloc")


class TestMainLoginAndPush:
    """Tests for main(): login and push command construction and error handling."""

    @pytest.fixture(autouse=True)
    def setup_env_and_mocks(self, tmp_path):
        self.workspace = tmp_path
        self.chart_dir = tmp_path / "chart"
        self.chart_dir.mkdir()
        self.github_output = tmp_path / "github_output"
        yield
        # cleanup: restore modules if we patched

    def _env_ecr(self, **overrides):
        base = {
            "INPUT_REGISTRY_URL": "oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com",
            "INPUT_ACCESS_TOKEN": "ecr-token-123",
            "INPUT_CHART_FOLDER": "chart",
            "INPUT_FORCE": "false",
            "GITHUB_WORKSPACE": str(self.workspace),
        }
        base.update(overrides)
        return base

    def _env_classic(self, **overrides):
        base = {
            "INPUT_REGISTRY_URL": "https://h.cfcr.io/user/repo",
            "INPUT_USERNAME": "myuser",
            "INPUT_PASSWORD": "mypass",
            "INPUT_CHART_FOLDER": "chart",
            "INPUT_FORCE": "false",
            "GITHUB_WORKSPACE": str(self.workspace),
        }
        base.update(overrides)
        return base

    @patch("entrypoint.subprocess.run")
    def test_ecr_mode_calls_login_with_aws_and_token_then_push(self, run_mock):
        run_mock.return_value = MagicMock(returncode=0)
        with patch.dict(os.environ, self._env_ecr(), clear=False):
            ep.main()
        assert run_mock.call_count == 2
        login_args = run_mock.call_args_list[0]
        assert login_args[0][0] == [
            "helm",
            "registry",
            "login",
            "123456789123.dkr.ecr.eu-west-1.amazonaws.com",
            "--username",
            "AWS",
            "--password-stdin",
        ]
        assert login_args[1]["input"] == b"ecr-token-123"
        assert login_args[1]["check"] is True
        push_args = run_mock.call_args_list[1][0][0]
        assert push_args[:2] == ["helm", "push"]
        assert push_args[2] == str(self.chart_dir)
        assert push_args[3] == "oci://123456789123.dkr.ecr.eu-west-1.amazonaws.com"
        assert "--force" not in push_args

    @patch("entrypoint.subprocess.run")
    def test_ecr_mode_with_custom_username(self, run_mock):
        run_mock.return_value = MagicMock(returncode=0)
        with patch.dict(os.environ, self._env_ecr(INPUT_USERNAME="CustomUser"), clear=False):
            ep.main()
        login_args = run_mock.call_args_list[0][0][0]
        assert login_args[login_args.index("--username") + 1] == "CustomUser"

    @patch("entrypoint.subprocess.run")
    def test_classic_mode_calls_login_with_username_password_then_push(self, run_mock):
        run_mock.return_value = MagicMock(returncode=0)
        with patch.dict(os.environ, self._env_classic(), clear=False):
            ep.main()
        assert run_mock.call_count == 2
        login_args = run_mock.call_args_list[0]
        assert login_args[0][0] == [
            "helm",
            "registry",
            "login",
            "h.cfcr.io",
            "--username",
            "myuser",
            "--password-stdin",
        ]
        assert login_args[1]["input"] == b"mypass"
        push_args = run_mock.call_args_list[1][0][0]
        assert push_args[2] == str(self.chart_dir)
        assert push_args[3] == "https://h.cfcr.io/user/repo"

    @patch("entrypoint.subprocess.run")
    def test_force_true_adds_force_flag_to_push(self, run_mock):
        run_mock.return_value = MagicMock(returncode=0)
        with patch.dict(os.environ, self._env_classic(INPUT_FORCE="true"), clear=False):
            ep.main()
        push_args = run_mock.call_args_list[1][0][0]
        assert push_args[-1] == "--force"

    @patch("entrypoint.subprocess.run")
    def test_success_writes_push_status_to_github_output(self, run_mock, tmp_path):
        run_mock.return_value = MagicMock(returncode=0)
        with patch.dict(
            os.environ,
            self._env_classic(GITHUB_OUTPUT=str(tmp_path / "out")),
            clear=False,
        ):
            ep.main()
        assert (tmp_path / "out").read_text() == "push-status=success\n"

    def test_missing_registry_url_exits_1(self):
        with patch.dict(
            os.environ,
            {"GITHUB_WORKSPACE": str(self.workspace), "INPUT_CHART_FOLDER": "chart"},
            clear=False,
        ):
            for k in list(os.environ):
                if k.startswith("INPUT_"):
                    del os.environ[k]
            with pytest.raises(SystemExit) as exc_info:
                ep.main()
            assert exc_info.value.code == 1

    def test_chart_folder_not_found_exits_1(self):
        with patch.dict(
            os.environ,
            self._env_classic(INPUT_CHART_FOLDER="nonexistent"),
            clear=False,
        ):
            with pytest.raises(SystemExit) as exc_info:
                ep.main()
            assert exc_info.value.code == 1

    def test_classic_mode_without_password_exits_1(self):
        with patch.dict(
            os.environ,
            {
                **self._env_classic(),
                "INPUT_PASSWORD": "",
            },
            clear=False,
        ):
            with pytest.raises(SystemExit) as exc_info:
                ep.main()
            assert exc_info.value.code == 1

    def test_classic_mode_without_username_exits_1(self):
        with patch.dict(
            os.environ,
            {
                **self._env_classic(),
                "INPUT_USERNAME": "",
            },
            clear=False,
        ):
            with pytest.raises(SystemExit) as exc_info:
                ep.main()
            assert exc_info.value.code == 1

    @patch("entrypoint.subprocess.run")
    def test_login_failure_exits_1(self, run_mock):
        run_mock.side_effect = subprocess.CalledProcessError(1, "helm", stderr=b"login failed")
        with patch.dict(os.environ, self._env_classic(), clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ep.main()
            assert exc_info.value.code == 1

    @patch("entrypoint.subprocess.run")
    def test_push_failure_exits_1(self, run_mock):
        run_mock.side_effect = [
            MagicMock(returncode=0),
            subprocess.CalledProcessError(1, "helm", stderr=b"push failed"),
        ]
        with patch.dict(os.environ, self._env_classic(), clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ep.main()
            assert exc_info.value.code == 1
