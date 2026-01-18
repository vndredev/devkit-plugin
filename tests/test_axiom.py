"""Tests for lib/axiom.py - Axiom CLI wrapper."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.axiom import (
    axiom_status,
    check_auth,
    check_cli,
    check_token,
    create_dataset,
    delete_dataset,
    ingest_data,
    list_datasets,
    query_apl,
    validate_token,
)


class TestCheckCli:
    """Tests for check_cli()."""

    def test_cli_installed(self):
        """Should return success when CLI is installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="axiom version 0.12.0",
            )

            ok, msg = check_cli()

            assert ok is True
            assert "0.12.0" in msg

    def test_cli_not_installed(self):
        """Should return failure when CLI is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            ok, msg = check_cli()

            assert ok is False
            assert "not installed" in msg.lower()

    def test_cli_timeout(self):
        """Should handle timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("axiom", 30)

            ok, msg = check_cli()

            assert ok is False
            assert "timed out" in msg.lower()


class TestCheckAuth:
    """Tests for check_auth()."""

    def test_authenticated(self):
        """Should return success when authenticated."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Logged in as user@example.com",
            )

            ok, msg = check_auth()

            assert ok is True
            assert "user@example.com" in msg

    def test_not_authenticated(self):
        """Should return failure when not authenticated."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Not authenticated",
            )

            ok, msg = check_auth()

            assert ok is False
            assert "not authenticated" in msg.lower()

    def test_cli_not_installed(self):
        """Should handle CLI not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            ok, msg = check_auth()

            assert ok is False
            assert "not installed" in msg.lower()


class TestListDatasets:
    """Tests for list_datasets()."""

    def test_list_success(self):
        """Should return datasets list."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(
                    [
                        {"name": "logs", "description": "App logs"},
                        {"name": "http-requests", "description": "HTTP logs"},
                    ]
                ),
            )

            ok, datasets = list_datasets()

            assert ok is True
            assert isinstance(datasets, list)
            assert len(datasets) == 2
            assert datasets[0]["name"] == "logs"

    def test_list_empty(self):
        """Should handle empty dataset list."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[]",
            )

            ok, datasets = list_datasets()

            assert ok is True
            assert datasets == []

    def test_list_failure(self):
        """Should handle API failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Not authenticated",
            )

            ok, msg = list_datasets()

            assert ok is False
            assert isinstance(msg, str)


class TestCreateDataset:
    """Tests for create_dataset()."""

    def test_create_success(self):
        """Should create dataset successfully."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Dataset created",
            )

            ok, msg = create_dataset("test-logs", "Test dataset")

            assert ok is True
            assert "test-logs" in msg
            mock_run.assert_called_once()
            # Check that description was passed
            call_args = mock_run.call_args[0][0]
            assert "--name=test-logs" in call_args
            assert "--description=Test dataset" in call_args

    def test_create_without_description(self):
        """Should create dataset without description."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Dataset created",
            )

            ok, msg = create_dataset("test-logs")

            assert ok is True
            call_args = mock_run.call_args[0][0]
            assert "--description" not in " ".join(call_args)

    def test_create_failure(self):
        """Should handle creation failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Dataset already exists",
            )

            ok, msg = create_dataset("existing-dataset")

            assert ok is False
            assert "already exists" in msg.lower()


class TestDeleteDataset:
    """Tests for delete_dataset()."""

    def test_delete_success(self):
        """Should delete dataset successfully."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Dataset deleted",
            )

            ok, msg = delete_dataset("test-logs")

            assert ok is True
            assert "deleted" in msg.lower()

    def test_delete_with_force(self):
        """Should pass force flag."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")

            delete_dataset("test-logs", force=True)

            call_args = mock_run.call_args[0][0]
            assert "--force" in call_args


class TestQueryApl:
    """Tests for query_apl()."""

    def test_query_json_success(self):
        """Should return JSON query results."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps(
                    [
                        {"_time": "2024-01-01", "level": "error", "message": "Test"},
                    ]
                ),
            )

            ok, results = query_apl("['logs'] | limit 10")

            assert ok is True
            assert isinstance(results, list)
            assert results[0]["level"] == "error"

    def test_query_table_success(self):
        """Should return table format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="| _time | level |\n| 2024-01-01 | error |",
            )

            ok, results = query_apl("['logs'] | limit 10", format_output="table")

            assert ok is True
            assert isinstance(results, str)
            assert "_time" in results

    def test_query_failure(self):
        """Should handle query failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Invalid APL syntax",
            )

            ok, msg = query_apl("invalid query")

            assert ok is False
            assert "invalid" in msg.lower() or "failed" in msg.lower()


