"""Configuration for Chrome Deep Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AgentConfig:
    """Agent configuration with sensible defaults."""

    # LLM settings — use provider:model format or preset name
    # Examples: "anthropic:claude-sonnet-4-20250514", "openrouter:deepseek/deepseek-chat-v3",
    #           "ollama:llama3.3", "azure:gpt-4o", "google:gemini-2.5-pro"
    model: str = "anthropic:claude-sonnet-4-20250514"
    temperature: float = 0.0
    api_key: str | None = None       # Override provider API key
    base_url: str | None = None      # Override base URL (for OpenRouter, Ollama, etc.)

    # Chrome DevTools MCP settings
    chrome_mcp_command: str = "npx"
    chrome_mcp_args: list[str] = field(default_factory=lambda: ["-y", "chrome-devtools-mcp@latest"])
    headless: bool = False
    slim_mode: bool = False
    isolated: bool = True            # Temp profile, auto-cleanup
    browser_url: str | None = None   # Connect to running Chrome
    chrome_channel: str | None = None
    viewport: str = "1920x1080"
    no_usage_stats: bool = True

    # Agent behavior
    system_prompt: str | None = None
    max_iterations: int = 50

    def get_mcp_args(self) -> list[str]:
        """Build the full argument list for chrome-devtools-mcp."""
        args = list(self.chrome_mcp_args)
        if self.headless:
            args.append("--headless")
        if self.slim_mode:
            args.append("--slim")
        if self.isolated:
            args.append("--isolated")
        if self.no_usage_stats:
            args.append("--no-usage-statistics")
        if self.viewport:
            args.extend(["--viewport", self.viewport])
        if self.browser_url:
            args.extend(["--browserUrl", self.browser_url])
        if self.chrome_channel:
            args.extend(["--channel", self.chrome_channel])
        return args

    @classmethod
    def from_env(cls) -> AgentConfig:
        """Create config from environment variables."""
        provider = os.getenv("AGENT_MODEL_PROVIDER", "anthropic")
        model_name = os.getenv("AGENT_MODEL_NAME", "claude-sonnet-4-20250514")
        model = os.getenv("AGENT_MODEL", f"{provider}:{model_name}")

        return cls(
            model=model,
            api_key=os.getenv("AGENT_API_KEY"),
            base_url=os.getenv("AGENT_BASE_URL"),
            headless=os.getenv("CHROME_HEADLESS", "false").lower() == "true",
            slim_mode=os.getenv("CHROME_SLIM", "false").lower() == "true",
            isolated=os.getenv("CHROME_ISOLATED", "true").lower() == "true",
            browser_url=os.getenv("CHROME_BROWSER_URL"),
            chrome_channel=os.getenv("CHROME_CHANNEL"),
            viewport=os.getenv("CHROME_VIEWPORT", "1920x1080"),
        )
