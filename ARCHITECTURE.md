# Architecture

## System Overview

Deep Browser Agent has three operating modes. All share the same core: a LangGraph agent connected to Chrome DevTools MCP.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Deep Browser Agent                            │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Mode 1: CDP Bridge (bridge.py)        ← PRIMARY              │ │
│  │  Connects to user's real Chrome via CDP                       │ │
│  │  User sees actions in their own browser                       │ │
│  │  POST /bridge on port 8878                                    │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  Mode 2: Interactive CLI (cli.py)                             │ │
│  │  Terminal-based agent, opens its own Chrome                   │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  Mode 3: Headless Server (server.py)                          │ │
│  │  Separate headless Chrome per request                         │ │
│  │  POST /chat on port 8877                                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                             │                                       │
│  ┌──────────────┐    ┌──────▼───────────┐    ┌──────────────────┐  │
│  │   LLM        │    │  LangGraph       │    │  Browser Skills  │  │
│  │  (any        │◄──►│  ReAct Agent     │◄──►│  (7 composite    │  │
│  │   provider)  │    │                  │    │   guides)        │  │
│  └──────────────┘    └──────┬───────────┘    └──────────────────┘  │
│                             │                                       │
│  ┌──────────────────────────▼──────────────────────────────────┐   │
│  │           langchain-mcp-adapters                            │   │
│  │           MultiServerMCPClient (stdio transport)            │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              │ JSON-RPC over stdin/stdout          │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                  chrome-devtools-mcp                                 │
│                  (Node.js subprocess)                                │
│                                                                     │
│  ┌────────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────────┐  │
│  │ Navigation │ │  Input   │ │ Inspection│ │  Network/Perf/     │  │
│  │ 6 tools    │ │ 9 tools  │ │ 3 tools   │ │  Console/Audit     │  │
│  └────────────┘ └──────────┘ └───────────┘ │  11 tools          │  │
│                                             └────────────────────┘  │
│  Puppeteer (Chrome DevTools Protocol client)                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ CDP (WebSocket)
┌──────────────────────────────▼──────────────────────────────────────┐
│                       Chrome Browser                                │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │
│  │  Tab 1   │  │  Tab 2   │  │  Tab N   │                         │
│  │  (page)  │  │  (page)  │  │  (page)  │                         │
│  └──────────┘  └──────────┘  └──────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

## CDP Bridge Architecture (Primary Mode)

The CDP Bridge is the main way to use Deep Browser Agent. It allows a frontend (chat popup, extension, or any HTTP client) to control the user's actual browser.

```
┌───────────────────┐         ┌───────────────────────────────────────┐
│  Frontend         │         │  Bridge Server (FastAPI :8878)        │
│  (chat popup,     │  HTTP   │                                       │
│   extension,      │────────►│  SessionStore                         │
│   curl, etc.)     │         │  ├── Session abc-123                  │
│                   │◄────────│  │   ├── BrowserAgentSession          │
│                   │         │  │   │   ├── MCP Client (stdio)       │
│                   │         │  │   │   └── LangGraph Agent          │
│                   │         │  │   ├── messages[] (conversation)     │
│                   │         │  │   └── last_active (for cleanup)    │
│                   │         │  ├── Session def-456                  │
│                   │         │  │   └── ...                          │
│                   │         │  └── cleanup loop (10min timeout)     │
│                   │         └────────────────────┬──────────────────┘
└───────────────────┘                              │
                                                   │ CDP WebSocket
                              ┌────────────────────▼──────────────────┐
                              │  User's Chrome (:9222)                │
                              │  ├── Tab 1: gmail.com                 │
                              │  ├── Tab 2: form page  ← agent here  │
                              │  └── Tab 3: youtube.com               │
                              └───────────────────────────────────────┘
```

### Request Flow (CDP Bridge)

