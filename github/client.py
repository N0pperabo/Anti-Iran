"""GitHub REST API client for repository management, workflow dispatching, and artifact retrieval."""

import base64
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import zipfile
import httpx

from github.exceptions import (
    GitHubAPIError,
    AuthenticationError,
    RepositoryNotFoundError,
    WorkflowDispatchError,
    WorkflowNotFoundError,
    FileCollisionError,
    ArtifactDownloadError,
)
from github.models import (
    WorkflowRunInfo,
    RunStatus,
    RunConclusion,
    JobInfo,
    JobStepInfo,
    ArtifactInfo,
    RepoValidationResult,
)

logger = logging.getLogger(__name__)


class GitHubClient:
    """Handles communication with GitHub REST API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, owner: str, repo: str, default_branch: str = "main"):
        self.token = token.strip()
        self.owner = owner.strip()
        self.repo = repo.strip()
        self.default_branch = default_branch.strip()
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Browser-Automation-Studio/1.0",
        }

    def _get_client(self, timeout: float = 30.0) -> httpx.Client:
        return httpx.Client(base_url=self.BASE_URL, headers=self._headers, timeout=timeout)

    def validate_connection(self) -> RepoValidationResult:
        """Validates credentials, repository access, privacy, and branch existence."""
        with self._get_client() as client:
            # 1. Check user authentication
            user_resp = client.get("/user")
            if user_resp.status_code == 401:
                raise AuthenticationError("Invalid Personal Access Token (401 Unauthorized)", status_code=401)
            elif user_resp.status_code != 200:
                raise GitHubAPIError(f"GitHub authentication check failed ({user_resp.status_code}): {user_resp.text}", status_code=user_resp.status_code)

            # 2. Check repository access
            repo_resp = client.get(f"/repos/{self.owner}/{self.repo}")
            if repo_resp.status_code == 404:
                raise RepositoryNotFoundError(f"Repository '{self.owner}/{self.repo}' not found or token lacks access.", status_code=404)
            elif repo_resp.status_code != 200:
                raise GitHubAPIError(f"Failed to access repository ({repo_resp.status_code}): {repo_resp.text}", status_code=repo_resp.status_code)

            repo_data = repo_resp.json()
            is_private = repo_data.get("private", False)
            default_branch = repo_data.get("default_branch", self.default_branch)

            # 3. Check workflows presence
            wf_resp = client.get(f"/repos/{self.owner}/{self.repo}/actions/workflows")
            has_workflows = False
            if wf_resp.status_code == 200:
                wf_data = wf_resp.json()
                has_workflows = wf_data.get("total_count", 0) > 0

            msg = "Connected successfully."
            if not is_private:
                msg += " WARNING: Repository is PUBLIC! Browser sessions and cookies should only be stored in PRIVATE repositories."

            return RepoValidationResult(
                valid=True,
                owner=self.owner,
                repo=self.repo,
                is_private=is_private,
                default_branch=default_branch,
                has_workflows=has_workflows,
                message=msg,
            )

    def dispatch_workflow(self, workflow_filename: str, inputs: Optional[Dict[str, Any]] = None, ref: Optional[str] = None) -> bool:
        """Triggers a workflow_dispatch event for the specified workflow."""
        ref = ref or self.default_branch
        url = f"/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_filename}/dispatches"
        payload = {
            "ref": ref,
            "inputs": inputs or {},
        }
        with self._get_client() as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 204:
                logger.info(f"Dispatched workflow '{workflow_filename}' on ref '{ref}'")
                return True
            elif resp.status_code == 404:
                raise WorkflowNotFoundError(f"Workflow '{workflow_filename}' not found in '{self.owner}/{self.repo}'", status_code=404)
            elif resp.status_code == 422:
                raise WorkflowDispatchError(f"Workflow dispatch rejected (invalid inputs or disabled workflow): {resp.text}", status_code=422)
            else:
                raise WorkflowDispatchError(f"Dispatch failed with status {resp.status_code}: {resp.text}", status_code=resp.status_code)

    def list_workflow_runs(self, workflow_filename: Optional[str] = None, per_page: int = 15) -> List[WorkflowRunInfo]:
        """Lists recent workflow execution runs."""
        endpoint = (
            f"/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_filename}/runs"
            if workflow_filename
            else f"/repos/{self.owner}/{self.repo}/actions/runs"
        )
        with self._get_client() as client:
            resp = client.get(endpoint, params={"per_page": per_page})
            if resp.status_code != 200:
                raise GitHubAPIError(f"Failed to list workflow runs: {resp.text}", status_code=resp.status_code)
            data = resp.json()
            runs = []
            for r in data.get("workflow_runs", []):
                runs.append(
                    WorkflowRunInfo(
                        id=r["id"],
                        workflow_id=r["workflow_id"],
                        name=r["name"],
                        head_branch=r.get("head_branch", ""),
                        status=RunStatus(r["status"]),
                        conclusion=RunConclusion(r["conclusion"]) if r.get("conclusion") else None,
                        html_url=r["html_url"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                        run_number=r["run_number"],
                        event=r["event"],
                    )
                )
            return runs

    def get_run(self, run_id: int) -> WorkflowRunInfo:
        """Retrieves details of a specific workflow run."""
        with self._get_client() as client:
            resp = client.get(f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}")
            if resp.status_code != 200:
                raise GitHubAPIError(f"Failed to get run {run_id}: {resp.text}", status_code=resp.status_code)
            r = resp.json()
            return WorkflowRunInfo(
                id=r["id"],
                workflow_id=r["workflow_id"],
                name=r["name"],
                head_branch=r.get("head_branch", ""),
                status=RunStatus(r["status"]),
                conclusion=RunConclusion(r["conclusion"]) if r.get("conclusion") else None,
                html_url=r["html_url"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                run_number=r["run_number"],
                event=r["event"],
            )

    def get_run_jobs(self, run_id: int) -> List[JobInfo]:
        """Retrieves jobs and step statuses for a run."""
        with self._get_client() as client:
            resp = client.get(f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/jobs")
            if resp.status_code != 200:
                return []
            data = resp.json()
            jobs = []
            for j in data.get("jobs", []):
                steps = [
                    JobStepInfo(
                        name=s["name"],
                        status=s["status"],
                        conclusion=s.get("conclusion"),
                        number=s["number"],
                        started_at=s.get("started_at"),
                        completed_at=s.get("completed_at"),
                    )
                    for s in j.get("steps", [])
                ]
                jobs.append(
                    JobInfo(
                        id=j["id"],
                        run_id=j["run_id"],
                        name=j["name"],
                        status=j["status"],
                        conclusion=j.get("conclusion"),
                        started_at=j.get("started_at"),
                        completed_at=j.get("completed_at"),
                        steps=steps,
                    )
                )
            return jobs

    def list_artifacts(self, run_id: int) -> List[ArtifactInfo]:
        """Lists artifacts associated with a workflow run."""
        with self._get_client() as client:
            resp = client.get(f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/artifacts")
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [
                ArtifactInfo(
                    id=a["id"],
                    name=a["name"],
                    size_in_bytes=a["size_in_bytes"],
                    archive_download_url=a["archive_download_url"],
                    expired=a.get("expired", False),
                    created_at=a["created_at"],
                )
                for a in data.get("artifacts", [])
            ]

    def download_and_extract_artifact(self, artifact_id: int, destination_dir: Path) -> List[Path]:
        """Downloads artifact ZIP from GitHub and extracts it to destination directory."""
        with self._get_client(timeout=120.0) as client:
            url = f"/repos/{self.owner}/{self.repo}/actions/artifacts/{artifact_id}/zip"
            resp = client.get(url, follow_redirects=True)
            if resp.status_code != 200:
                raise ArtifactDownloadError(f"Failed to download artifact {artifact_id} ({resp.status_code})")

            extracted_files: List[Path] = []
            try:
                destination_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    z.extractall(destination_dir)
                    for member in z.namelist():
                        extracted_files.append(destination_dir / member)
                logger.info(f"Extracted {len(extracted_files)} files from artifact {artifact_id} to {destination_dir}")
                return extracted_files
            except Exception as e:
                raise ArtifactDownloadError(f"Failed to extract artifact zip: {e}")

    def get_file_content(self, file_path: str, ref: Optional[str] = None) -> Tuple[str, str]:
        """Reads file from repository. Returns (content_str, sha)."""
        ref = ref or self.default_branch
        url = f"/repos/{self.owner}/{self.repo}/contents/{file_path}"
        with self._get_client() as client:
            resp = client.get(url, params={"ref": ref})
            if resp.status_code == 404:
                raise FileNotFoundError(f"File '{file_path}' not found on branch '{ref}'")
            elif resp.status_code != 200:
                raise GitHubAPIError(f"Failed to read file '{file_path}': {resp.text}", status_code=resp.status_code)

            data = resp.json()
            sha = data.get("sha", "")
            encoding = data.get("encoding", "base64")
            raw_content = data.get("content", "")
            if encoding == "base64":
                decoded = base64.b64decode(raw_content).decode("utf-8")
            else:
                decoded = raw_content
            return decoded, sha

    def create_or_update_file(
        self,
        file_path: str,
        content: str,
        commit_message: str,
        sha: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> str:
        """Creates or updates a file with collision protection (SHA check). Returns new SHA."""
        branch = branch or self.default_branch
        url = f"/repos/{self.owner}/{self.repo}/contents/{file_path}"
        b64_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        payload: Dict[str, Any] = {
            "message": commit_message,
            "content": b64_content,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        with self._get_client() as client:
            resp = client.put(url, json=payload)
            if resp.status_code == 409:
                raise FileCollisionError(f"File update conflict on '{file_path}': remote SHA has changed.", status_code=409)
            elif resp.status_code not in (200, 201):
                raise GitHubAPIError(f"Failed to save file '{file_path}' ({resp.status_code}): {resp.text}", status_code=resp.status_code)

            data = resp.json()
            return data.get("content", {}).get("sha", "")
