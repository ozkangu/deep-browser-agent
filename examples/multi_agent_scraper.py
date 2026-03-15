"""Example: Multi-agent setup — a coordinator delegates browser tasks to a sub-agent.

This demonstrates DeepAgent's subagent spawning combined with Chrome MCP tools.
"""

import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

from chromancer.config import AgentConfig
from chromancer.providers import create_model, get_provider_from_string
from chromancer.skills import get_browser_skills


async def main():
    config = AgentConfig(headless=True)

    async with MultiServerMCPClient(
        {
            "chrome-devtools": {
                "command": config.chrome_mcp_command,
                "args": config.get_mcp_args(),
                "transport": "stdio",
            }
        }
    ) as client:
        mcp_tools = await client.get_tools()
        all_tools = mcp_tools + get_browser_skills()
        model = create_model(get_provider_from_string(config.model))

        try:
            from deepagents import create_deep_agent

            # DeepAgent's built-in `task` tool enables sub-agent spawning.
            # The main agent can delegate browser tasks to a focused sub-agent.
            agent = create_deep_agent(
                model=model,
                tools=all_tools,
                system_prompt=(
                    "You are a research coordinator. "
                    "Use your browser tools to scrape data from multiple pages. "
                    "Use the task tool to spawn sub-agents for parallel work. "
                    "Combine results into a final report."
                ),
            )
        except ImportError:
            from langgraph.prebuilt import create_react_agent

            agent = create_react_agent(model=model, tools=all_tools)

        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Research the top 3 Python web frameworks. "
                            "For each one, navigate to its homepage, take a screenshot, "
                            "and extract the main tagline. Compile a comparison."
                        ),
                    }
                ]
            }
        )

        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                print(msg.content)
                break


if __name__ == "__main__":
    asyncio.run(main())
