#!/usr/bin/env python3
"""Test the Grant Writer Agent."""

import asyncio
import os
import sys

# Add the agent package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


async def test_agent():
    """Test the grant writer agent with a sample application."""
    from grant_writer_agent.agent import GrantWriterAgent

    console.print(Panel.fit(
        "[bold cyan]Grant Writer Agent Test[/bold cyan]\n\n"
        "Testing autonomous grant application generation...",
        border_style="cyan"
    ))

    # Create the agent
    agent = GrantWriterAgent()

    # Test with a rural health grant
    result = await agent.write_grant_application(
        grant_id="hrsa_rural_health",
        user_id="demo_user",
        project_title="Harlan County Telehealth Expansion Initiative",
        project_summary="""
        This project will expand telehealth services to 5,000 underserved residents
        in Harlan County, Kentucky by establishing 3 new telehealth kiosks in
        community locations, hiring 2 telehealth coordinators, and providing
        training to 15 local healthcare providers. The initiative addresses critical
        healthcare access barriers in this rural Appalachian community where the
        nearest hospital is 45 miles away.
        """
    )

    # Print results
    console.print("\n")
    console.print(Panel(
        f"[green]Generation Time:[/green] {result['generation_time_seconds']:.1f}s\n"
        f"[green]Tool Calls:[/green] {result['tool_calls']}\n"
        f"[green]Sections Generated:[/green] {len(result['sections'])}",
        title="📊 Results Summary",
        border_style="green"
    ))

    # Print the full application
    console.print("\n")
    console.print(Panel(
        Markdown(result["full_application"][:5000] + "\n\n...[truncated for display]..."),
        title="📄 Generated Application (Preview)",
        border_style="blue"
    ))

    # Save to file
    import json
    output_file = "test_output.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    console.print(f"\n[green]Full output saved to {output_file}[/green]")

    return result


if __name__ == "__main__":
    asyncio.run(test_agent())
