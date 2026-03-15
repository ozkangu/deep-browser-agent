"""Example: Basic browser navigation and screenshot."""

import asyncio

from deep_browser_agent.agent import BrowserAgentSession
from deep_browser_agent.config import AgentConfig


async def main():
    config = AgentConfig(headless=False)

    async with BrowserAgentSession(config=config) as session:
        # Navigate and take screenshot
        result = await session.invoke(
            "Navigate to https://news.ycombinator.com, take a screenshot, "
            "and tell me the top 5 stories on the front page."
        )

        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                print(msg.content)
                break


if __name__ == "__main__":
    asyncio.run(main())
