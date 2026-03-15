"""FastAPI server — exposes Deep Browser Agent as an HTTP API.

The frontend chat popup sends:
  - message: what the user wants to do
  - url: the page the user is currently on
  - cookies (optional): user's session cookies for authenticated pages

The server spins up a headless Chrome, injects the session, navigates
to the target URL, and executes the agent's actions.
"""

from __future__ import annotations

import asyncio
import base64
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from deep_browser_agent.agent import BrowserAgentSession
from deep_browser_agent.config import AgentConfig


# ── Request / Response models ──────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., description="User instruction (e.g., 'fill the form')")
    url: str = Field(..., description="Current page URL where the action should happen")
    cookies: list[dict[str, Any]] | None = Field(
        None,
        description="Browser cookies for session auth. "
        "Each dict: {name, value, domain, path, ...}",
    )
    config: dict[str, Any] | None = Field(
        None,
        description="Optional AgentConfig overrides (model, headless, etc.)",
    )


class ChatResponse(BaseModel):
    reply: str
    screenshot: str | None = Field(None, description="Base64-encoded PNG screenshot")
    success: bool = True
    actions_taken: list[str] = Field(default_factory=list)


# ── Session manager ───────────────────────────────────────────────

class TargetedBrowserSession:
    """Wraps BrowserAgentSession with URL targeting and cookie injection."""

    def __init__(self, config: AgentConfig):
        self._config = config

    async def execute(self, request: ChatRequest) -> ChatResponse:
        """Execute an agent task on a specific URL with optional session cookies."""

        # Build the instruction with URL context
        instruction_parts = [
            f"Navigate to {request.url}.",
        ]

        # If cookies provided, inject them via JS before interacting
        if request.cookies:
            cookie_script = self._build_cookie_script(request.cookies)
            instruction_parts.append(
                f"First, run this JavaScript to set session cookies:\n"
                f"evaluate_script(function=\"{cookie_script}\")\n"
                f"Then reload the page with navigate_page(type='reload')."
            )

        instruction_parts.append(
            f"Then do the following: {request.message}"
        )
        instruction_parts.append(
            "After completing the task, take a screenshot to show the result."
        )

        full_instruction = "\n".join(instruction_parts)

        async with BrowserAgentSession(config=self._config) as session:
            result = await session.invoke(full_instruction)

            # Extract the agent's reply and any screenshots
            reply = ""
            screenshot = None
            actions = []

            for msg in result.get("messages", []):
                # Collect tool calls as actions
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        actions.append(f"{tc['name']}({tc.get('args', {})})")

                # Get the final AI reply
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

            return ChatResponse(
                reply=reply,
                screenshot=screenshot,
                success=True,
                actions_taken=actions[-10:],  # last 10 actions
            )

    @staticmethod
    def _build_cookie_script(cookies: list[dict]) -> str:
        """Build a JS function that sets cookies."""
        set_statements = []
        for c in cookies:
            name = c.get("name", "")
            value = c.get("value", "")
            domain = c.get("domain", "")
            path = c.get("path", "/")
            set_statements.append(
                f"document.cookie = '{name}={value}; path={path}; domain={domain}';"
            )
        joined = " ".join(set_statements)
        return f"() => {{ {joined} return 'cookies set'; }}"


# ── FastAPI app ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown."""
    yield


app = FastAPI(
    title="Deep Browser Agent API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Execute a browser task on the specified URL."""
    try:
        config = AgentConfig.from_env()
        config.headless = True
        config.isolated = True

        # Apply any config overrides from request
        if request.config:
            for key, value in request.config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        session = TargetedBrowserSession(config)
        return await session.execute(request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    """Run the server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8877)


if __name__ == "__main__":
    main()
