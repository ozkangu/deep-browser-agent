"""Example: Run a performance audit on a website."""

import asyncio

from chromancer.agent import BrowserAgentSession
from chromancer.config import AgentConfig


async def main():
    config = AgentConfig(headless=True)

    async with BrowserAgentSession(config=config) as session:
        result = await session.invoke(
            "Run a full performance audit on https://example.com. "
            "Use the performance_audit_workflow skill first to plan, "
            "then execute each step. Report the findings."
        )

        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                print(msg.content)
                break


if __name__ == "__main__":
    asyncio.run(main())