class TestIngestData:
    """Tests for ingest_data()."""

    def test_ingest_dict_list(self):
        """Should ingest list of dicts."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Ingested 2 events",
            )

            data = [{"level": "info", "message": "Test 1"}, {"level": "info", "message": "Test 2"}]
            ok, msg = ingest_data("logs", data)

            assert ok is True
            # Check that JSON was passed via stdin
            call_kwargs = mock_run.call_args[1]
            assert "input" in call_kwargs
            assert json.loads(call_kwargs["input"]) == data

    def test_ingest_json_string(self):
        """Should ingest JSON string directly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Ingested",
            )

            data = '{"level": "info"}'
            ok, msg = ingest_data("logs", data)

            assert ok is True
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["input"] == data


class TestCheckToken:
    """Tests for check_token()."""

    def test_token_from_env(self, monkeypatch):
        """Should detect token from environment."""
        monkeypatch.setenv("AXIOM_TOKEN", "xaat-1234567890abcdef")
        monkeypatch.setenv("AXIOM_DATASET", "logs")

        has_token, info = check_token()

        assert has_token is True
        assert info["source"] == "env"
        assert "xaat-123" in info["masked_token"]
        assert info["dataset"] == "logs"

    def test_token_from_env_local(self, tmp_path, monkeypatch):
        """Should detect token from .env.local."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AXIOM_TOKEN", raising=False)

        env_local = tmp_path / ".env.local"
        env_local.write_text('AXIOM_TOKEN="xaat-abcdef1234567890"')

        has_token, info = check_token()

        assert has_token is True
        assert info["source"] == "env.local"

    def test_no_token(self, tmp_path, monkeypatch):
        """Should handle missing token."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AXIOM_TOKEN", raising=False)
        monkeypatch.delenv("AXIOM_DATASET", raising=False)

        has_token, info = check_token()

        assert has_token is False
        assert info["source"] is None


class TestValidateToken:
    """Tests for validate_token()."""

    def test_valid_token(self):
        """Should validate working token."""
        with patch("lib.axiom.list_datasets") as mock_list:
            mock_list.return_value = (True, [{"name": "logs"}])

            ok, msg = validate_token()

            assert ok is True
            assert "1 datasets" in msg

    def test_invalid_token(self):
        """Should detect invalid token."""
        with patch("lib.axiom.list_datasets") as mock_list:
            mock_list.return_value = (False, "Unauthorized")

            ok, msg = validate_token()

            assert ok is False
            assert "failed" in msg.lower()


class TestAxiomStatus:
    """Tests for axiom_status()."""

    def test_full_status(self):
        """Should return comprehensive status."""
        with patch("lib.axiom.check_cli") as mock_cli:
            with patch("lib.axiom.check_auth") as mock_auth:
                with patch("lib.axiom.check_token") as mock_token:
                    with patch("lib.axiom.list_datasets") as mock_datasets:
                        mock_cli.return_value = (True, "axiom version 0.12.0")
                        mock_auth.return_value = (True, "Logged in as user")
                        mock_token.return_value = (
                            True,
                            {"has_token": True, "masked_token": "xaat-***"},
                        )
                        mock_datasets.return_value = (True, [{"name": "logs"}])

                        status = axiom_status()

                        assert status["cli_installed"] is True
                        assert status["authenticated"] is True
                        assert status["dataset_count"] == 1
                        assert "app.axiom.co" in status["dashboard"]

    def test_status_cli_not_installed(self):
        """Should handle CLI not installed."""
        with patch("lib.axiom.check_cli") as mock_cli:
            with patch("lib.axiom.check_token") as mock_token:
                mock_cli.return_value = (False, "Not installed")
                mock_token.return_value = (False, {"has_token": False})

                status = axiom_status()

                assert status["cli_installed"] is False
                assert status["authenticated"] is False
                assert status["datasets"] == []
