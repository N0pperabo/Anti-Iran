"""Categorized exceptions for GitHub REST API client operations."""

class GitHubAPIError(Exception):
    """Base exception for all GitHub API interactions."""
    def __init__(self, message: str, status_code: int = 0, details: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class AuthenticationError(GitHubAPIError):
    """Raised when GitHub PAT token is invalid or lacks necessary scopes."""
    pass


class RepositoryNotFoundError(GitHubAPIError):
    """Raised when target repository does not exist or user lacks access."""
    pass


class WorkflowNotFoundError(GitHubAPIError):
    """Raised when target workflow file is not found in repository."""
    pass


class WorkflowDispatchError(GitHubAPIError):
    """Raised when dispatching a workflow fails."""
    pass


class FileCollisionError(GitHubAPIError):
    """Raised when SHA mismatch indicates concurrent file update collision."""
    pass


class ArtifactDownloadError(GitHubAPIError):
    """Raised when downloading or extracting artifacts fails."""
    pass
