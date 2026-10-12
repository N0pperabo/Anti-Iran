"""Page inspector module for DOM elements, JavaScript resources, and visual snapshots."""

import base64
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.async_api import Page

from models.inspect_bundle import DOMElementInfo, JavaScriptResource, InspectBundle
from automation.selectors import generate_candidate_selectors

logger = logging.getLogger(__name__)


class PageInspector:
    """Inspects a live Playwright page, extracting DOM elements, JavaScript resources, and visual captures."""

    def __init__(self, page: Page):
        self.page = page

    async def inspect(self, capture_screenshot: bool = True) -> InspectBundle:
        """Performs full inspection of the current page state."""
        url = self.page.url
        title = await self.page.title()
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Capture visual screenshot
        screenshot_b64 = None
        if capture_screenshot:
            try:
                shot_bytes = await self.page.screenshot(full_page=False)
                screenshot_b64 = base64.b64encode(shot_bytes).decode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot during inspection: {e}")

        # 2. Extract JavaScript resources
        scripts = await self._extract_scripts()

        # 3. Extract interactive & key DOM elements
        dom_elements = await self._extract_dom_elements()

        # 4. Extract storage metadata (counts and keys only, strictly no sensitive values)
        cookies_count = 0
        local_storage_keys: List[str] = []
        try:
            cookies = await self.page.context.cookies()
            cookies_count = len(cookies)
            ls_keys = await self.page.evaluate("() => Object.keys(localStorage)")
            local_storage_keys = list(ls_keys) if isinstance(ls_keys, list) else []
        except Exception as e:
            logger.debug(f"Failed to inspect storage metadata: {e}")

        # 5. Extract HTML snapshot (up to 500KB to prevent bloated bundles)
        html_snapshot = None
        try:
            full_html = await self.page.content()
            html_snapshot = full_html[:500000]
        except Exception as e:
            logger.debug(f"Failed to capture HTML snapshot: {e}")

        return InspectBundle(
            url=url,
            title=title,
            timestamp=now_iso,
            screenshot_base64=screenshot_b64,
            dom_elements=dom_elements,
            scripts=scripts,
            html_snapshot=html_snapshot,
            cookies_count=cookies_count,
            local_storage_keys=local_storage_keys,
            metadata={
                "viewport": self.page.viewport_size,
            },
        )

    async def _extract_scripts(self) -> List[JavaScriptResource]:
        """Extracts inline and external script tags from the page."""
        try:
            raw_scripts = await self.page.evaluate(
                """() => {
                    const scriptNodes = Array.from(document.querySelectorAll('script'));
                    return scriptNodes.map((s, idx) => {
                        const src = s.src || s.getAttribute('src');
                        const isInline = !src;
                        const content = isInline ? (s.textContent || '') : '';
                        let name = isInline ? `inline-script-${idx + 1}` : src.split('/').pop().split('?')[0] || `script-${idx + 1}.js`;
                        return {
                            id: `script-${idx}`,
                            name: name,
                            is_inline: isInline,
                            src: src || null,
                            script_type: s.type || 'text/javascript',
                            size_bytes: content.length,
                            content: content.substring(0, 100000) // cap inline script size at 100KB
                        };
                    });
                }"""
            )
            return [JavaScriptResource(**item) for item in raw_scripts]
        except Exception as e:
            logger.warning(f"Error extracting scripts: {e}")
            return []

    async def _extract_dom_elements(self) -> List[DOMElementInfo]:
        """Extracts visible, interactive, and semantic elements from the DOM."""
        try:
            raw_elements = await self.page.evaluate(
                """() => {
                    const query = 'a, button, input, textarea, select, form, [role], [data-testid], [data-test], [data-qa], h1, h2, h3, nav, header, main, table, tr, th, td';
                    const nodes = Array.from(document.querySelectorAll(query)).slice(0, 300); // cap to 300 key elements
                    
                    function getXPath(element) {
                        if (element.id !== '') return `//*[@id="${element.id}"]`;
                        if (element === document.body) return '/html/body';
                        let ix = 0;
                        const siblings = element.parentNode ? element.parentNode.childNodes : [];
                        for (let i = 0; i < siblings.length; i++) {
                            const sibling = siblings[i];
                            if (sibling === element) {
                                return (element.parentNode ? getXPath(element.parentNode) : '') + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                            }
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                                ix++;
                            }
                        }
                        return '';
                    }

                    return nodes.map(el => {
                        const rect = el.getBoundingClientRect();
                        const isVisible = rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
                        
                        // Collect attributes
                        const attrs = {};
                        for (let i = 0; i < el.attributes.length; i++) {
                            const a = el.attributes[i];
                            attrs[a.name] = a.value;
                        }

                        const text = (el.innerText || el.textContent || '').trim().substring(0, 100);

                        return {
                            tag: el.tagName.toLowerCase(),
                            id: el.id || null,
                            classes: Array.from(el.classList),
                            name: el.getAttribute('name') || null,
                            role: el.getAttribute('role') || null,
                            text_content: text || null,
                            attributes: attrs,
                            bounding_box: isVisible ? {
                                x: Math.round(rect.x),
                                y: Math.round(rect.y),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            } : null,
                            xpath: getXPath(el)
                        };
                    });
                }"""
            )

            result: List[DOMElementInfo] = []
            for item in raw_elements:
                candidates = generate_candidate_selectors(
                    tag=item["tag"],
                    attributes=item.get("attributes", {}),
                    role=item.get("role"),
                    text_content=item.get("text_content"),
                    xpath=item.get("xpath"),
                )
                suggested = [c.selector for c in candidates]
                elem_info = DOMElementInfo(
                    tag=item["tag"],
                    id=item.get("id"),
                    classes=item.get("classes", []),
                    name=item.get("name"),
                    role=item.get("role"),
                    text_content=item.get("text_content"),
                    attributes=item.get("attributes", {}),
                    bounding_box=item.get("bounding_box"),
                    suggested_selectors=suggested,
                    xpath=item.get("xpath"),
                )
                result.append(elem_info)

            return result
        except Exception as e:
            logger.warning(f"Error extracting DOM elements: {e}")
            return []
