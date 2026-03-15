# Deep Browser Agent

AI-powered browser automation using [LangGraph DeepAgent](https://github.com/langchain-ai/deepagents) and [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp).

An autonomous agent that controls a real Chrome browser — navigates pages, fills forms, clicks buttons, takes screenshots, runs JavaScript, inspects network traffic, and audits performance. All driven by natural language.

## How it works

```
You (natural language)
 └─→ DeepAgent / ReAct (LangGraph)
      └─→ langchain-mcp-adapters (stdio)
           └─→ chrome-devtools-mcp (29 tools)
                └─→ Chrome Browser (CDP protocol)
                     └─→ Any website
```

The agent receives your instructions, plans a sequence of browser actions, executes them via Chrome DevTools Protocol, and reports back what it sees.

## Quick Start

```bash
# Prerequisites: Node.js 20.19+, Python 3.11+, Chrome

# Clone
git clone https://github.com/ozkangu/deep-browser-agent.git
cd deep-browser-agent

# Install with uv (recommended)
uv sync --extra anthropic

# Or with pip
pip install -e ".[anthropic]"

# Configure
cp .env.example .env
# Edit .env → set your ANTHROPIC_API_KEY

# Run
deep-browser-agent
```

## Usage

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

## Multi-Provider Support

Use any LLM provider via `--model provider:model` or the `AGENT_MODEL` env var:

| Provider | Example | Env Var |
|----------|---------|---------|
| **Anthropic** | `anthropic:claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| **OpenAI** | `openai:gpt-4o` | `OPENAI_API_KEY` |
| **OpenRouter** | `openrouter:deepseek/deepseek-chat-v3` | `OPENROUTER_API_KEY` |
| **Ollama** | `ollama:llama3.3` | `OLLAMA_BASE_URL` |
| **Azure** | `azure:gpt-4o` | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` |
| **Google** | `google:gemini-2.5-pro` | `GOOGLE_API_KEY` |

```bash
# Install the provider you need
uv sync --extra anthropic    # or openai, google, ollama
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

UIDs change after every navigation — the agent always takes a fresh snapshot before interacting. This is handled automatically by the system prompt and skills.

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

## Browser Skills (built-in)

High-level composite skills that guide the agent through common workflows:

| Skill | Purpose |
|-------|---------|
| `snapshot_and_plan` | Plan multi-step workflows using UID-based approach |
| `form_fill_guide` | Step-by-step form filling with correct UID patterns |
| `extract_data_js` | Generate JS snippets for data extraction |
| `handle_bot_detection` | Advice for CAPTCHA/bot protection (with mitigations) |
| `debug_page` | Comprehensive page debugging checklist |
| `multi_tab_workflow` | Multi-tab management patterns |
| `performance_audit_guide` | Full performance audit workflow |

## Connecting to an Existing Chrome

To bypass bot detection or use your logged-in sessions:

```bash
# Terminal 1: Launch Chrome with debug port
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Terminal 2: Connect the agent
deep-browser-agent --browser-url http://localhost:9222
```

## Project Structure

```
src/deep_browser_agent/
├── __init__.py        # Public API
├── config.py          # AgentConfig
├── providers.py       # Multi-provider LLM support
├── agent.py           # Core: DeepAgent + MCP bridge
├── skills.py          # Battle-tested browser skills
└── cli.py             # Interactive terminal UI
```

## Docs

- [GUIDE.md](GUIDE.md) — Detailed Turkish guide with real test results
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture and data flow

## License

MIT
