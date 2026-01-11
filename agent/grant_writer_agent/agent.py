"""
Grant Writer Agent

An autonomous AI agent that writes complete grant applications by:
1. Researching grant requirements
2. Gathering organization context
3. Finding supporting statistics
4. Drafting each section
5. Self-evaluating and revising
6. Checking compliance
7. Returning complete application
"""

import asyncio
import os
from typing import Any, Optional
from datetime import datetime

from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    UserMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from .tools import ALL_TOOLS

console = Console()


# =============================================================================
# GRANT WRITER AGENT
# =============================================================================

SYSTEM_PROMPT = """You are an expert grant writer agent. Your job is to write complete, high-quality grant applications autonomously.

## Your Process:

1. **RESEARCH PHASE**
   - Use `fetch_grant_details` to understand the grant requirements
   - Use `get_org_profile` to understand the applicant organization
   - Use `search_statistics` to find data for the statement of need
   - Use `web_search` to find additional supporting information

2. **WRITING PHASE**
   For each required section, write professional grant content that:
   - Uses specific data with citations
   - Aligns with funder priorities
   - Demonstrates organizational capacity
   - Follows best practices for federal grants

3. **EVALUATION PHASE**
   - Use `evaluate_section` to score each section you write
   - If a section scores below 8/10, revise it with the feedback
   - Continue revising until quality threshold is met

4. **COMPLIANCE PHASE**
   - Use `check_compliance` to verify all requirements are met
   - Address any compliance issues before finalizing

## Required Sections:
1. Executive Summary (500 words max)
2. Statement of Need (1500 words max)
3. Project Description (3000 words max)
4. Goals & Objectives (1000 words max)
5. Evaluation Plan (1500 words max)
6. Budget Narrative (1500 words max)
7. Sustainability Plan (1000 words max)

## Writing Guidelines:
- Use active voice and clear, concise language
- Include specific, cited statistics (not vague claims)
- Connect local data to national context
- Show organizational capacity and track record
- Emphasize innovation and evidence-based approaches
- Address sustainability from the start

## Output Format:
After completing all sections, output the complete application in a clearly formatted document with all sections clearly labeled.

START NOW - Begin by researching the grant and organization, then systematically write each section."""


