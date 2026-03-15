"""Interactive CLI for Deep Browser Agent."""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from deep_browser_agent.agent import BrowserAgentSession
from deep_browser_agent.config import AgentConfig
from deep_browser_agent.providers import PROVIDER_PRESETS

console = Console()


async def interactive_loop(config: AgentConfig):
    """Run an interactive chat loop with the browser agent."""
    console.print(
        Panel(
            "[bold]Deep Browser Agent[/bold]\n"
            "Browser automation via DeepAgent + Chrome DevTools MCP\n\n"
            "Commands:\n"
            "  [cyan]quit[/cyan] / [cyan]exit[/cyan]   — End session\n"
            "  [cyan]screenshot[/cyan]     — Screenshot current page\n"
            "  [cyan]snapshot[/cyan]       — DOM snapshot (a11y tree)\n"
            "  [cyan]pages[/cyan]          — List open tabs\n"
            "  [cyan]url <url>[/cyan]      — Navigate to URL\n\n"
            f"Model: [yellow]{config.model}[/yellow]  "
            f"Headless: [yellow]{config.headless}[/yellow]",
            title="Welcome",
            border_style="blue",
        )
    )

    async with BrowserAgentSession(config=config) as session:
        console.print("[green]Agent ready. Chrome DevTools MCP connected.[/green]\n")

        while True:
            try:
                user_input = console.input("[bold cyan]You>[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                break

            # Shortcuts
            if user_input.lower() == "screenshot":
                user_input = "Take a screenshot of the current page and describe what you see."
            elif user_input.lower() == "snapshot":
                user_input = "Take a snapshot (a11y tree) and show me all interactive elements with their UIDs."
            elif user_input.lower() == "pages":
                user_input = "List all open browser pages."
            elif user_input.lower().startswith("url "):
                url = user_input[4:].strip()
                user_input = f"Navigate to {url}, take a screenshot, and describe the page."

            console.print("[dim]Thinking...[/dim]")

            try:
                result = await session.invoke(user_input)
                messages = result.get("messages", [])

                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.type == "ai" and msg.content:
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        console.print()
                        console.print(
                            Panel(Markdown(content), title="Agent", border_style="green")
                        )
                        break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        console.print("\n[dim]Session ended.[/dim]")


def print_providers():
    """Print available provider presets."""
    table = Table(title="Provider Presets")
    table.add_column("Preset", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Model")
    for name, cfg in PROVIDER_PRESETS.items():
        table.add_row(name, cfg["provider"], cfg["model"])
    console.print(table)
    console.print("\nOr use provider:model format: [yellow]--model openrouter:deepseek/deepseek-chat-v3[/yellow]")


def main():
    """Entry point for the CLI."""
    config = AgentConfig.from_env()
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        console.print(
            "Usage: deep-browser-agent [options]\n\n"
            "Options:\n"
            "  --model <provider:model>  LLM to use (e.g., anthropic:claude-sonnet-4-20250514)\n"
            "  --headless               Run Chrome in headless mode\n"
            "  --slim                   Only 3 essential MCP tools\n"
            "  --browser-url <url>      Connect to running Chrome\n"
            "  --providers              List available provider presets\n"
            "  --api-key <key>          Override API key\n"
            "  --base-url <url>         Override base URL (OpenRouter, Ollama, etc.)\n"
        )
        return

    if "--providers" in args:
        print_providers()
        return

    if "--headless" in args:
        config.headless = True
    if "--slim" in args:
        config.slim_mode = True

    for i, arg in enumerate(args):
        if arg == "--model" and i + 1 < len(args):
            config.model = args[i + 1]
        elif arg == "--browser-url" and i + 1 < len(args):
            config.browser_url = args[i + 1]
        elif arg == "--api-key" and i + 1 < len(args):
            config.api_key = args[i + 1]
        elif arg == "--base-url" and i + 1 < len(args):
            config.base_url = args[i + 1]

    asyncio.run(interactive_loop(config))


if __name__ == "__main__":
    main()
