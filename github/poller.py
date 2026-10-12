"""Workflow run status poller and artifact fetcher."""

import logging
import time
from pathlib import Path
from typing import Callable, List, Optional
from github.client import GitHubClient
from github.models import ArtifactInfo, JobInfo, RunConclusion, RunStatus, WorkflowRunInfo

logger = logging.getLogger(__name__)


class WorkflowPoller:
    """Polls GitHub API for workflow run progress, step logs, and artifact completion."""

    def __init__(self, client: GitHubClient, poll_interval_sec: float = 3.0):
        self.client = client
        self.poll_interval_sec = poll_interval_sec

    def wait_for_new_run(
        self,
        workflow_filename: str,
        dispatched_after_timestamp: float,
        timeout_sec: float = 60.0,
    ) -> Optional[WorkflowRunInfo]:
        """Polls until a new run created after dispatch timestamp appears."""
        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                runs = self.client.list_workflow_runs(workflow_filename=workflow_filename, per_page=5)
                for r in runs:
                    # If this run was created recently (within last 2 minutes)
                    if r.status in (RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.COMPLETED):
                        return r
            except Exception as e:
                logger.debug(f"Error checking for new workflow run: {e}")
            time.sleep(self.poll_interval_sec)
        return None

    def poll_run_until_complete(
        self,
        run_id: int,
        on_status_update: Optional[Callable[[WorkflowRunInfo, List[JobInfo]], None]] = None,
        timeout_sec: float = 600.0,
    ) -> WorkflowRunInfo:
        """Polls run until completion, notifying status callback along the way."""
        start = time.time()
        while time.time() - start < timeout_sec:
            run_info = self.client.get_run(run_id)
            jobs = self.client.get_run_jobs(run_id)

            if on_status_update:
                on_status_update(run_info, jobs)

            if run_info.status == RunStatus.COMPLETED:
                return run_info

            time.sleep(self.poll_interval_sec)

        raise TimeoutError(f"Workflow run {run_id} timed out after {timeout_sec} seconds")
