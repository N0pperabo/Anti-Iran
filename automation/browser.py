"""Playwright browser launcher, context manager, and session persistence."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from models.workflow import ViewportConfig
from automation.state import StateStore, mask_sensitive_data

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright lifecycle, browser context, and session storage."""

    def __init__(
        self,
        headless: bool = True,
        viewport: Optional[ViewportConfig] = None,
        user_agent: Optional[str] = None,
        state_store: Optional[StateStore] = None,
    ):
        self.headless = headless
        self.viewport = viewport or ViewportConfig()
        self.user_agent = user_agent
        self.state_store = state_store
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self, restore_state: bool = True) -> Tuple[BrowserContext, Page]:
        """Launches Chromium browser and initializes context with restored state if available."""
        self._playwright = await async_playwright().start()

        # Launch Chromium with anti-bot / standard options suitable for headless runs
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-infobars",
                "--window-position=0,0",
            ],
        )

        context_kwargs: Dict[str, Any] = {
            "viewport": {
                "width": self.viewport.width,
                "height": self.viewport.height,
            },
            "device_scale_factor": self.viewport.device_scale_factor,
        }

        if self.user_agent:
            context_kwargs["user_agent"] = self.user_agent

        # Restore storage state if available
        if restore_state and self.state_store:
            saved_state = self.state_store.load_state()
            if saved_state:
                logger.info(
                    "Restoring browser session state (Cookies count: %d, Origins count: %d)",
                    len(saved_state.get("cookies", [])),
                    len(saved_state.get("origins", [])),
                )
                context_kwargs["storage_state"] = saved_state

        self._context = await self._browser.new_context(**context_kwargs)
        self._page = await self._context.new_page()

        # Set default timeouts
        self._page.set_default_timeout(15000)
        self._page.set_default_navigation_timeout(30000)

        return self._context, self._page

    async def save_session_state(self) -> bool:
        """Captures cookies & storage and persists through the state store."""
        if not self._context or not self.state_store:
            return False

        try:
            current_state = await self._context.storage_state()
            success = self.state_store.save_state(current_state)
            logger.info("Persisted updated browser session state: %s", "Success" if success else "Failed")
            return success
        except Exception as e:
            logger.error("Failed to capture and persist storage state: %s", e)
            return False

    async def close(self, save_state: bool = True):
        """Cleanly saves state and closes browser resources."""
        if save_state and self._context:
            await self.save_session_state()

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
