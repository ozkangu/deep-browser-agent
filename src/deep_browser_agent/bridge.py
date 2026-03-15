"""CDP Bridge — agent controls the user's actual browser via Chrome DevTools Protocol.

Unlike the headless server.py (separate Chrome) or DOM bridge approaches, this mode:
1. Connects to the user's running Chrome via --remote-debugging-port (CDP)
2. Finds and selects the tab the user is currently on
3. Agent executes MCP tools (fill, click, etc.) directly on the real visible page
4. User sees everything happening in their own browser in real-time

Compatible with future Chrome WebMCP migration since both use CDP as transport.

Setup:
    # Terminal 1: Launch Chrome with debug port
    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222

    # Terminal 2: Start the bridge server
    deep-browser-agent-bridge
"""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from deep_browser_agent.agent import DEFAULT_SYSTEM_PROMPT, BrowserAgentSession
from deep_browser_agent.config import AgentConfig


# ── Models ─────────────────────────────────────────────────────────

class BridgeRequest(BaseModel):
    message: str = Field(..., description="User instruction")
    url: str = Field(..., description="Current page URL (for tab matching)")
    session_id: str | None = Field(None, description="Session ID for multi-turn conversation")
    config: dict[str, Any] | None = Field(None, description="Optional AgentConfig overrides")


class BridgeResponse(BaseModel):
    reply: str
    session_id: str
    screenshot: str | None = Field(None, description="Base64 PNG if agent took a screenshot")
    actions_taken: list[str] = Field(default_factory=list)
    success: bool = True


class CloseRequest(BaseModel):
    session_id: str


# ── CDP system prompt extension ────────────────────────────────────

CDP_PROMPT_PREFIX = """\
You are connected to the user's REAL browser via Chrome DevTools Protocol.
The user can see every action you perform in their browser window.

## Tab Selection
- The user tells you which URL they are on. Use `list_pages` to find the matching tab,
  then `select_page(index=N)` to switch to it.
- Match by URL substring — the exact URL may differ slightly.
- Once on the correct tab, use `take_snapshot` before interacting.

## Important
- Do NOT navigate away from the current page unless the user explicitly asks.
- Do NOT close any tabs.
- Be precise and efficient — the user is watching.

"""


# ── CDP Session ────────────────────────────────────────────────────

class CDPSession:
    """Persistent agent session connected to user's Chrome via CDP."""

    def __init__(self, session_id: str, agent_session: BrowserAgentSession):
        self.session_id = session_id
        self.agent_session = agent_session
        self.messages: list = []
        self.last_active: float = time.time()
        self._tab_selected: bool = False

    async def execute(self, message: str, url: str) -> BridgeResponse:
        self.last_active = time.time()

        # Build user instruction
        parts = []
        if not self._tab_selected:
            parts.append(
                f"Find and select the browser tab with URL matching '{url}' "
                f"using list_pages and select_page. Then take a snapshot."
            )
            self._tab_selected = True

        parts.append(message)
        full_message = "\n".join(parts)

        # Add user message to conversation history
        self.messages.append({"role": "user", "content": full_message})

        # Invoke agent with full conversation history
        result = await self.agent_session.agent.ainvoke(
            {"messages": self.messages}
        )

        # Update history from result (includes tool calls, tool responses, etc.)
        self.messages = result.get("messages", self.messages)

        # Extract reply and metadata from result messages
        reply = ""
        screenshot = None
        actions = []

        for msg in result.get("messages", []):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    actions.append(f"{tc['name']}({tc.get('args', {})})")

            if hasattr(msg, "content") and getattr(msg, "type", None) == "ai":
                if isinstance(msg.content, str) and msg.content:
                    reply = msg.content
                elif isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                reply = block["text"]
                            elif block.get("type") == "image":
                                screenshot = block.get("data")

        return BridgeResponse(
            reply=reply,
            session_id=self.session_id,
            screenshot=screenshot,
            actions_taken=actions[-10:],
            success=True,
        )


class SessionStore:
    """In-memory session store with timeout-based cleanup."""

    def __init__(self, timeout: int = 600):
        self._sessions: dict[str, CDPSession] = {}
        self._timeout = timeout
        self._cleanup_task: asyncio.Task | None = None

    async def start(self):
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
        for session in list(self._sessions.values()):
            await session.agent_session.__aexit__(None, None, None)
        self._sessions.clear()

    async def get_or_create(
        self, session_id: str | None, config: AgentConfig
    ) -> CDPSession:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        sid = session_id or str(uuid.uuid4())
        agent_session = BrowserAgentSession(config=config)
        await agent_session.__aenter__()

        cdp_session = CDPSession(sid, agent_session)
        self._sessions[sid] = cdp_session
        return cdp_session

    async def remove(self, session_id: str) -> bool:
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            await session.agent_session.__aexit__(None, None, None)
            return True
        return False

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(60)
            now = time.time()
            expired = [
                sid for sid, s in self._sessions.items()
                if now - s.last_active > self._timeout
            ]
            for sid in expired:
                await self.remove(sid)


# ── FastAPI app ────────────────────────────────────────────────────

store = SessionStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.start()
    yield
    await store.stop()


app = FastAPI(
    title="Deep Browser Agent — CDP Bridge",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/bridge", response_model=BridgeResponse)
async def bridge(request: BridgeRequest):
    """Execute agent actions on the user's actual browser via CDP."""
    try:
        config = AgentConfig.from_env()

        # CDP bridge: connect to user's Chrome, non-headless, non-isolated
        config.headless = False
        config.isolated = False
        if not config.browser_url:
            config.browser_url = "http://localhost:9222"

        # Prepend CDP-specific instructions to the system prompt
        config.system_prompt = CDP_PROMPT_PREFIX + DEFAULT_SYSTEM_PROMPT

        # Apply optional overrides from request
        if request.config:
            for key, value in request.config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        session = await store.get_or_create(request.session_id, config)
        return await session.execute(request.message, request.url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bridge/close")
async def close_session(request: CloseRequest):
    """Close a session and free resources."""
    if await store.remove(request.session_id):
        return {"status": "closed", "session_id": request.session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "cdp-bridge",
        "active_sessions": store.active_count,
    }


def main():
    """Run the CDP bridge server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8878)


if __name__ == "__main__":
    main()


# ── Frontend JS snippet (for reference) ───────────────────────────
FRONTEND_SNIPPET = """\
// === deep-browser-agent CDP bridge — paste in your frontend ===
// Unlike the DOM bridge, this requires NO DOM snapshotting on the frontend.
// The backend connects to Chrome directly via CDP and handles everything.

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
// const agent = new DeepBrowserBridge('http://localhost:8878');
// const data = await agent.chat('Fill the registration form with test data');
// console.log(data.reply);          // Agent's text response
// console.log(data.actions_taken);  // What MCP tools were called
// console.log(data.screenshot);     // Base64 PNG if agent took a screenshot
// await agent.close();              // Clean up when done
""";