class GrantWriterAgent:
    """Autonomous agent for writing complete grant applications."""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        # Create MCP server with all tools
        self.tools_server = create_sdk_mcp_server(
            name="grant-tools",
            version="1.0.0",
            tools=ALL_TOOLS
        )

        # Configure agent options
        self.options = ClaudeAgentOptions(
            model="claude-sonnet-4-20250514",
            system_prompt=SYSTEM_PROMPT,
            max_turns=50,  # Allow enough turns for complete application
            mcp_servers={"grants": self.tools_server},
            allowed_tools=[
                "mcp__grants__fetch_grant_details",
                "mcp__grants__search_grants",
                "mcp__grants__get_org_profile",
                "mcp__grants__search_statistics",
                "mcp__grants__web_search",
                "mcp__grants__evaluate_section",
                "mcp__grants__check_compliance",
            ]
        )

        self.conversation_history = []
        self.sections_written = {}
        self.total_tool_calls = 0

    async def write_grant_application(
        self,
        grant_id: str,
        user_id: str,
        project_title: str,
        project_summary: str
    ) -> dict[str, Any]:
        """
        Write a complete grant application autonomously.

        Args:
            grant_id: The grant program ID to apply for
            user_id: The user/organization ID
            project_title: Title of the proposed project
            project_summary: Brief summary of what the project will do

        Returns:
            Dictionary containing the complete application with all sections
        """
        start_time = datetime.now()

        console.print(Panel.fit(
            f"[bold cyan]Grant Writer Agent[/bold cyan]\n\n"
            f"Grant: {grant_id}\n"
            f"Project: {project_title}",
            title="🚀 Starting Grant Application",
            border_style="cyan"
        ))

        # Construct the initial prompt
        initial_prompt = f"""Write a complete grant application for:

**Grant Program ID:** {grant_id}
**Organization ID:** {user_id}

**Proposed Project:**
Title: {project_title}

Summary: {project_summary}

Begin by researching the grant requirements and organization profile, then write all required sections. Evaluate each section and revise as needed until quality threshold is met. Finally, check compliance and output the complete application."""

        # Run the agent loop
        async with ClaudeSDKClient(options=self.options) as client:
            await client.query(initial_prompt)

            final_response = ""
            current_section = ""

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Agent working...", total=None)

                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                final_response += block.text
                                # Update progress based on content
                                if "Statement of Need" in block.text:
                                    progress.update(task, description="[cyan]Writing Statement of Need...")
                                elif "Project Description" in block.text:
                                    progress.update(task, description="[cyan]Writing Project Description...")
                                elif "Evaluation" in block.text:
                                    progress.update(task, description="[cyan]Evaluating sections...")

                            elif isinstance(block, ToolUseBlock):
                                self.total_tool_calls += 1
                                progress.update(task, description=f"[yellow]Using tool: {block.name}...")
                                console.print(f"  [dim]→ {block.name}[/dim]")

        elapsed = (datetime.now() - start_time).total_seconds()

        # Extract sections from final response
        application = {
            "grant_id": grant_id,
            "user_id": user_id,
            "project_title": project_title,
            "project_summary": project_summary,
            "generated_at": datetime.now().isoformat(),
            "generation_time_seconds": elapsed,
            "tool_calls": self.total_tool_calls,
            "full_application": final_response,
            "sections": self._extract_sections(final_response)
        }

        # Print summary
        console.print(Panel.fit(
            f"[bold green]Application Complete![/bold green]\n\n"
            f"⏱️  Time: {elapsed:.1f} seconds\n"
            f"🔧 Tool calls: {self.total_tool_calls}\n"
            f"📄 Sections: {len(application['sections'])}",
            title="✅ Grant Application Generated",
            border_style="green"
        ))

        return application

    def _extract_sections(self, content: str) -> dict[str, str]:
        """Extract individual sections from the full application."""
        sections = {}
        section_markers = [
            ("executive_summary", "Executive Summary"),
            ("statement_of_need", "Statement of Need"),
            ("project_description", "Project Description"),
            ("goals_objectives", "Goals and Objectives"),
            ("evaluation_plan", "Evaluation Plan"),
            ("budget_narrative", "Budget Narrative"),
            ("sustainability_plan", "Sustainability Plan"),
        ]

        for key, marker in section_markers:
            # Try to find the section in the content
            start_patterns = [
                f"## {marker}",
                f"# {marker}",
                f"**{marker}**",
                f"{marker}:",
            ]

            for pattern in start_patterns:
                if pattern in content:
                    start_idx = content.find(pattern)
                    # Find the end (next section or end of content)
                    end_idx = len(content)
                    for _, next_marker in section_markers:
                        if next_marker != marker:
                            for next_pattern in start_patterns:
                                next_pattern = next_pattern.replace(marker, next_marker)
                                if next_pattern in content[start_idx + len(pattern):]:
                                    potential_end = content.find(next_pattern, start_idx + len(pattern))
                                    if potential_end > start_idx and potential_end < end_idx:
                                        end_idx = potential_end

                    section_content = content[start_idx:end_idx].strip()
                    sections[key] = section_content
                    break

        return sections


# =============================================================================
# CLI INTERFACE
# =============================================================================

async def run_agent(
    grant_id: str,
    project_title: str,
    project_summary: str,
    user_id: str = "demo_user"
) -> dict[str, Any]:
    """Run the grant writer agent."""
    agent = GrantWriterAgent()
    return await agent.write_grant_application(
        grant_id=grant_id,
        user_id=user_id,
        project_title=project_title,
        project_summary=project_summary
    )


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Grant Writer Agent")
    parser.add_argument("--grant-id", default="hrsa_rural_health", help="Grant program ID")
    parser.add_argument("--title", default="Rural Health Access Expansion", help="Project title")
    parser.add_argument("--summary", default="Expand primary care services to underserved rural communities through telehealth and mobile health units.", help="Project summary")
    parser.add_argument("--user-id", default="demo_user", help="User/organization ID")
    parser.add_argument("--output", help="Output file path (optional)")

    args = parser.parse_args()

    console.print("\n[bold cyan]🤖 Grant Writer Agent[/bold cyan]\n")

    result = asyncio.run(run_agent(
        grant_id=args.grant_id,
        project_title=args.title,
        project_summary=args.summary,
        user_id=args.user_id
    ))

    # Print the full application
    console.print("\n")
    console.print(Panel(
        Markdown(result["full_application"]),
        title="📄 Complete Grant Application",
        border_style="blue"
    ))

    # Save to file if requested
    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"\n[green]Saved to {args.output}[/green]")


if __name__ == "__main__":
    main()
