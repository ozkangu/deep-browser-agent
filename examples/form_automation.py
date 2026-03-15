"""Example: Automated form filling and submission."""

import asyncio

from chromancer.agent import BrowserAgentSession
from chromancer.config import AgentConfig


async def main():
    config = AgentConfig(headless=False)

    async with BrowserAgentSession(config=config) as session:
        result = await session.invoke(
            "Go to https://httpbin.org/forms/post. "
            "Fill the form with these values:\n"
            "- Customer name: John Doe\n"
            "- Telephone: 555-1234\n"
            "- E-mail: john@example.com\n"
            "- Size: Medium\n"
            "- Topping: Cheese\n"
            "- Delivery time: 11:45\n"
            "- Instructions: Ring the doorbell\n\n"
            "Then submit the form and take a screenshot of the result."
        )

        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                print(msg.content)
                break


if __name__ == "__main__":
    asyncio.run(main())
