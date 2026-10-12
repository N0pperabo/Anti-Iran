"""Models for automation run reporting, step logs, and execution diagnostics."""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ActionStepResult(BaseModel):
    """Execution result for an individual workflow action."""
    action_id: str
    action_type: str
    description: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    duration_ms: int = 0
    used_selector: Optional[str] = None
    output: Optional[Any] = None
    error_message: Optional[str] = None
    failure_screenshot_path: Optional[str] = None
    dom_snippet_on_failure: Optional[str] = None


class RunSummary(BaseModel):
    """Overall execution summary of a workflow run."""
    workflow_id: str
    workflow_name: str
    start_time: str
    end_time: Optional[str] = None
    total_duration_ms: int = 0
    total_actions: int = 0
    succeeded_actions: int = 0
    failed_actions: int = 0
    skipped_actions: int = 0
    overall_status: StepStatus = StepStatus.PENDING
    state_saved: bool = False
    error: Optional[str] = None
    steps: List[ActionStepResult] = Field(default_factory=list)
