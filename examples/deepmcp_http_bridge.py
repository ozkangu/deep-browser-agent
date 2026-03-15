"""Example: Using DeepMCPAgent with Chrome DevTools MCP over HTTP bridge.

This approach uses an HTTP proxy to expose chrome-devtools-mcp to
DeepMCPAgent (which prefers HTTP/SSE transport).

Prerequisites:
    pip install "deepmcpagent[deep]" mcp-proxy
    npx -y chrome-devtools-mcp@latest  # verify it works

Step 1: Start the MCP proxy (converts stdio → HTTP):
    npx @anthropic/mcp-proxy --port 3100 -- npx -y chrome-devtools-mcp@latest

Step 2: Run this script.
"""

import asyncio


async def main():
    try:
        from deepmcpagent import HTTPServerSpec, build_deep_agent
    except ImportError:
        print("Install deepmcpagent: pip install 'deepmcpagent[deep]'")
        return

    servers = {
        "chrome-devtools": HTTPServerSpec(
            url="http://127.0.0.1:3100/mcp",
            transport="http",
        ),
    }

    graph, _ = await build_deep_agent(
        servers=servers,
        model="anthropic:claude-sonnet-4-20250514",
        instructions=(
            "You are a browser automation agent with Chrome DevTools tools. "
            "Navigate pages, fill forms, take screenshots, and debug web apps."
        ),
    )

    result = await graph.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Go to https://example.com, take a screenshot, "
                        "and describe the page content."
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
