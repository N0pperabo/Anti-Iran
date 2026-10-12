"""Structured logging and report generator for automation runs."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from models.run_report import ActionStepResult, RunSummary, StepStatus

logger = logging.getLogger(__name__)


class RunReporter:
    """Collects step execution results and produces formatted logs and JSON summaries."""

    def __init__(self, workflow_id: str, workflow_name: str, artifacts_dir: Path):
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.artifacts_dir = artifacts_dir
        self.start_time = datetime.now(timezone.utc).isoformat()
        self.steps: List[ActionStepResult] = []

    def record_step(self, step: ActionStepResult):
        """Records a completed step and prints a structured console log."""
        self.steps.append(step)
        idx = len(self.steps)
        status_marker = "SUCCESS" if step.status == StepStatus.SUCCESS else step.status.value.upper()
        selector_info = f" {step.used_selector}" if step.used_selector else ""
        print(f"[{idx}] {step.action_type.upper()}{selector_info} -> {status_marker} ({step.duration_ms}ms)")
        if step.error_message:
            print(f"    ERROR: {step.error_message}")
        if step.dom_snippet_on_failure:
            print(f"    DOM SNIPPET: {step.dom_snippet_on_failure[:120]}...")

    def finalize(self, overall_error: Optional[str] = None, state_saved: bool = False) -> RunSummary:
        """Finalizes the run, computes statistics, and writes report.json into artifacts."""
        end_time = datetime.now(timezone.utc).isoformat()
        total_actions = len(self.steps)
        succeeded = sum(1 for s in self.steps if s.status == StepStatus.SUCCESS)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in self.steps if s.status == StepStatus.SKIPPED)
        total_duration = sum(s.duration_ms for s in self.steps)

        overall_status = StepStatus.SUCCESS
        if failed > 0 or overall_error:
            overall_status = StepStatus.FAILED

        summary = RunSummary(
            workflow_id=self.workflow_id,
            workflow_name=self.workflow_name,
            start_time=self.start_time,
            end_time=end_time,
            total_duration_ms=total_duration,
            total_actions=total_actions,
            succeeded_actions=succeeded,
            failed_actions=failed,
            skipped_actions=skipped,
            overall_status=overall_status,
            state_saved=state_saved,
            error=overall_error,
            steps=self.steps,
        )

        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            report_path = self.artifacts_dir / "run_report.json"
            report_path.write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")
            logger.info(f"Saved run report to {report_path}")
        except Exception as e:
            logger.error(f"Failed to write run report: {e}")

        return summary
