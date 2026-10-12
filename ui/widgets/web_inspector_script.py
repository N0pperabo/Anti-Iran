"""Client-side JavaScript code for natural action recording, DOM analysis, and local network blocking."""

INSPECTOR_JS_CODE = r"""
(function() {
    if (window.__STUDIO_RECORD_INITIALIZED__) {
        return;
    }
    window.__STUDIO_RECORD_INITIALIZED__ = true;
    window.__STUDIO_RECORD_ENABLED__ = true;

    // Toast notification container
    const toastContainer = document.createElement('div');
    toastContainer.id = '__studio_toast_container__';
    toastContainer.style.position = 'fixed';
    toastContainer.style.bottom = '20px';
    toastContainer.style.right = '20px';
    toastContainer.style.zIndex = '2147483647';
    toastContainer.style.pointerEvents = 'none';
    toastContainer.style.display = 'flex';
    toastContainer.style.flexDirection = 'column';
    toastContainer.style.gap = '8px';
    document.documentElement.appendChild(toastContainer);

    function showToast(msg, color) {
        const t = document.createElement('div');
        t.style.backgroundColor = color || '#1f6feb';
        t.style.color = '#ffffff';
        t.style.padding = '8px 16px';
        t.style.borderRadius = '6px';
        t.style.fontSize = '12px';
        t.style.fontFamily = '-apple-system, sans-serif';
        t.style.fontWeight = 'bold';
        t.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
        t.style.transition = 'opacity 0.3s ease';
        t.textContent = msg;
        toastContainer.appendChild(t);
        setTimeout(() => {
            t.style.opacity = '0';
            setTimeout(() => t.remove(), 300);
        }, 2200);
    }

    // Hover outline box
    const hoverBox = document.createElement('div');
    hoverBox.id = '__studio_hover_outline__';
    hoverBox.style.position = 'fixed';
    hoverBox.style.pointerEvents = 'none';
    hoverBox.style.zIndex = '2147483646';
    hoverBox.style.outline = '2px dashed #58a6ff';
    hoverBox.style.backgroundColor = 'rgba(88, 166, 255, 0.08)';
    hoverBox.style.borderRadius = '3px';
    hoverBox.style.display = 'none';
    document.documentElement.appendChild(hoverBox);

    function isStudioElement(el) {
        return el === toastContainer || el === hoverBox || toastContainer.contains(el);
    }

    function isStable(str) {
        if (!str || typeof str !== 'string') return false;
        str = str.trim();
        if (str.length < 1 || str.length > 50) return false;
        if (/^[0-9a-f]{8}-[0-9a-f]{4}/i.test(str)) return false;
        if (/^[a-z0-9_-]{24,}$/i.test(str)) return false;
        if (/:r[0-9a-z]+:/i.test(str)) return false;
        if (/^ember\d+$/i.test(str)) return false;
        if (/^\d+$/.test(str)) return false;
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
        const text = (el.innerText || el.textContent || '').trim();

        // 1. Text-based locator (Highest priority for buttons & links in Playwright)
        if (text && text.length >= 2 && text.length <= 40 && !text.includes('\n') && (tag === 'button' || tag === 'a' || tag === 'span' || tag === 'div')) {
            const safeText = text.replace(/"/g, '\\"');
            list.push(`${tag}:has-text("${safeText}")`);
        }

        // 2. Stable ID
        if (el.id && isStable(el.id)) {
            list.push('#' + CSS.escape(el.id));
        }

        // 3. Stable data-* attributes
        const dataAttrs = ['data-testid', 'data-test', 'data-qa', 'data-cy', 'data-id'];
        for (const attr of dataAttrs) {
            const val = el.getAttribute(attr);
            if (val) {
                list.push(`[${attr}="${val.replace(/"/g, '\\"')}"]`);
            }
        }

        // 4. Form name / Type
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

        // 6. Role / Aria
        const role = el.getAttribute('role');
        const ariaLabel = el.getAttribute('aria-label');
        if (role && ariaLabel) {
            list.push(`[role="${role}"][aria-label="${ariaLabel.replace(/"/g, '\\"')}"]`);
        } else if (ariaLabel) {
            list.push(`${tag}[aria-label="${ariaLabel.replace(/"/g, '\\"')}"]`);
        }

        // 7. Stable CSS class
        if (el.classList && el.classList.length > 0) {
            const stableClasses = Array.from(el.classList).filter(isStable);
            if (stableClasses.length > 0) {
                list.push(`${tag}.` + stableClasses.slice(0, 2).map(CSS.escape).join('.'));
            }
        }

        // 8. XPath fallback
        const xp = getXPath(el);
        if (xp) {
            list.push(`xpath=${xp}`);
        }

        return list.length > 0 ? list : [tag];
    }

    // 1. Mouse Hover Highlighting
    document.addEventListener('mousemove', function(e) {
        if (!window.__STUDIO_RECORD_ENABLED__) {
            hoverBox.style.display = 'none';
            return;
        }

        const target = document.elementFromPoint(e.clientX, e.clientY);
        if (!target || isStudioElement(target) || target === document.documentElement || target === document.body) {
            hoverBox.style.display = 'none';
            return;
        }

        const rect = target.getBoundingClientRect();
        hoverBox.style.display = 'block';
        hoverBox.style.top = Math.max(0, rect.top) + 'px';
        hoverBox.style.left = Math.max(0, rect.left) + 'px';
        hoverBox.style.width = rect.width + 'px';
        hoverBox.style.height = rect.height + 'px';
    }, true);

    // 2. Click Interception & Natural Recording (BLOCKS local navigation!)
    document.addEventListener('click', function(e) {
        if (!window.__STUDIO_RECORD_ENABLED__) return;

        const target = document.elementFromPoint(e.clientX, e.clientY);
        if (!target || isStudioElement(target)) return;

        const tag = target.tagName.toLowerCase();
        const isInput = (tag === 'input' || tag === 'textarea');
        const inputType = target.getAttribute('type') || '';

        // If it's a regular text input or textarea, let user focus and type
        if (isInput && !['button', 'submit', 'reset', 'checkbox', 'radio'].includes(inputType)) {
            return; // Allow focus for typing
        }

        // PREVENT LOCAL BROWSER FROM NAVIGATING OR SUBMITTING LOCALLY!
        e.preventDefault();
        e.stopPropagation();

        const selectors = computeSelectors(target);
        const primarySelector = selectors[0];
        const text = (target.innerText || target.textContent || '').trim().substring(0, 30);

        const payload = {
            type: 'click',
            selector: primarySelector,
            fallback_selectors: selectors.slice(1, 4),
            description: `Click ${tag}${text ? ' "' + text + '"' : ''}`
        };

        console.log("STUDIO_RECORD:" + JSON.stringify(payload));
        showToast(`✓ Recorded: CLICK on <${tag}> ${text ? '"' + text + '"' : ''}`, '#238636');
    }, true);

    // 3. Natural Typing Interception
    document.addEventListener('change', function(e) {
        if (!window.__STUDIO_RECORD_ENABLED__) return;
        const target = e.target;
        if (!target) return;

        const tag = target.tagName.toLowerCase();
        if (tag !== 'input' && tag !== 'textarea') return;

        const inputType = target.getAttribute('type') || 'text';
        if (['button', 'submit', 'reset'].includes(inputType)) return;

        const textVal = target.value;
        if (!textVal) return;

        const selectors = computeSelectors(target);
        const primarySelector = selectors[0];

        const payload = {
            type: 'type',
            selector: primarySelector,
            fallback_selectors: selectors.slice(1, 4),
            text: textVal,
            description: `Type "${textVal}" into ${primarySelector}`
        };

        console.log("STUDIO_RECORD:" + JSON.stringify(payload));
        showToast(`✓ Recorded: TYPE "${textVal}"`, '#1f6feb');
    }, true);

    // 4. Enter Key Detection
    document.addEventListener('keydown', function(e) {
        if (!window.__STUDIO_RECORD_ENABLED__) return;
        if (e.key === 'Enter') {
            const target = e.target;
            const tag = target ? target.tagName.toLowerCase() : '';
            if (tag === 'input') {
                // If there's text in input, record TYPE first
                if (target.value) {
                    const selectors = computeSelectors(target);
                    const primarySelector = selectors[0];
                    const typePayload = {
                        type: 'type',
                        selector: primarySelector,
                        fallback_selectors: selectors.slice(1, 4),
                        text: target.value,
                        description: `Type "${target.value}" into ${primarySelector}`
                    };
                    console.log("STUDIO_RECORD:" + JSON.stringify(typePayload));
                }

                // Record Enter key press
                const keyPayload = {
                    type: 'key_press',
                    key: 'Enter',
                    description: 'Press Enter key'
                };
                console.log("STUDIO_RECORD:" + JSON.stringify(keyPayload));
                showToast(`✓ Recorded: KEY Enter`, '#d29922');
            }
        }
    }, true);
})();
"""