```
Frontend                    Bridge Server                  MCP / Chrome
   │                            │                              │
   │  POST /bridge              │                              │
   │  {message, url}            │                              │
   │───────────────────────────►│                              │
   │                            │                              │
   │                       get_or_create session               │
   │                       (reuse if session_id given)         │
   │                            │                              │
   │                       First request?                      │
   │                       Add "find tab by URL" prefix        │
   │                            │                              │
   │                       agent.ainvoke(messages)             │
   │                            │                              │
   │                            │  list_pages()                │
   │                            │─────────────────────────────►│
   │                            │  [{index:0, url:"gmail"},    │
   │                            │   {index:1, url:"form"},     │
   │                            │   {index:2, url:"youtube"}]  │
   │                            │◄─────────────────────────────│
   │                            │                              │
   │                            │  select_page(index=1)        │
   │                            │─────────────────────────────►│
   │                            │  "switched to tab 1"         │
   │                            │◄─────────────────────────────│
   │                            │                              │
   │                            │  take_snapshot()             │
   │                            │─────────────────────────────►│
   │                            │  uid=2_1 textbox "Name"      │
   │                            │  uid=2_2 textbox "Email"     │
   │                            │  uid=2_5 button "Submit"     │
   │                            │◄─────────────────────────────│
   │                            │                              │
   │                            │  fill(uid="2_1",value="John")│   User sees
   │                            │─────────────────────────────►│   "John" appear
   │                            │◄─────────────────────────────│   in form field
   │                            │                              │
   │                            │  fill(uid="2_2",             │   User sees
   │                            │       value="john@test.com") │   email appear
   │                            │─────────────────────────────►│   in form field
   │                            │◄─────────────────────────────│
   │                            │                              │
   │  {reply, session_id,       │                              │
   │   actions_taken, ...}      │                              │
   │◄───────────────────────────│                              │
   │                            │                              │
   │  Next request              │                              │
   │  (same session_id)         │                              │
   │───────────────────────────►│                              │
   │                       reuse session                       │
   │                       skip tab selection                  │
   │                       agent has full history              │
   │                            │  click(uid="2_5")            │   User sees
   │                            │─────────────────────────────►│   button click
   │                            │◄─────────────────────────────│
```

## Session Management

```
SessionStore
│
├── _sessions: dict[str, CDPSession]
│   │
│   ├── CDPSession
│   │   ├── session_id: str (uuid)
│   │   ├── agent_session: BrowserAgentSession
│   │   │   ├── _agent: LangGraph agent graph
│   │   │   └── _client: MultiServerMCPClient → chrome-devtools-mcp process
│   │   ├── messages: list  ← full conversation history (LangChain messages)
│   │   ├── last_active: float (timestamp)
│   │   └── _tab_selected: bool
│   │
│   └── CDPSession ...
│
├── get_or_create(session_id, config)
│   ├── Existing session_id? → return cached session
│   └── New? → BrowserAgentSession.__aenter__() → spawn MCP → return
│
├── remove(session_id)
│   └── BrowserAgentSession.__aexit__() → close MCP → delete
│
└── _cleanup_loop()
    └── Every 60s: remove sessions idle > 10 minutes
```

### Session Lifecycle

```
1. First request (no session_id)
   → SessionStore creates new CDPSession
   → BrowserAgentSession spawns chrome-devtools-mcp Node.js process
   → MCP connects to Chrome at localhost:9222
   → Agent uses list_pages + select_page to find correct tab
   → Returns session_id to frontend

2. Subsequent requests (with session_id)
   → SessionStore returns existing CDPSession
   → Agent has full conversation history
   → Skips tab selection (already on correct tab)
   → Executes new actions directly

3. Session cleanup
   → Idle > 10 minutes: auto-removed by cleanup loop
   → Manual: POST /bridge/close {session_id}
   → Server shutdown: all sessions closed
```

## Module Responsibilities

### `config.py` — Configuration

```
AgentConfig
├── model: str              "anthropic:claude-sonnet-4-20250514"
├── temperature: float      0.0
├── api_key: str | None     override provider API key
├── base_url: str | None    override base URL
├── headless: bool          Chrome headless mode
├── isolated: bool          temp profile, auto-cleanup
├── viewport: str           "1920x1080"
├── browser_url: str | None connect to running Chrome (CDP bridge uses this)
└── get_mcp_args() → list   builds CLI args for chrome-devtools-mcp
```

### `providers.py` — Multi-Provider LLM

```
ProviderConfig → init_chat_model kwargs

Supported providers:
├── anthropic   → langchain-anthropic     (direct)
├── openai      → langchain-openai        (direct)
├── openrouter  → langchain-openai        (custom base_url)
├── ollama      → langchain-ollama        (local)
├── azure       → langchain-openai        (azure_endpoint)
├── google      → langchain-google-genai  (direct)
└── <any>       → provider:model          (generic passthrough)
```

### `agent.py` — Core Agent

```
_create_agent_async(config, extra_tools)
│
├── 1. MultiServerMCPClient(stdio)     ← connect to chrome-devtools-mcp
│      └── get_tools() → 29 tools
│
├── 2. get_browser_skills() → 7 skills
│
├── 3. create_model(provider_config)   ← init LLM
│
└── 4. create_deep_agent(model, tools) ← build graph
       │   or create_react_agent()     (fallback)
       │
       └── Returns: (agent_graph, mcp_client)

BrowserAgentSession                    ← async context manager
├── __aenter__  → _create_agent_async
├── invoke(msg) → agent.ainvoke
├── stream(msg) → agent.astream
└── __aexit__   → client.close
```

### `bridge.py` — CDP Bridge Server

