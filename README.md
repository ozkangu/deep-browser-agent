# Deep Browser Agent

AI-powered browser automation using [LangGraph](https://github.com/langchain-ai/langgraph) and [Chrome DevTools MCP](https://github.com/anthropics/anthropic-quickstarts/tree/main/chrome-devtools-mcp).

An autonomous agent that controls a real Chrome browser via natural language — fills forms, clicks buttons, reads pages, takes screenshots, and more. **The user sees every action happening in their own browser in real-time.**

## How it works

```
Chat popup / Frontend
  │  POST /bridge {message, url}
  ▼
Bridge Server (FastAPI)
  │  session management + LLM agent
  ▼
LangGraph ReAct Agent ←→ LLM (Claude, GPT-4o, Gemini, Ollama, ...)
  │
  ▼
langchain-mcp-adapters (stdio)
  │  JSON-RPC
  ▼
chrome-devtools-mcp (29 tools)
  │  CDP WebSocket
  ▼
User's Chrome Browser (--remote-debugging-port=9222)
  ├── Tab 1: gmail.com
  ├── Tab 2: example.com/form  ← agent acts HERE, user watches
  └── Tab N: ...
```

The key difference from typical browser agents: this doesn't open a separate headless Chrome. It connects to the **user's actual browser** via Chrome DevTools Protocol, finds the correct tab, and executes actions there. The user sees forms being filled and buttons being clicked in real-time.

## Quick Start

### Prerequisites

- **Node.js** 20.19+ (for chrome-devtools-mcp)
- **Python** 3.11+
- **Chrome** browser
- An LLM API key (Anthropic, OpenAI, OpenRouter, etc.)

### Install

```bash
git clone https://github.com/ozkangu/deep-browser-agent.git
cd deep-browser-agent

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .

# Configure
cp .env.example .env
# Edit .env → set your API key (e.g. ANTHROPIC_API_KEY)
```

### Run: CDP Bridge (Primary Mode)

This is the main way to use the agent — it controls your real browser.

**Step 1: Launch Chrome with debug port**

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Step 2: Start the bridge server**

```bash
deep-browser-agent-bridge
```

The server starts on `http://localhost:8878`.

**Step 3: Send instructions from your frontend**

```js
// Minimal frontend integration
const res = await fetch('http://localhost:8878/bridge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Fill the registration form with test data',
    url: window.location.href,  // tells agent which tab to target
  }),
});
const data = await res.json();
console.log(data.reply);       // "I filled the form with..."
console.log(data.session_id);  // reuse for multi-turn conversation
```

The agent finds your tab by URL, takes a snapshot of the accessibility tree, and executes fill/click/type actions on your visible page. You watch it happen.

### Multi-turn Conversation

The bridge supports stateful sessions. Pass `session_id` from the first response to continue the conversation:

```js
// Turn 1: Fill the form
const r1 = await fetch('http://localhost:8878/bridge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Fill name with "John" and email with "john@test.com"',
    url: 'https://example.com/form',
  }),
});
const d1 = await r1.json();

// Turn 2: Submit (same session, agent remembers context)
const r2 = await fetch('http://localhost:8878/bridge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Now submit the form',
    url: 'https://example.com/form',
    session_id: d1.session_id,  // continues the conversation
  }),
});

// Turn 3: Verify result
const r3 = await fetch('http://localhost:8878/bridge', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Take a screenshot and tell me what the result page says',
    url: 'https://example.com/form',
    session_id: d1.session_id,
  }),
});
```

### Frontend JS Helper

A ready-to-use JS class is included in the bridge module:

```js
class DeepBrowserBridge {
  constructor(serverUrl = 'http://localhost:8878') {
    this.serverUrl = serverUrl;
    this.sessionId = null;
  }

  async chat(message) {
    const res = await fetch(this.serverUrl + '/bridge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        url: window.location.href,
        session_id: this.sessionId,
      }),
    });
    const data = await res.json();
    this.sessionId = data.session_id;
    return data;
  }

  async close() {
    if (this.sessionId) {
      await fetch(this.serverUrl + '/bridge/close', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.sessionId }),
      });
      this.sessionId = null;
    }
  }
}

// Usage:
const agent = new DeepBrowserBridge();
const data = await agent.chat('Fill the form with test data');
console.log(data.reply);
await agent.close();
```

## Three Modes

| Mode | Command | Port | Description |
|------|---------|------|-------------|
| **CDP Bridge** | `deep-browser-agent-bridge` | 8878 | Controls user's real browser via CDP. Primary mode. |
| **Interactive CLI** | `deep-browser-agent` | — | Terminal-based interactive agent. |
| **Headless Server** | `deep-browser-agent-server` | 8877 | Separate headless Chrome per request. |

### Interactive CLI

```bash
deep-browser-agent                                        # normal mode
deep-browser-agent --headless                             # headless
deep-browser-agent --model ollama:llama3.3                # local model
deep-browser-agent --browser-url http://localhost:9222    # attach to running Chrome
```

Built-in shortcuts:
- `url <url>` — navigate and screenshot
- `screenshot` — capture current page
- `snapshot` — show accessibility tree with UIDs
- `pages` — list open tabs

### Python API

```python
import asyncio
from deep_browser_agent import BrowserAgentSession, AgentConfig

async def main():
    config = AgentConfig(model="anthropic:claude-sonnet-4-20250514")

    async with BrowserAgentSession(config=config) as session:
        result = await session.invoke(
            "Go to news.ycombinator.com, take a screenshot, "
            "and list the top 5 stories."
        )

asyncio.run(main())
```

## API Reference

### CDP Bridge Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/bridge` | Execute agent actions on user's browser |
| `POST` | `/bridge/close` | Close a session and free resources |
| `GET` | `/health` | Health check with active session count |

**POST /bridge** — Request:
```json
{
  "message": "Fill the name field with John",
  "url": "https://example.com/form",
  "session_id": null,
  "config": {}
}
```

**POST /bridge** — Response:
```json
{
  "reply": "I filled the name field with 'John'.",
  "session_id": "a1b2c3d4-...",
  "screenshot": "base64...",
  "actions_taken": ["list_pages({})", "select_page({index: 2})", "take_snapshot({})", "fill({uid: '1_3', value: 'John'})"],
  "success": true
}
```

## Multi-Provider Support

Use any LLM provider via `AGENT_MODEL` env var or `--model` flag:

| Provider | Example | Env Var |
|----------|---------|---------|
| **Anthropic** | `anthropic:claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| **OpenAI** | `openai:gpt-4o` | `OPENAI_API_KEY` |
| **OpenRouter** | `openrouter:deepseek/deepseek-chat-v3` | `OPENROUTER_API_KEY` |
| **Ollama** | `ollama:llama3.3` | `OLLAMA_BASE_URL` |
| **Azure** | `azure:gpt-4o` | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` |
| **Google** | `google:gemini-2.5-pro` | `GOOGLE_API_KEY` |

Anthropic and OpenAI come installed by default. For additional providers:

```bash
uv sync --extra google         # Google Gemini
uv sync --extra ollama         # Ollama (local)
uv sync --extra all-providers  # everything

# List presets
deep-browser-agent --providers
```

## Key Concept: UID-Based Interaction

Chrome DevTools MCP uses **UIDs from the accessibility tree**, not CSS selectors.

```
1. take_snapshot → returns a11y tree with UIDs
   uid=1_2 textbox "Username"
   uid=1_3 textbox "Password"
   uid=1_5 button "Log in"

2. fill(uid="1_2", value="john")
3. fill(uid="1_3", value="secret")
4. click(uid="1_5")
```

UIDs change after every navigation — the agent always takes a fresh snapshot before interacting. This is handled automatically by the system prompt.

## MCP Tools (29 total)

| Category | Tools |
|----------|-------|
| **Navigation** | `navigate_page`, `new_page`, `close_page`, `list_pages`, `select_page`, `wait_for` |
| **Input** | `click`, `fill`, `fill_form`, `type_text`, `press_key`, `hover`, `drag`, `upload_file`, `handle_dialog` |
| **Inspection** | `take_screenshot`, `take_snapshot`, `evaluate_script` |
| **Network** | `list_network_requests`, `get_network_request` |
| **Performance** | `performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight` |
| **Console** | `list_console_messages`, `get_console_message` |
| **Emulation** | `emulate`, `resize_page` |
| **Audit** | `lighthouse_audit`, `take_memory_snapshot` |

## Project Structure

```
src/deep_browser_agent/
├── __init__.py        # Public API
├── config.py          # AgentConfig — all settings
├── providers.py       # Multi-provider LLM support (6 providers)
├── agent.py           # Core: LangGraph agent + MCP connection
├── skills.py          # Browser skills (form filling, debugging, etc.)
├── bridge.py          # CDP Bridge server — controls user's real browser
├── server.py          # Headless server — separate Chrome per request
└── cli.py             # Interactive terminal UI
```

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture, data flow, session management
- [GUIDE.md](GUIDE.md) — Detailed Turkish guide with real test results

## License

MIT
