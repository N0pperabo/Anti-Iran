"""Central state manager coordinating application models, clients, and execution context."""

import logging
from pathlib import Path
from typing import List, Optional
from app.config import AppConfig
from app.keyring_store import (
    get_stored_github_token,
    set_stored_github_token,
    get_stored_state_key,
    set_stored_state_key,
)
from github.client import GitHubClient
from github.models import RepoValidationResult, WorkflowRunInfo
from models.workflow import WorkflowDefinition
from models.inspect_bundle import InspectBundle

logger = logging.getLogger(__name__)


class ApplicationStateManager:
    """Singleton-style coordinator for application configuration and runtime state."""

    def __init__(self):
        self.config = AppConfig.load()
        self._github_client: Optional[GitHubClient] = None
        self.current_workflow: WorkflowDefinition = WorkflowDefinition.create_sample()
        self.current_inspect_bundle: Optional[InspectBundle] = None
        self.recent_runs: List[WorkflowRunInfo] = []
        self.is_connected: bool = False
        self.last_validation: Optional[RepoValidationResult] = None

    def get_token(self) -> Optional[str]:
        return get_stored_github_token()

    def set_token(self, token: str) -> bool:
        success = set_stored_github_token(token)
        if success:
            self._github_client = None  # Force re-initialization
        return success

    def get_encryption_key(self) -> Optional[str]:
        return get_stored_state_key()

    def set_encryption_key(self, key: str) -> bool:
        return set_stored_state_key(key)

    def get_github_client(self) -> Optional[GitHubClient]:
        """Returns initialized GitHubClient if credentials are present."""
        token = self.get_token()
        if not token or not self.config.repo_owner or not self.config.repo_name:
            return None

        if self._github_client is None:
            self._github_client = GitHubClient(
                token=token,
                owner=self.config.repo_owner,
                repo=self.config.repo_name,
                default_branch=self.config.default_branch,
            )
        return self._github_client

    def validate_connection(self) -> RepoValidationResult:
        """Validates current GitHub settings and updates connection status."""
        client = self.get_github_client()
        if not client:
            res = RepoValidationResult(
                valid=False,
                owner=self.config.repo_owner,
                repo=self.config.repo_name,
                is_private=False,
                default_branch=self.config.default_branch,
                has_workflows=False,
                message="Missing Token, Repository Owner, or Repository Name.",
            )
            self.is_connected = False
            self.last_validation = res
            return res

        try:
            res = client.validate_connection()
            self.is_connected = res.valid
            self.last_validation = res
            return res
        except Exception as e:
            res = RepoValidationResult(
                valid=False,
                owner=self.config.repo_owner,
                repo=self.config.repo_name,
                is_private=False,
                default_branch=self.config.default_branch,
                has_workflows=False,
                message=f"Connection failed: {e}",
            )
            self.is_connected = False
            self.last_validation = res
            return res
