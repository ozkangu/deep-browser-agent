"""Browser skills — battle-tested composite actions for Chrome DevTools MCP.

Based on real testing against: Hacker News, Google, Skyscanner, Wikipedia,
GitHub, httpbin. All patterns verified with actual MCP calls.

KEY INSIGHT: All interactions are UID-based via accessibility tree snapshots,
not CSS selectors. UIDs are ephemeral and change after every navigation.
"""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def snapshot_and_plan(goal: str) -> str:
    """Plan how to achieve a browser goal using the snapshot-first approach.

    ALWAYS use this before complex multi-step interactions.
    It reminds the agent of the correct UID-based workflow.

    Args:
        goal: What you want to accomplish in the browser.
    """
    return (
        f"Goal: {goal}\n\n"
        f"Required workflow (UID-based):\n"
        f"1. take_snapshot → read the a11y tree, find element UIDs\n"
        f"2. Identify target elements by their description (e.g., textbox 'Email', button 'Submit')\n"
        f"3. Use UIDs in fill/click/hover calls\n"
        f"4. take_screenshot → verify the action worked\n"
        f"5. If navigated to a new page, take_snapshot again (UIDs have changed!)\n\n"
        f"IMPORTANT:\n"
        f"- click/fill/hover use `uid` parameter, NOT CSS selectors\n"
        f"- evaluate_script uses `function` parameter (arrow function), NOT `script`\n"
        f"- fill_form takes `elements: [{{uid, value}}]` for batch filling\n"
        f"- wait_for takes `text: ['string1', 'string2']` (array of strings)"
    )


@tool
def extract_data_js(description: str) -> str:
    """Generate a JavaScript function for data extraction via evaluate_script.

    Args:
        description: What data to extract (e.g., 'all links', 'table rows', 'page title').
    """
    snippets = {
        "title": '() => document.title',
        "url": '() => window.location.href',
        "links": '() => JSON.stringify(Array.from(document.querySelectorAll("a")).map(a => ({text: a.textContent.trim(), href: a.href})).filter(l => l.text))',
        "headings": '() => JSON.stringify(Array.from(document.querySelectorAll("h1, h2, h3")).map(h => ({tag: h.tagName, text: h.textContent.trim()})))',
        "images": '() => JSON.stringify(Array.from(document.querySelectorAll("img")).map(i => ({alt: i.alt, src: i.src})))',
        "tables": '() => JSON.stringify(Array.from(document.querySelectorAll("table")).map(t => ({rows: t.rows.length, html: t.outerHTML.substring(0, 500)})))',
        "meta": '() => JSON.stringify(Array.from(document.querySelectorAll("meta")).map(m => ({name: m.name || m.property, content: m.content})).filter(m => m.name))',
        "text": '() => document.body.innerText.substring(0, 3000)',
        "forms": '() => JSON.stringify(Array.from(document.querySelectorAll("input, textarea, select, button")).map(el => ({tag: el.tagName, type: el.type, name: el.name, id: el.id, placeholder: el.placeholder})))',
    }

    desc_lower = description.lower()
    matched = []
    for key, snippet in snippets.items():
        if key in desc_lower:
            matched.append(f"// Extract {key}\nevaluate_script(function=\"{snippet}\")")

    if not matched:
        matched.append(
            f"// Custom extraction for: {description}\n"
            f"evaluate_script(function=\"() => JSON.stringify(/* your selector here */)\")\n\n"
            f"Available patterns:\n" +
            "\n".join(f"  - {k}: {v[:60]}..." for k, v in snippets.items())
        )

    return "\n\n".join(matched)


@tool
def form_fill_guide(form_description: str) -> str:
    """Guide for filling a form — based on real tested patterns.

    Args:
        form_description: Description of the form and data to enter.
    """
    return (
        f"Form fill guide for: {form_description}\n\n"
        f"TESTED WORKFLOW:\n"
        f"1. take_snapshot → get the a11y tree\n"
        f"2. In the snapshot, look for:\n"
        f"   - `textbox \"Label\"` → use fill(uid=..., value=...)\n"
        f"   - `radio \"Label\"` → use click(uid=...) to select\n"
        f"   - `checkbox \"Label\"` → use click(uid=...) to toggle\n"
        f"   - `combobox \"Label\"` → use fill(uid=..., value=...) to type, or click to open\n"
        f"   - `button \"Submit\"` → use click(uid=...) to submit\n"
        f"   - `spinbutton \"Hours\"` → use fill(uid=..., value=...) for numeric\n\n"
        f"3. For batch fill, use fill_form:\n"
        f"   fill_form(elements=[{{\"uid\": \"1_2\", \"value\": \"John\"}}, ...], includeSnapshot=true)\n\n"
        f"4. After filling, take_screenshot to verify fields are populated\n"
        f"5. After submit, wait_for a confirmation text or take_screenshot\n\n"
        f"PITFALLS:\n"
        f"- NEVER use CSS selectors with fill/click — only UIDs from snapshot\n"
        f"- UIDs change per navigation: 1_X on first page, 2_X after nav, etc.\n"
        f"- InputTime fields have sub-elements (Hours spinbutton, Minutes spinbutton)\n"
        f"- Select/dropdown: may need click to open, then click option UID"
    )


