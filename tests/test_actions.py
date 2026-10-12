"""Unit tests for ActionExecutor using local HTML fixture and Playwright."""

from pathlib import Path
import pytest
from playwright.async_api import async_playwright
from models.action_types import (
    ActionType,
    ClickAction,
    TypeAction,
    KeyPressAction,
    WaitAction,
    ScreenshotAction,
    ExtractTextAction,
)
from models.run_report import StepStatus
from automation.actions import ActionExecutor


HTML_FIXTURE = """
<!DOCTYPE html>
<html>
<head><title>Automation Test Page</title></head>
<body>
    <h1 id="heading">Automation Studio Ready</h1>
    <input id="search-input" name="q" type="text" placeholder="Search..." />
    <button id="submit-btn" data-testid="submit-action">Submit</button>
    <div id="output-box">Default Text</div>
    <script>
        document.getElementById('submit-btn').addEventListener('click', () => {
            const val = document.getElementById('search-input').value;
            document.getElementById('output-box').innerText = 'Submitted: ' + val;
        });
    </script>
</body>
</html>
"""


def test_action_executor_flow(tmp_path: Path):
    import asyncio

    async def _test():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(HTML_FIXTURE)

            executor = ActionExecutor(page, artifacts_dir=tmp_path)

            # 1. Type into search input
            type_act = TypeAction(
                id="act-type",
                selector="#search-input",
                text="Playwright Actions",
            )
            res_type = await executor.execute_action(type_act)
            assert res_type.status == StepStatus.SUCCESS
            assert res_type.duration_ms >= 0

            # Verify input value
            val = await page.input_value("#search-input")
            assert val == "Playwright Actions"

            # 2. Click submit button using fallback selector
            click_act = ClickAction(
                id="act-click-fallback",
                selector="#non-existent-button-id",
                fallback_selectors=["[data-testid='submit-action']"],
            )
            res_click = await executor.execute_action(click_act)
            assert res_click.status == StepStatus.SUCCESS
            assert res_click.used_selector == "[data-testid='submit-action']"

            # 3. Extract text from output box
            extract_act = ExtractTextAction(
                id="act-extract",
                selector="#output-box",
                variable_name="res_text",
            )
            res_extract = await executor.execute_action(extract_act)
            assert res_extract.status == StepStatus.SUCCESS
            assert res_extract.output == "Submitted: Playwright Actions"
            assert executor.variables["res_text"] == "Submitted: Playwright Actions"

            # 4. Wait action
            wait_act = WaitAction(id="act-wait", milliseconds=200)
            res_wait = await executor.execute_action(wait_act)
            assert res_wait.status == StepStatus.SUCCESS

            # 5. Screenshot action
            shot_act = ScreenshotAction(id="act-shot", filename="test_shot.png")
            res_shot = await executor.execute_action(shot_act)
            assert res_shot.status == StepStatus.SUCCESS
            assert (tmp_path / "test_shot.png").exists()

            await browser.close()

    asyncio.run(_test())
