"""Unit tests for GitHubClient with mocked HTTP responses."""

import io
import json
from pathlib import Path
import zipfile
import pytest
import httpx
from github.client import GitHubClient
from github.exceptions import (
    AuthenticationError,
    FileCollisionError,
    RepositoryNotFoundError,
    WorkflowDispatchError,
    WorkflowNotFoundError,
)


def test_validate_connection_success(monkeypatch):
    def mock_get(url, **kwargs):
        if url.endswith("/user"):
            return httpx.Response(200, json={"login": "testuser"})
        elif "/repos/myowner/myrepo" in url and not url.endswith("/workflows"):
            return httpx.Response(200, json={"private": True, "default_branch": "main"})
        elif url.endswith("/workflows"):
            return httpx.Response(200, json={"total_count": 2})
        return httpx.Response(404)

    client = GitHubClient(token="mock_token", owner="myowner", repo="myrepo")
    monkeypatch.setattr(client, "_get_client", lambda timeout=30: httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(lambda req: mock_get(str(req.url)))))

    res = client.validate_connection()
    assert res.valid is True
    assert res.is_private is True
    assert res.has_workflows is True
    assert "Connected successfully" in res.message


def test_validate_connection_auth_error(monkeypatch):
    def mock_get(url, **kwargs):
        return httpx.Response(401, json={"message": "Bad credentials"})

    client = GitHubClient(token="bad_token", owner="myowner", repo="myrepo")
    monkeypatch.setattr(client, "_get_client", lambda timeout=30: httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(lambda req: mock_get(str(req.url)))))

    with pytest.raises(AuthenticationError):
        client.validate_connection()


def test_dispatch_workflow_success(monkeypatch):
    def mock_post(url, **kwargs):
        return httpx.Response(204)

    client = GitHubClient(token="mock_token", owner="myowner", repo="myrepo")
    monkeypatch.setattr(client, "_get_client", lambda timeout=30: httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(lambda req: mock_post(str(req.url)))))

    dispatched = client.dispatch_workflow("browser-automation.yml", inputs={"param": "1"})
    assert dispatched is True


def test_dispatch_workflow_not_found(monkeypatch):
    def mock_post(url, **kwargs):
        return httpx.Response(404, json={"message": "Not Found"})

    client = GitHubClient(token="mock_token", owner="myowner", repo="myrepo")
    monkeypatch.setattr(client, "_get_client", lambda timeout=30: httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(lambda req: mock_post(str(req.url)))))

    with pytest.raises(WorkflowNotFoundError):
        client.dispatch_workflow("invalid-workflow.yml")


def test_file_collision_error(monkeypatch):
    def mock_put(url, **kwargs):
        return httpx.Response(409, json={"message": "Conflict"})

    client = GitHubClient(token="mock_token", owner="myowner", repo="myrepo")
    monkeypatch.setattr(client, "_get_client", lambda timeout=30: httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(lambda req: mock_put(str(req.url)))))

    with pytest.raises(FileCollisionError):
        client.create_or_update_file(
            file_path="workflows/test.json",
            content="{}",
            commit_message="test",
            sha="old_sha",
        )


def test_download_and_extract_artifact(tmp_path: Path, monkeypatch):
    # Create in-memory zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("test_report.txt", "Sample execution log data")

    zip_bytes = zip_buffer.getvalue()

    def mock_get(url, **kwargs):
        return httpx.Response(200, content=zip_bytes)

    client = GitHubClient(token="mock_token", owner="myowner", repo="myrepo")
    monkeypatch.setattr(client, "_get_client", lambda timeout=120: httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(lambda req: mock_get(str(req.url)))))

    dest = tmp_path / "extracted_artifact"
    extracted = client.download_and_extract_artifact(artifact_id=12345, destination_dir=dest)

    assert len(extracted) == 1
    assert extracted[0].name == "test_report.txt"
    assert extracted[0].read_text() == "Sample execution log data"
