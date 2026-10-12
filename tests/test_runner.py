"""End-to-end integration tests for automation runner."""

import json
from pathlib import Path
import pytest
from automation.runner import run_inspection, run_workflow_execution
from models.action_types import ClickAction, TypeAction
from models.workflow import WorkflowDefinition

HTML_FILE_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Runner Integration Test</title>
    <script>
        console.log("Inline script initialized");
        window.testVar = "Ready";
    </script>
</head>
<body>
    <h1>Integration Suite</h1>
    <input id="test-field" name="testname" placeholder="Type here..." />
    <button id="action-btn">Click me</button>
    <div id="status-display">Idle</div>
    <script>
        document.getElementById('action-btn').addEventListener('click', () => {
            document.getElementById('status-display').innerText = 'Completed';
        });
    </script>
</body>
</html>
"""


def test_runner_inspection_flow(tmp_path: Path):
    import asyncio

    async def _test():
        fixture_file = tmp_path / "page.html"
        fixture_file.write_text(HTML_FILE_CONTENT, encoding="utf-8")
        file_url = fixture_file.as_uri()

        artifacts_dir = tmp_path / "inspect_artifacts"
        exit_code = await run_inspection(
            url=file_url,
            state_file=None,
            encryption_key=None,
            artifacts_dir=artifacts_dir,
            headless=True,
        )
        assert exit_code == 0
        bundle_file = artifacts_dir / "inspection-bundle.json"
        assert bundle_file.exists()

        data = json.loads(bundle_file.read_text(encoding="utf-8"))
        assert data["title"] == "Runner Integration Test"
        assert len(data["dom_elements"]) > 0
        assert len(data["scripts"]) > 0
        assert (artifacts_dir / "preview.png").exists()

    asyncio.run(_test())


def test_runner_workflow_execution_flow(tmp_path: Path):
    import asyncio

    async def _test():
        fixture_file = tmp_path / "page.html"
        fixture_file.write_text(HTML_FILE_CONTENT, encoding="utf-8")
        file_url = fixture_file.as_uri()

        wf = WorkflowDefinition(
            version=1,
            id="test-wf-integration",
            name="Test Integration Run",
            target_url=file_url,
            restore_state=False,
            save_state=False,
            actions=[
                TypeAction(id="a-1", selector="#test-field", text="Testing Playwright"),
                ClickAction(id="a-2", selector="#action-btn"),
            ],
        )
        wf_file = tmp_path / "wf.json"
        wf_file.write_text(json.dumps(wf.model_dump()), encoding="utf-8")

        artifacts_dir = tmp_path / "run_artifacts"
        exit_code = await run_workflow_execution(
            workflow_source=str(wf_file),
            state_file=None,
            encryption_key=None,
            artifacts_dir=artifacts_dir,
            headless=True,
        )
        assert exit_code == 0
        report_file = artifacts_dir / "run_report.json"
        assert report_file.exists()

        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        assert report_data["overall_status"] == "success"
        assert report_data["total_actions"] == 2
        assert report_data["succeeded_actions"] == 2

    asyncio.run(_test())
