"""Action executor for declarative browser automation with retries, selector fallbacks, and failure diagnostics."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from models.action_types import (
    ActionType,
    BaseAction,
    TargetElementAction,
    ClickAction,
    DoubleClickAction,
    RightClickAction,
    TypeAction,
    ClearAction,
    KeyPressAction,
    KeyDownAction,
    KeyUpAction,
    MouseMoveAction,
    ScrollAction,
    WaitAction,
    SelectOptionAction,
    CheckAction,
    UncheckAction,
    ScreenshotAction,
    ExtractTextAction,
    ExtractAttributeAction,
    NavigateAction,
    GoBackAction,
    GoForwardAction,
    ReloadAction,
)
from models.run_report import ActionStepResult, StepStatus
from automation.selectors import verify_selector_ambiguity

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executes workflow actions against a Playwright Page instance."""

    def __init__(self, page: Page, artifacts_dir: Optional[Path] = None):
        self.page = page
        self.artifacts_dir = artifacts_dir or Path("artifacts")
        self.variables: Dict[str, Any] = {}

    async def execute_action(self, action: BaseAction) -> ActionStepResult:
        """Executes a single action with retry, fallback selectors, and failure diagnostics."""
        start_time = time.perf_counter()
        result = ActionStepResult(
            action_id=action.id,
            action_type=action.type.value,
            description=action.description,
            status=StepStatus.RUNNING,
        )

        if not action.enabled:
            result.status = StepStatus.SKIPPED
            result.duration_ms = 0
            return result

        try:
            # Build list of selectors to try: primary selector first, followed by fallbacks
            selectors_to_try: List[str] = []
            if isinstance(action, TargetElementAction):
                selectors_to_try.append(action.selector)
                selectors_to_try.extend(action.fallback_selectors)
            elif isinstance(action, KeyPressAction) and action.selector:
                selectors_to_try.append(action.selector)
                selectors_to_try.extend(action.fallback_selectors)
            elif isinstance(action, WaitAction) and action.selector:
                selectors_to_try.append(action.selector)
                selectors_to_try.extend(action.fallback_selectors)
            elif isinstance(action, ScrollAction) and action.selector:
                selectors_to_try.append(action.selector)
                selectors_to_try.extend(action.fallback_selectors)

            output = None
            used_selector = None

            if selectors_to_try:
                # Try selectors with retry
                last_error: Optional[Exception] = None
                success = False

                for selector in selectors_to_try:
                    for attempt in range(max(1, action.retry_count)):
                        try:
                            # Ambiguity safety check
                            count, is_unique = await verify_selector_ambiguity(self.page, selector)
                            if count > 1:
                                logger.warning(
                                    f"Selector '{selector}' matched {count} elements (ambiguous). Using strict locator resolution."
                                )

                            output = await self._dispatch_action(action, selector)
                            used_selector = selector
                            success = True
                            break
                        except Exception as e:
                            last_error = e
                            logger.info(
                                f"Attempt {attempt + 1} with selector '{selector}' failed: {e}. Retrying if possible."
                            )
                            await asyncio.sleep(0.3)
                    if success:
                        break

                if not success:
                    raise last_error or RuntimeError(f"Could not resolve any selector among {selectors_to_try}")
            else:
                # Element-independent action (e.g. Navigate, Wait, Reload, GoBack)
                output = await self._dispatch_action(action, selector=None)

            result.status = StepStatus.SUCCESS
            result.used_selector = used_selector
            result.output = output
        except Exception as e:
            logger.error(f"Action '{action.id}' ({action.type.value}) failed: {e}")
            result.status = StepStatus.FAILED
            result.error_message = str(e)
            # Capture failure diagnostics (screenshot & DOM snippet)
            await self._capture_failure_diagnostics(action, result)

        duration = int((time.perf_counter() - start_time) * 1000)
        result.duration_ms = duration
        return result

    async def _dispatch_action(self, action: BaseAction, selector: Optional[str]) -> Any:
        """Dispatches action execution based on action type."""
        timeout = action.timeout_ms

        if isinstance(action, ClickAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.click(
                button=action.button,
                modifiers=action.modifiers,
                timeout=timeout,
            )
            return None

        elif isinstance(action, DoubleClickAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.dblclick(timeout=timeout)
            return None

        elif isinstance(action, RightClickAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.click(button="right", timeout=timeout)
            return None

        elif isinstance(action, TypeAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            if action.clear_first:
                await locator.fill("")
            if action.delay_ms > 0:
                await locator.press_sequentially(action.text, delay=action.delay_ms)
            else:
                await locator.fill(action.text)
            return None

        elif isinstance(action, ClearAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.fill("")
            return None

        elif isinstance(action, KeyPressAction):
            if selector:
                locator = self.page.locator(selector).first
                await locator.press(action.key, timeout=timeout)
            else:
                await self.page.keyboard.press(action.key)
            return None

        elif isinstance(action, KeyDownAction):
            await self.page.keyboard.down(action.key)
            return None

        elif isinstance(action, KeyUpAction):
            await self.page.keyboard.up(action.key)
            return None

        elif isinstance(action, MouseMoveAction):
            await self.page.mouse.move(action.x, action.y)
            return None

        elif isinstance(action, ScrollAction):
            if selector:
                locator = self.page.locator(selector).first
                await locator.evaluate(
                    f"(el) => el.scrollBy({action.delta_x}, {action.delta_y})"
                )
            else:
                await self.page.mouse.wheel(action.delta_x, action.delta_y)
            return None

        elif isinstance(action, WaitAction):
            if selector:
                locator = self.page.locator(selector).first
                await locator.wait_for(state=action.state, timeout=action.milliseconds or timeout)
            else:
                await asyncio.sleep(action.milliseconds / 1000.0)
            return None

        elif isinstance(action, SelectOptionAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.select_option(values=action.values, timeout=timeout)
            return None

        elif isinstance(action, CheckAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.check(timeout=timeout)
            return None

        elif isinstance(action, UncheckAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.uncheck(timeout=timeout)
            return None

        elif isinstance(action, ScreenshotAction):
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            filename = action.filename or f"screenshot_{action.id}_{int(time.time())}.png"
            output_path = self.artifacts_dir / filename
            if selector:
                locator = self.page.locator(selector).first
                await locator.screenshot(path=str(output_path))
            else:
                await self.page.screenshot(path=str(output_path), full_page=action.full_page)
            return str(output_path)

        elif isinstance(action, ExtractTextAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            text = await locator.inner_text()
            self.variables[action.variable_name] = text
            return text

        elif isinstance(action, ExtractAttributeAction):
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            attr_val = await locator.get_attribute(action.attribute_name)
            self.variables[action.variable_name] = attr_val
            return attr_val

        elif isinstance(action, NavigateAction):
            await self.page.goto(action.url, timeout=timeout, wait_until="load")
            return None

        elif isinstance(action, GoBackAction):
            await self.page.go_back(timeout=timeout, wait_until="load")
            return None

        elif isinstance(action, GoForwardAction):
            await self.page.go_forward(timeout=timeout, wait_until="load")
            return None

        elif isinstance(action, ReloadAction):
            await self.page.reload(timeout=timeout, wait_until="load")
            return None

        else:
            raise ValueError(f"Unsupported action type: {action.type}")

    async def _capture_failure_diagnostics(self, action: BaseAction, result: ActionStepResult):
        """Captures screenshot and DOM context upon action failure for debugging."""
        try:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            shot_file = self.artifacts_dir / f"failure_{action.id}_{int(time.time())}.png"
            await self.page.screenshot(path=str(shot_file), full_page=False)
            result.failure_screenshot_path = str(shot_file)

            # Capture DOM snippet
            if isinstance(action, TargetElementAction) and action.selector:
                try:
                    snippet = await self.page.evaluate(
                        """(sel) => {
                            const el = document.querySelector(sel);
                            return el ? el.outerHTML.substring(0, 500) : "Element not found in DOM";
                        }""",
                        action.selector,
                    )
                    result.dom_snippet_on_failure = snippet
                except Exception:
                    pass
        except Exception as diag_err:
            logger.warning(f"Failed to capture diagnostics for {action.id}: {diag_err}")
