"""Core agent: bridges LangGraph DeepAgent with Chrome DevTools MCP.

Architecture:
    DeepAgent/ReAct → langchain-mcp-adapters (stdio) → chrome-devtools-mcp → Chrome (CDP)
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from deep_browser_agent.config import AgentConfig
from deep_browser_agent.providers import ProviderConfig, create_model, get_provider_from_string
from deep_browser_agent.skills import get_browser_skills

# ---------------------------------------------------------------------------
# System prompt based on REAL testing of chrome-devtools-mcp
# ---------------------------------------------------------------------------
DEFAULT_SYSTEM_PROMPT = """\
You are a browser automation agent with full Chrome DevTools access via MCP tools.

## CRITICAL: UID-Based Interaction Model

All interactive tools (click, fill, hover, drag) use **UIDs** from the accessibility tree,
NOT CSS selectors. The workflow is always:

1. Call `take_snapshot` → returns an a11y tree with UIDs like `uid=1_2 textbox "Username"`
2. Use the UID in tool calls: `fill(uid="1_2", value="john")` or `click(uid="1_5")`
3. UIDs change after every navigation — always take a fresh snapshot before interacting.

## Tool Parameter Reference (verified)

### navigate_page
- `url`: target URL (string)
- `type`: "url" | "back" | "forward" | "reload" (optional, default "url")

### take_snapshot
- No required params. Returns a11y tree with UIDs for all interactive elements.

### take_screenshot
- No required params. Returns a PNG image of the current viewport.

### click
- `uid`: element UID from snapshot (required)
- `dblClick`: boolean for double-click (optional)

### fill
- `uid`: element UID from snapshot (required)
- `value`: text to fill (required)

### fill_form
- `elements`: array of `{uid, value}` objects for batch filling (required)
- `includeSnapshot`: boolean to get updated snapshot after fill (optional)

### evaluate_script
- `function`: a JavaScript function expression (required). Must be an arrow function or function declaration.
  Examples: `() => document.title` or `(el) => el.innerText`
- `args`: optional array of element UIDs to pass as arguments

### press_key
- `key`: key name like "Enter", "Tab", "Escape", "ArrowDown" (required)

### wait_for
- `text`: array of strings — resolves when any text appears on page (required)
- `timeout`: max wait in ms (optional)

### hover
- `uid`: element UID from snapshot (required)

### list_pages / list_network_requests / list_console_messages
- No required params.

## Workflow Patterns

### Standard page interaction:
1. `navigate_page(url=...)` → go to page
2. `take_snapshot` → discover element UIDs
3. `fill(uid=..., value=...)` or `click(uid=...)` → interact
4. `take_screenshot` → verify result

### Form filling:
1. `take_snapshot` → find form field UIDs (textbox, radio, checkbox, button elements)
2. `fill` for text inputs, `click` for radios/checkboxes/buttons
3. Or use `fill_form(elements=[{uid, value}, ...])` for batch fill
4. `click` the submit button UID
5. `take_screenshot` to verify

### Data extraction:
1. `evaluate_script(function="() => JSON.stringify(document.querySelectorAll('h1')[0].textContent)")`
2. Or use `take_snapshot` and parse the a11y tree text

## Important Notes
- Bot detection: Sites like Google, Skyscanner may show CAPTCHAs in headless mode.
  If blocked, report this to the user rather than retrying endlessly.
- Always verify actions with screenshots or snapshots.
- UIDs are ephemeral — NEVER reuse UIDs from a previous snapshot after navigation.
- The `evaluate_script` parameter is called `function` (not `script`), and must be a
  JS function expression like `() => { ... }`.
"""


async def _create_agent_async(
    config: AgentConfig | None = None,
    extra_tools: list[Any] | None = None,
):
    """Create the browser agent (async).

    Returns (agent_graph, mcp_client) — caller must manage mcp_client lifecycle.
    """
    if config is None:
        config = AgentConfig.from_env()

    # ------------------------------------------------------------------
    # 1) Connect to Chrome DevTools MCP via stdio
    # ------------------------------------------------------------------
    mcp_client = MultiServerMCPClient(
        {
            "chrome-devtools": {
                "command": config.chrome_mcp_command,
                "args": config.get_mcp_args(),
                "transport": "stdio",
            }
        }
    )

    tools = await mcp_client.get_tools()
    skills = get_browser_skills()
    all_tools = tools + skills + (extra_tools or [])

    # ------------------------------------------------------------------
    # 2) Create LLM with multi-provider support
    # ------------------------------------------------------------------
    provider_config = get_provider_from_string(config.model)
    provider_config.temperature = config.temperature
    if config.api_key:
        provider_config.api_key = config.api_key
    if config.base_url:
        provider_config.base_url = config.base_url

    model = create_model(provider_config)

    system_prompt = config.system_prompt or DEFAULT_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # 3) Build agent graph
    # ------------------------------------------------------------------
    try:
        from deepagents import create_deep_agent

        agent = create_deep_agent(
            model=model,
            tools=all_tools,
            system_prompt=system_prompt,
        )
    except ImportError:
        from langgraph.prebuilt import create_react_agent

        agent = create_react_agent(
            model=model,
            tools=all_tools,
            prompt=system_prompt,
        )

    return agent, mcp_client


def create_browser_agent(
    config: AgentConfig | None = None,
    extra_tools: list[Any] | None = None,
):
    """Synchronous wrapper — returns (agent, mcp_client)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_create_agent_async(config, extra_tools))
    finally:
        loop.close()


class BrowserAgentSession:
    """Async context manager for agent lifecycle.

    Usage::

        async with BrowserAgentSession() as session:
            result = await session.invoke("Go to example.com and take a screenshot")
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        extra_tools: list[Any] | None = None,
    ):
        self._config = config
        self._extra_tools = extra_tools
        self._agent = None
        self._client = None

    async def __aenter__(self):
        self._agent, self._client = await _create_agent_async(
            self._config, self._extra_tools
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.close()

    async def invoke(self, message: str) -> dict:
        """Send a user message and return the full state dict."""
        return await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": message}]}
        )

    async def stream(self, message: str):
        """Stream agent responses."""
        async for chunk in self._agent.astream(
            {"messages": [{"role": "user", "content": message}]},
            stream_mode="messages",
        ):
            yield chunk

    @property
    def agent(self):
        return self._agent