@tool
def handle_bot_detection(site_name: str) -> str:
    """Advice for handling bot detection / CAPTCHA on a site.

    Args:
        site_name: The website that is blocking automation.
    """
    return (
        f"Bot detection encountered on: {site_name}\n\n"
        f"OBSERVED IN TESTING:\n"
        f"- Skyscanner: 'Are you a person or a robot?' with PRESS & HOLD challenge\n"
        f"- Google: reCAPTCHA after multiple searches in headless mode\n\n"
        f"MITIGATIONS (from most to least effective):\n"
        f"1. Use non-headless mode: remove --headless flag (shows real browser window)\n"
        f"2. Connect to an existing user Chrome session:\n"
        f"   - Launch Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome "
        f"--remote-debugging-port=9222\n"
        f"   - Connect MCP with: --browserUrl http://localhost:9222\n"
        f"   - This uses your real profile with cookies/sessions\n"
        f"3. Add realistic viewport: --viewport 1920x1080 (already default)\n"
        f"4. Don't use --isolated if you need persistent cookies\n"
        f"5. Use a proxy server: --proxyServer socks5://proxy:1080\n\n"
        f"IMPORTANT: Report the block to the user. Don't retry endlessly."
    )


@tool
def debug_page() -> str:
    """Generate a comprehensive debugging checklist for the current page."""
    return (
        "Debug checklist (execute each step):\n\n"
        "1. evaluate_script(function=\"() => JSON.stringify({readyState: document.readyState, "
        "url: window.location.href, title: document.title})\")\n\n"
        "2. list_console_messages → check for JS errors (msgid, level, text)\n\n"
        "3. list_network_requests → check for failed requests:\n"
        "   - Look for [4xx] or [5xx] status codes\n"
        "   - Use get_network_request(reqid=...) for details on failures\n\n"
        "4. take_snapshot → check if expected elements exist in a11y tree\n\n"
        "5. take_screenshot → visual verification\n\n"
        "6. evaluate_script(function=\"() => JSON.stringify({cookies: document.cookie.length, "
        "localStorage: Object.keys(localStorage).length, "
        "errors: window.__errors || 'none'})\")"
    )


@tool
def multi_tab_workflow(description: str) -> str:
    """Guide for working with multiple browser tabs.

    Args:
        description: What you want to do across tabs.
    """
    return (
        f"Multi-tab workflow for: {description}\n\n"
        f"TESTED COMMANDS:\n"
        f"- new_page(url=\"...\") → opens URL in new tab and selects it\n"
        f"- list_pages → shows all tabs with indices, marks [selected]\n"
        f"- select_page(index=0) → switch to tab by 0-based index\n"
        f"- close_page(index=1) → close a specific tab\n\n"
        f"WORKFLOW:\n"
        f"1. Open tabs: new_page(url=...) for each\n"
        f"2. list_pages to see all tabs and their indices\n"
        f"3. select_page(index=N) to switch\n"
        f"4. take_snapshot / take_screenshot on each tab\n"
        f"5. Each tab has independent UIDs — always take_snapshot after switching\n\n"
        f"NOTE: The last open page cannot be closed."
    )


@tool
def performance_audit_guide(url: str) -> str:
    """Step-by-step performance audit workflow.

    Args:
        url: URL to audit.
    """
    return (
        f"Performance audit for: {url}\n\n"
        f"1. navigate_page(url=\"{url}\")\n"
        f"2. performance_start_trace → begins recording\n"
        f"3. Interact with the page (scroll, click key elements)\n"
        f"4. performance_stop_trace → ends recording, returns insights\n"
        f"5. performance_analyze_insight(insightId=...) for deep-dive on specific issues\n"
        f"6. lighthouse_audit → comprehensive scoring (a11y, SEO, best practices)\n"
        f"7. take_memory_snapshot → if memory leak concern\n\n"
        f"Report: Combine trace insights + Lighthouse scores + any memory issues."
    )


def get_browser_skills() -> list:
    """Return all browser skill tools."""
    return [
        snapshot_and_plan,
        extract_data_js,
        form_fill_guide,
        handle_bot_detection,
        debug_page,
        multi_tab_workflow,
        performance_audit_guide,
    ]
