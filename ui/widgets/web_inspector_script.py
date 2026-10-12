"""Client-side JavaScript code injected into QWebEngineView for real-time DOM inspection."""

INSPECTOR_JS_CODE = r"""
(function() {
    if (window.__STUDIO_INSPECTOR_INITIALIZED__) {
        return;
    }
    window.__STUDIO_INSPECTOR_INITIALIZED__ = true;
    window.__STUDIO_INSPECT_MODE__ = false;

    // Overlay highlight element
    const highlightBox = document.createElement('div');
    highlightBox.id = '__studio_highlight_overlay__';
    highlightBox.style.position = 'fixed';
    highlightBox.style.pointerEvents = 'none';
    highlightBox.style.zIndex = '2147483647';
    highlightBox.style.border = '2px solid #58a6ff';
    highlightBox.style.backgroundColor = 'rgba(88, 166, 255, 0.15)';
    highlightBox.style.borderRadius = '3px';
    highlightBox.style.transition = 'all 0.05s ease';
    highlightBox.style.display = 'none';
    document.documentElement.appendChild(highlightBox);

    // Tooltip badge near element
    const tooltip = document.createElement('div');
    tooltip.id = '__studio_tooltip_overlay__';
    tooltip.style.position = 'fixed';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.zIndex = '2147483647';
    tooltip.style.backgroundColor = '#161b22';
    tooltip.style.color = '#58a6ff';
    tooltip.style.padding = '3px 8px';
    tooltip.style.fontSize = '11px';
    tooltip.style.fontFamily = 'monospace';
    tooltip.style.borderRadius = '4px';
    tooltip.style.border = '1px solid #30363d';
    tooltip.style.boxShadow = '0 4px 12px rgba(0,0,0,0.4)';
    tooltip.style.display = 'none';
    document.documentElement.appendChild(tooltip);

    let currentHovered = null;

    function isStudioOverlay(el) {
        return el === highlightBox || el === tooltip;
    }

    function isStable(str) {
        if (!str || typeof str !== 'string') return false;
        str = str.trim();
        if (str.length < 1 || str.length > 50) return false;
        if (/^[0-9a-f]{8}-[0-9a-f]{4}/i.test(str)) return false; // UUID
        if (/^[a-z0-9_-]{24,}$/i.test(str)) return false; // Random hash
        if (/:r[0-9a-z]+:/i.test(str)) return false; // React useId
        if (/^ember\d+$/i.test(str)) return false;
        if (/^\d+$/.test(str)) return false; // Numeric
        return true;
    }

    function getXPath(element) {
        if (element.id && isStable(element.id)) return `//*[@id="${element.id}"]`;
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

    function computeSelectors(el) {
        const list = [];
        const tag = el.tagName.toLowerCase();

        // 1. Stable ID
        if (el.id && isStable(el.id)) {
            list.push('#' + CSS.escape(el.id));
        }

        // 2. Stable data attributes
        const dataAttrs = ['data-testid', 'data-test', 'data-qa', 'data-cy', 'data-id'];
        for (const attr of dataAttrs) {
            const val = el.getAttribute(attr);
            if (val) {
                list.push(`[${attr}="${val.replace(/"/g, '\\"')}"]`);
            }
        }

        // 3. Role / Aria
        const role = el.getAttribute('role');
        const ariaLabel = el.getAttribute('aria-label');
        if (role && ariaLabel) {
            list.push(`[role="${role}"][aria-label="${ariaLabel.replace(/"/g, '\\"')}"]`);
        } else if (ariaLabel) {
            list.push(`${tag}[aria-label="${ariaLabel.replace(/"/g, '\\"')}"]`);
        } else if (role) {
            list.push(`[role="${role}"]`);
        }

        // 4. Name attribute
        const name = el.getAttribute('name');
        if (name && isStable(name)) {
            list.push(`${tag}[name="${name.replace(/"/g, '\\"')}"]`);
        }

        // 5. Input Type / Placeholder
        if (tag === 'input') {
            const type = el.getAttribute('type') || 'text';
            const placeholder = el.getAttribute('placeholder');
            if (placeholder) {
                list.push(`input[type="${type}"][placeholder="${placeholder.replace(/"/g, '\\"')}"]`);
            } else {
                list.push(`input[type="${type}"]`);
            }
        }

        // 6. Stable Class
        if (el.classList && el.classList.length > 0) {
            const stableClasses = Array.from(el.classList).filter(isStable);
            if (stableClasses.length > 0) {
                list.push(`${tag}.` + stableClasses.slice(0, 2).map(CSS.escape).join('.'));
            }
        }

        // 7. XPath fallback
        const xp = getXPath(el);
        if (xp) {
            list.push(`xpath=${xp}`);
        }

        return list;
    }

    document.addEventListener('mousemove', function(e) {
        if (!window.__STUDIO_INSPECT_MODE__) {
            highlightBox.style.display = 'none';
            tooltip.style.display = 'none';
            return;
        }

        const target = document.elementFromPoint(e.clientX, e.clientY);
        if (!target || isStudioOverlay(target) || target === document.documentElement || target === document.body) {
            return;
        }

        currentHovered = target;
        const rect = target.getBoundingClientRect();

        highlightBox.style.display = 'block';
        highlightBox.style.top = Math.max(0, rect.top) + 'px';
        highlightBox.style.left = Math.max(0, rect.left) + 'px';
        highlightBox.style.width = rect.width + 'px';
        highlightBox.style.height = rect.height + 'px';

        const tag = target.tagName.toLowerCase();
        let badge = `<${tag}>`;
        if (target.id && isStable(target.id)) badge = `#${target.id}`;
        else if (target.getAttribute('name')) badge = `${tag}[name="${target.getAttribute('name')}"]`;

        tooltip.textContent = badge;
        tooltip.style.display = 'block';
        tooltip.style.top = Math.max(0, rect.top - 24) + 'px';
        tooltip.style.left = Math.max(0, rect.left) + 'px';
    }, true);

    document.addEventListener('click', function(e) {
        if (!window.__STUDIO_INSPECT_MODE__) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        const target = currentHovered || document.elementFromPoint(e.clientX, e.clientY);
        if (!target || isStudioOverlay(target)) {
            return;
        }

        const selectors = computeSelectors(target);
        const tag = target.tagName.toLowerCase();
        const text = (target.innerText || target.textContent || '').trim().substring(0, 80);

        const attrs = {};
        for (let i = 0; i < target.attributes.length; i++) {
            const a = target.attributes[i];
            attrs[a.name] = a.value;
        }

        const payload = {
            tag: tag,
            id: target.id || null,
            name: target.getAttribute('name') || null,
            role: target.getAttribute('role') || null,
            text: text,
            selectors: selectors,
            attributes: attrs,
            primary_selector: selectors.length > 0 ? selectors[0] : tag
        };

        console.log("STUDIO_INSPECT:" + JSON.stringify(payload));
    }, true);

    window.__STUDIO_SET_INSPECT_MODE = function(active) {
        window.__STUDIO_INSPECT_MODE__ = Boolean(active);
        if (!active) {
            highlightBox.style.display = 'none';
            tooltip.style.display = 'none';
        }
    };
})();
"""
