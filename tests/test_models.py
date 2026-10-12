"""Unit tests for models and workflow validation."""

import pytest
from pydantic import ValidationError
from models.action_types import ActionType, ClickAction, TypeAction, WaitAction
from models.workflow import WorkflowDefinition, ViewportConfig
from models.inspect_bundle import DOMElementInfo, InspectBundle
from models.run_report import ActionStepResult, RunSummary, StepStatus


def test_action_models_validation():
    click = ClickAction(
        id="act-1",
        selector="#search",
        description="Click search input",
        fallback_selectors=["input[name='q']", "[role='searchbox']"],
    )
    assert click.type == ActionType.CLICK
    assert click.selector == "#search"
    assert len(click.fallback_selectors) == 2

    type_act = TypeAction(
        id="act-2",
        selector="input[name='q']",
        text="GitHub Actions",
        clear_first=True,
    )
    assert type_act.type == ActionType.TYPE
    assert type_act.clear_first is True

    wait_act = WaitAction(id="act-3", milliseconds=1500)
    assert wait_act.type == ActionType.WAIT
    assert wait_act.milliseconds == 1500


def test_workflow_definition_sample():
    sample = WorkflowDefinition.create_sample()
    assert sample.version == 1
    assert sample.name == "GitHub Search Demo"
    assert len(sample.actions) == 4
    assert sample.actions[0].type == ActionType.CLICK

    # Test JSON round-trip
    dumped = sample.model_dump()
    reloaded = WorkflowDefinition.model_validate(dumped)
    assert reloaded.id == sample.id
    assert len(reloaded.actions) == len(sample.actions)


def test_inspect_bundle_model():
    bundle = InspectBundle(
        url="https://example.com",
        title="Example Domain",
        timestamp="2026-10-12T00:00:00Z",
        dom_elements=[
            DOMElementInfo(
                tag="input",
                id="q",
                name="search",
                suggested_selectors=["#q", "input[name='search']"],
            )
        ],
    )
    assert bundle.url == "https://example.com"
    assert len(bundle.dom_elements) == 1
    assert bundle.dom_elements[0].suggested_selectors[0] == "#q"


def test_run_report_summary():
    step1 = ActionStepResult(
        action_id="act-1",
        action_type="click",
        status=StepStatus.SUCCESS,
        duration_ms=42,
        used_selector="#btn",
    )
    summary = RunSummary(
        workflow_id="wf-1",
        workflow_name="Test WF",
        start_time="2026-10-12T00:00:00Z",
        total_actions=1,
        succeeded_actions=1,
        overall_status=StepStatus.SUCCESS,
        steps=[step1],
    )
    assert summary.overall_status == StepStatus.SUCCESS
    assert summary.steps[0].duration_ms == 42
