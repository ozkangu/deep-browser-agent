# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Deep Browser Agent                         │
│                                                                 │
│  ┌──────────────┐    ┌─────────────────────┐                   │
│  │   LLM        │    │  Browser Skills     │                   │
│  │  (any        │    │  (7 composite       │                   │
│  │   provider)  │    │   actions)          │                   │
│  └──────┬───────┘    └──────────┬──────────┘                   │
│         │                       │                               │
│  ┌──────▼───────────────────────▼──────────┐                   │
│  │         DeepAgent / ReAct Graph         │                   │
│  │           (LangGraph runtime)           │                   │
│  └──────────────────┬──────────────────────┘                   │
│                     │                                           │
│  ┌──────────────────▼──────────────────────┐                   │
│  │      langchain-mcp-adapters             │                   │
│  │      MultiServerMCPClient               │                   │
│  │      (stdio transport)                  │                   │
│  └──────────────────┬──────────────────────┘                   │
│                     │ JSON-RPC over stdin/stdout               │
└─────────────────────┼───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              chrome-devtools-mcp                                 │
│              (Node.js subprocess)                                │
│                                                                  │
│  ┌────────────┐ ┌──────────┐ ┌───────────┐ ┌────────────────┐  │
│  │ Navigation │ │  Input   │ │ Inspection│ │  Performance   │  │
│  │ 6 tools    │ │ 9 tools  │ │ 3 tools   │ │  5 tools       │  │
│  └────────────┘ └──────────┘ └───────────┘ └────────────────┘  │
│                                                                  │
│  Puppeteer (Chrome DevTools Protocol client)                     │
└─────────────────────┬────────────────────────────────────────────┘
                      │ CDP (WebSocket)
┌─────────────────────▼───────────────────────────────────────────┐
│                   Chrome Browser                                 │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │  Tab 1   │  │  Tab 2   │  │  Tab N   │                      │
│  │  (page)  │  │  (page)  │  │  (page)  │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Request → Agent Response

```
User: "Go to httpbin.org/forms/post and fill the name field with 'John'"
  │
  ▼
AgentConfig.from_env()          ← reads .env, CLI args
  │
  ▼
ProviderConfig                  ← resolves provider:model string
  │
  ▼
init_chat_model(...)            ← creates LangChain chat model
  │
  ▼
MultiServerMCPClient            ← spawns chrome-devtools-mcp via stdio
  │
  ▼
client.get_tools()              ← MCP tool discovery (29 tools)
  │
  ▼
create_deep_agent(              ← builds LangGraph agent graph
    model, tools, system_prompt     with MCP tools + browser skills
)
  │
  ▼
agent.ainvoke(message)          ← agent plans and executes:
  │
  ├─ navigate_page(url="https://httpbin.org/forms/post")
  ├─ take_snapshot()            → returns a11y tree with UIDs
  ├─ fill(uid="1_2", value="John")
  └─ take_screenshot()          → returns PNG for verification
  │
  ▼
Response: "I navigated to the form and filled the name field with 'John'."
```

### 2. MCP Protocol (stdio)

```
Python process                    Node.js process
(deep_browser_agent)              (chrome-devtools-mcp)
      │                                  │
      │  ──── initialize ──────────►     │
      │  ◄─── capabilities ────────     │
      │                                  │
      │  ──── tools/list ──────────►     │
      │  ◄─── 29 tool schemas ─────     │
      │                                  │
      │  ──── tools/call ──────────►     │  ──── CDP ────► Chrome
      │       navigate_page              │
      │  ◄─── result ─────────────      │  ◄──────────── Chrome
      │                                  │
      │  ──── tools/call ──────────►     │  ──── CDP ────► Chrome
      │       take_snapshot              │
      │  ◄─── a11y tree ──────────      │  ◄──────────── Chrome
      │                                  │
      │  ──── tools/call ──────────►     │  ──── CDP ────► Chrome
      │       fill(uid, value)           │
      │  ◄─── "success" ──────────      │  ◄──────────── Chrome
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
├── browser_url: str | None connect to running Chrome
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

PROVIDER_PRESETS: dict of shorthand names
├── "openrouter-claude" → openrouter:anthropic/claude-sonnet-4-20250514
├── "ollama-llama"      → ollama:llama3.3
└── ...
```

### `agent.py` — Core Agent

```
_create_agent_async(config, extra_tools)
│
├── 1. MultiServerMCPClient(stdio)     ← connect to MCP
│      └── get_tools() → 29 tools
│
├── 2. get_browser_skills() → 7 skills
│
├── 3. create_model(provider_config)   ← init LLM
│
└── 4. create_deep_agent(model, tools) ← build graph
       │   or create_react_agent()
       │
       └── Returns: (agent_graph, mcp_client)

BrowserAgentSession                    ← async context manager
├── __aenter__  → _create_agent_async
├── invoke(msg) → agent.ainvoke
├── stream(msg) → agent.astream
└── __aexit__   → client.close
```

### `skills.py` — Browser Skills

Skills are LangChain `@tool` functions that return text instructions.
They don't execute browser actions directly — they guide the agent
on how to use the MCP tools correctly.

```
snapshot_and_plan(goal)       → UID-based workflow reminder
extract_data_js(description) → JS snippet templates
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

## UID System Deep Dive

The accessibility tree snapshot is the foundation of all interactions:

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
| `spinbutton` | Set number | `fill(uid, value)` |
| Any | Hover | `hover(uid)` |

## Comparison: WebMCP vs Chrome DevTools MCP

```
Chrome DevTools MCP (this project)     WebMCP (Chrome 146+, future)
──────────────────────────────────     ─────────────────────────────
External agent controls browser        Website IS the MCP server
Works on ANY website                   Only sites that opt-in
29 generic tools (screenshot, DOM...)  Site-specific tools (searchFlights...)
UID + a11y tree interaction            Structured JSON responses
~18k tokens for tool schemas           ~200 tokens per site tool
Subject to bot detection               No bot detection (site cooperates)
Available NOW                          Experimental (Chrome Canary flag)
```

Both are complementary. This project uses Chrome DevTools MCP because it works
universally today. As WebMCP adoption grows, agents can prefer WebMCP tools
when available and fall back to DevTools MCP for sites that don't support it.
