"""Automation Runner CLI entrypoint for both GitHub Actions workflows and local testing."""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from automation.browser import BrowserManager
from automation.inspector import PageInspector
from automation.actions import ActionExecutor
from automation.reporting import RunReporter
from automation.state import EncryptedFileStateStore, mask_sensitive_data
from models.workflow import WorkflowDefinition, ViewportConfig
from models.run_report import StepStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("automation.runner")


async def run_inspection(
    url: str,
    state_file: Optional[Path],
    encryption_key: Optional[str],
    artifacts_dir: Path,
    viewport_width: int = 1280,
    viewport_height: int = 800,
    headless: bool = True,
) -> int:
    """Executes page inspection, extracts DOM, scripts, screenshots, and saves bundle."""
    logger.info(f"Starting inspection for URL: {url}")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    state_store = None
    if state_file:
        state_store = EncryptedFileStateStore(state_file, encryption_key=encryption_key)

    viewport = ViewportConfig(width=viewport_width, height=viewport_height)
    browser_manager = BrowserManager(
        headless=headless,
        viewport=viewport,
        state_store=state_store,
    )

    try:
        context, page = await browser_manager.start(restore_state=True)
        logger.info(f"Navigating to {url}...")
        await page.goto(url, wait_until="load", timeout=30000)

        inspector = PageInspector(page)
        bundle = await inspector.inspect(capture_screenshot=True)

        bundle_path = artifacts_dir / "inspection-bundle.json"
        bundle_path.write_text(json.dumps(bundle.model_dump(), indent=2), encoding="utf-8")
        logger.info(f"Successfully saved inspection bundle to {bundle_path}")

        # Also write the raw screenshot image file if present
        if bundle.screenshot_base64:
            import base64
            shot_file = artifacts_dir / "preview.png"
            shot_file.write_bytes(base64.b64decode(bundle.screenshot_base64))
            logger.info(f"Saved preview screenshot to {shot_file}")

        # Save any new cookies/storage state
        if state_store:
            await browser_manager.save_session_state()

        return 0
    except Exception as e:
        logger.error(f"Inspection failed: {e}", exc_info=True)
        return 1
    finally:
        await browser_manager.close(save_state=False)


async def run_workflow_execution(
    workflow_source: str,
    state_file: Optional[Path],
    encryption_key: Optional[str],
    artifacts_dir: Path,
    headless: bool = True,
) -> int:
    """Executes a declarative workflow step-by-step."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse workflow JSON from file or string
    try:
        source_path = Path(workflow_source)
        if source_path.exists():
            content = source_path.read_text(encoding="utf-8")
        else:
            content = workflow_source
        data = json.loads(content)
        workflow = WorkflowDefinition.model_validate(data)
    except Exception as e:
        logger.error(f"Failed to parse workflow definition: {e}")
        return 2

    logger.info(f"Executing workflow '{workflow.name}' (Actions: {len(workflow.actions)})")

    state_store = None
    if state_file:
        state_store = EncryptedFileStateStore(state_file, encryption_key=encryption_key)

    reporter = RunReporter(workflow.id, workflow.name, artifacts_dir)
    browser_manager = BrowserManager(
        headless=headless,
        viewport=workflow.viewport,
        user_agent=workflow.user_agent,
        state_store=state_store,
    )

    overall_error: Optional[str] = None
    state_saved = False

    try:
        context, page = await browser_manager.start(restore_state=workflow.restore_state)
        executor = ActionExecutor(page, artifacts_dir=artifacts_dir)

        # Navigate to target_url if provided
        if workflow.target_url:
            logger.info(f"Navigating to initial target: {workflow.target_url}")
            await page.goto(workflow.target_url, wait_until="load", timeout=30000)

        # Execute actions in order
        for action in workflow.actions:
            step_result = await executor.execute_action(action)
            reporter.record_step(step_result)

            if step_result.status == StepStatus.FAILED:
                overall_error = f"Action {action.id} failed: {step_result.error_message}"
                logger.error(f"Terminating workflow execution on failure: {overall_error}")
                break

        # Persist updated session state if requested
        if workflow.save_state and state_store:
            state_saved = await browser_manager.save_session_state()

        # Capture resulting page state so desktop app renders the updated page after actions
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=6000)
        except Exception:
            pass

        try:
            final_inspector = PageInspector(page)
            final_bundle = await final_inspector.inspect(capture_screenshot=True)
            bundle_path = artifacts_dir / "inspection-bundle.json"
            bundle_path.write_text(json.dumps(final_bundle.model_dump(), indent=2), encoding="utf-8")
            if final_bundle.screenshot_base64:
                import base64
                shot_file = artifacts_dir / "preview.png"
                shot_file.write_bytes(base64.b64decode(final_bundle.screenshot_base64))
            logger.info(f"Captured post-execution page snapshot for: {final_bundle.url}")
        except Exception as e:
            logger.warning(f"Could not capture post-execution page snapshot: {e}")

    except Exception as e:
        overall_error = str(e)
        logger.error(f"Fatal error during execution: {e}", exc_info=True)
    finally:
        await browser_manager.close(save_state=False)

    summary = reporter.finalize(overall_error=overall_error, state_saved=state_saved)
    return 0 if summary.overall_status == StepStatus.SUCCESS else 1


def main():
    parser = argparse.ArgumentParser(description="GitHub Actions Browser Automation Runner")
    parser.add_argument("--mode", choices=["inspect", "execute"], required=True, help="Mode of operation")
    parser.add_argument("--url", type=str, help="Target URL (required for inspect)")
    parser.add_argument("--workflow", type=str, help="Workflow JSON string or path to workflow.json (for execute)")
    parser.add_argument("--state-file", type=str, default="state/browser_state.enc", help="Path to encrypted browser state file")
    parser.add_argument("--state-key", type=str, default=None, help="State encryption key (or env BROWSER_STATE_KEY)")
    parser.add_argument("--artifacts-dir", type=str, default="artifacts", help="Directory to save run/inspection artifacts")
    parser.add_argument("--viewport-width", type=int, default=1280, help="Viewport width in pixels")
    parser.add_argument("--viewport-height", type=int, default=800, help="Viewport height in pixels")
    parser.add_argument("--no-headless", action="store_true", help="Run with visible browser window")

    args = parser.parse_args()
    artifacts_path = Path(args.artifacts_dir)
    state_path = Path(args.state_file) if args.state_file else None
    headless = not args.no_headless

    if args.mode == "inspect":
        if not args.url:
            parser.error("--url is required when --mode is inspect")
        exit_code = asyncio.run(
            run_inspection(
                url=args.url,
                state_file=state_path,
                encryption_key=args.state_key,
                artifacts_dir=artifacts_path,
                viewport_width=args.viewport_width,
                viewport_height=args.viewport_height,
                headless=headless,
            )
        )
    else:  # execute
        if not args.workflow:
            parser.error("--workflow is required when --mode is execute")
        exit_code = asyncio.run(
            run_workflow_execution(
                workflow_source=args.workflow,
                state_file=state_path,
                encryption_key=args.state_key,
                artifacts_dir=artifacts_path,
                headless=headless,
            )
        )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