```
FastAPI app (:8878)
│
├── POST /bridge         ← main endpoint
│   ├── AgentConfig.from_env()
│   ├── Set: headless=False, isolated=False, browser_url=localhost:9222
│   ├── Prepend CDP_PROMPT_PREFIX to system prompt
│   ├── SessionStore.get_or_create(session_id)
│   └── CDPSession.execute(message, url) → BridgeResponse
│
├── POST /bridge/close   ← cleanup endpoint
│   └── SessionStore.remove(session_id)
│
└── GET /health          ← status check
    └── {status, mode, active_sessions}
```

### `server.py` — Headless Server

```
FastAPI app (:8877)
│
├── POST /chat
│   ├── Creates new AgentConfig(headless=True, isolated=True)
│   ├── Spawns fresh Chrome per request
│   ├── Navigates to requested URL
│   ├── Optionally injects cookies for auth
│   └── Returns {reply, screenshot, actions_taken}
│
└── GET /health
```

### `skills.py` — Browser Skills

Skills are LangChain `@tool` functions that return text instructions.
They don't execute browser actions — they guide the agent on how to use MCP tools correctly.

```
snapshot_and_plan(goal)       → UID-based workflow reminder
extract_data_js(description) → JS snippet templates for evaluate_script
form_fill_guide(description) → form fill workflow with UID patterns
handle_bot_detection(site)   → CAPTCHA mitigation advice
debug_page()                 → debugging checklist
multi_tab_workflow(desc)     → tab management patterns
performance_audit_guide(url) → performance audit steps
```

### `cli.py` — Interactive CLI

```
main()
├── parse CLI args (--model, --headless, --browser-url, etc.)
├── AgentConfig.from_env() + arg overrides
└── interactive_loop(config)
    ├── BrowserAgentSession(config)
    └── loop:
        ├── read user input
        ├── expand shortcuts (url, screenshot, snapshot, pages)
        ├── session.invoke(input)
        └── render AI response via Rich
```

## UID System

The accessibility tree snapshot is the foundation of all browser interactions:

```
uid=1_0 RootWebArea url="https://example.com/form"
  uid=1_1 heading "Register"
  uid=1_2 StaticText "Email: "
  uid=1_3 textbox "Email: "               ← fill target
  uid=1_4 StaticText "Password: "
  uid=1_5 textbox "Password: "            ← fill target
  uid=1_6 radio " Free plan"              ← click target
  uid=1_7 radio " Pro plan"               ← click target
  uid=1_8 checkbox " Accept terms"        ← click target
  uid=1_9 button "Sign up"                ← click target
```

### UID format: `{pageCounter}_{elementIndex}`

- `pageCounter` increments with each navigation (1, 2, 3, ...)
- `elementIndex` is the position in the a11y tree
- UIDs are **ephemeral** — invalidated by any navigation

### Element types and actions

| A11y Role | Action | Tool |
|-----------|--------|------|
| `textbox` | Type text | `fill(uid, value)` |
| `combobox` | Type or select | `fill(uid, value)` |
| `radio` | Select option | `click(uid)` |
| `checkbox` | Toggle | `click(uid)` |
| `button` | Press | `click(uid)` |
| `link` | Navigate | `click(uid)` |
| Any | Hover | `hover(uid)` |

## CDP Bridge vs Headless Server vs CLI

```
                    CDP Bridge           Headless Server       CLI
                    (bridge.py)          (server.py)           (cli.py)
──────────────────────────────────────────────────────────────────────
Chrome instance     User's own           New per request       New or user's
User sees actions   Yes                  No                    Yes (if non-headless)
Bot detection       Low (real browser)   High (headless)       Depends on mode
Session auth        User already logged  Cookie injection      User already logged
                    in                                         in
Multi-turn          Yes (session_id)     No                    Yes (interactive)
Use case            Chat popup,          Background tasks,     Development,
                    extension,           API automation        testing
                    frontend widget
Port                8878                 8877                  —
WebMCP compatible   Yes (same CDP)       No                    —
```

## WebMCP Migration Path

Chrome DevTools MCP and the upcoming WebMCP standard both use Chrome DevTools Protocol (CDP) as transport.

```
Current:                              Future (Chrome 146+):
CDP Bridge → chrome-devtools-mcp      CDP Bridge → WebMCP
             ↓                                     ↓
             CDP WebSocket                         CDP WebSocket
             ↓                                     ↓
             Chrome                                Chrome
             ↓                                     ↓
             Any website                           navigator.modelContext
             (UID-based generic tools)             (site-specific tools)
```

When WebMCP stabilizes:
- Sites that support WebMCP expose domain-specific tools (e.g., `searchFlights(from, to, date)`)
- The agent can prefer WebMCP tools when available (structured, efficient, no bot detection)
- Falls back to Chrome DevTools MCP for sites without WebMCP support (generic UID-based tools)
- The CDP bridge architecture stays the same — only the MCP server changes
