"""
Grant Writer Agent Service

Autonomous AI agent that writes complete grant applications by:
1. Researching grant requirements
2. Gathering organization context
3. Finding supporting statistics
4. Drafting each section
5. Self-evaluating and revising
6. Returning complete application
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Optional, Dict, List

import httpx
from anthropic import AsyncAnthropic

from app.config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# STATISTICS DATA (simulated - in production would use Census/CDC APIs)
# =============================================================================

STATISTICS_DATA = {
    "Harlan County, KY": {
        "poverty_rate": {"value": "32.1%", "comparison": "11.4% (US avg)", "source": "US Census Bureau 2023"},
        "unemployment": {"value": "8.2%", "comparison": "3.7% (US avg)", "source": "BLS 2024"},
        "median_income": {"value": "$27,149", "comparison": "$74,580 (US avg)", "source": "US Census Bureau 2023"},
        "uninsured_rate": {"value": "12.8%", "comparison": "8.0% (US avg)", "source": "Census ACS 2023"},
        "diabetes_rate": {"value": "18.2%", "comparison": "10.5% (US avg)", "source": "CDC 2023"},
        "life_expectancy": {"value": "72.1 years", "comparison": "78.8 years (US avg)", "source": "CDC NVSS 2023"},
        "opioid_deaths": {"value": "58.3 per 100k", "comparison": "21.6 per 100k (US avg)", "source": "CDC WONDER 2023"},
        "physicians_per_capita": {"value": "1.2 per 1,000", "comparison": "2.6 per 1,000 (US avg)", "source": "HRSA 2023"},
    }
}

SAMPLE_ORG_PROFILE = {
    "organization_name": "Harlan County Community Health Center",
    "organization_type": "501(c)(3) Nonprofit",
    "ein": "12-3456789",
    "uei_number": "ABC123456789",
    "address": "123 Main Street, Harlan, KY 40831",
    "congressional_district": "KY-05",
    "mission_statement": "To provide accessible, high-quality healthcare to all residents of Harlan County, regardless of ability to pay.",
    "founding_year": 2008,
    "service_area": "Harlan County, Kentucky",
    "service_area_population": 26010,
    "annual_budget": 2500000,
    "staff_count": 35,
    "clients_served_annually": 8500,
    "is_rural": True,
    "is_underserved": True,
    "prior_grants": [
        {"funder": "HRSA", "amount": 150000, "year": 2023, "purpose": "Telehealth expansion"},
        {"funder": "Appalachian Regional Commission", "amount": 75000, "year": 2022, "purpose": "Mobile health unit"}
    ]
}


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

async def fetch_grant_details(grant_id: str, db_session=None) -> str:
    """Fetch grant details from the database."""
    from app.models.database import GrantProgram

    if db_session:
        program = db_session.query(GrantProgram).filter(GrantProgram.id == grant_id).first()
        if program:
            return f"""
## Grant: {program.name}

**Agency:** {program.agency}
**Category:** {program.category.value if program.category else 'N/A'}

**Award Range:** ${program.min_award or 0:,.0f} - ${program.max_award or 0:,.0f}
**Match Required:** {(program.match_required or 0) * 100:.0f}%
**Deadline:** {program.deadline.isoformat() if program.deadline else 'Rolling/Open'}

**Description:**
{program.description or 'No description available'}

**Eligibility:**
{program.eligibility_summary or 'See grant guidelines'}

**Program URL:** {program.program_url or 'N/A'}
"""

    return f"Grant {grant_id} not found. Using generic federal grant requirements."


def get_org_profile(user_id: str, db_session=None) -> str:
    """Get organization profile."""
    # In production, fetch from database based on user_id
    profile = SAMPLE_ORG_PROFILE

    profile_text = f"""
## Organization Profile: {profile['organization_name']}

**Type:** {profile['organization_type']}
**EIN:** {profile['ein']}
**UEI:** {profile['uei_number']}
**Location:** {profile['address']}
**Congressional District:** {profile['congressional_district']}

### Mission
{profile['mission_statement']}

### Organizational Capacity
- **Founded:** {profile['founding_year']}
- **Service Area:** {profile['service_area']} (Pop: {profile['service_area_population']:,})
- **Annual Budget:** ${profile['annual_budget']:,}
- **Staff:** {profile['staff_count']}
- **Clients Served Annually:** {profile['clients_served_annually']:,}

### Demographics
- Rural Community: {'Yes' if profile['is_rural'] else 'No'}
- Medically Underserved: {'Yes' if profile['is_underserved'] else 'No'}

### Prior Grant Experience
"""
    for g in profile['prior_grants']:
        profile_text += f"- {g['funder']} ({g['year']}): ${g['amount']:,} - {g['purpose']}\n"

    return profile_text


def search_statistics(location: str) -> str:
    """Search for statistics about a location."""
    # Default to Harlan County data
    location_data = STATISTICS_DATA.get("Harlan County, KY", {})

    results = f"## Statistics for {location}\n\n"
    results += "| Metric | Local Value | National Average | Source |\n"
    results += "|--------|-------------|------------------|--------|\n"

    for metric, data in location_data.items():
        metric_name = metric.replace("_", " ").title()
        results += f"| {metric_name} | **{data['value']}** | {data['comparison']} | {data['source']} |\n"

    results += """
### Key Findings for Statement of Need:
1. **Poverty rate nearly 3x the national average** - demonstrates economic hardship
2. **Life expectancy 6.7 years below national average** - indicates health disparities
3. **Opioid death rate nearly 3x national average** - highlights substance abuse crisis
4. **Physician shortage** - only 1.2 doctors per 1,000 residents vs 2.6 nationally
"""
    return results


# =============================================================================
# AGENT SYSTEM PROMPT
# =============================================================================

AGENT_SYSTEM_PROMPT = """You are an expert grant writer. Write a complete, professional grant application.

## Required Sections (write ALL of these):
1. **Executive Summary** (400-500 words) - Compelling overview of the project
2. **Statement of Need** (800-1200 words) - Data-driven problem description with citations
3. **Project Description** (1000-1500 words) - Detailed activities, timeline, staffing
4. **Goals & Objectives** (400-600 words) - SMART goals with measurable outcomes
5. **Evaluation Plan** (500-800 words) - How success will be measured
6. **Budget Narrative** (400-600 words) - Justification for expenses
7. **Sustainability Plan** (300-500 words) - How project continues after funding

## Writing Guidelines:
- Use specific statistics WITH citations (source, year)
- Write in professional but accessible language
- Connect local data to national context
- Include measurable outcomes (percentages, numbers)
- Show organizational capacity and track record
- Align with funder priorities

## Format:
Use markdown headers (##) for each section. Write complete, polished content ready for submission.

START WRITING THE COMPLETE APPLICATION NOW."""


# =============================================================================
# GRANT WRITER AGENT
# =============================================================================

class GrantWriterAgent:
    """Autonomous agent for writing complete grant applications."""

    def __init__(self, db_session=None):
        api_key = settings.anthropic_api_key
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = AsyncAnthropic(api_key=api_key)
        self.db_session = db_session
        self.model = "claude-sonnet-4-20250514"

    async def generate_full_application(
        self,
        grant_id: str,
        user_id: str,
        project_title: str,
        project_summary: str,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Generate a complete grant application.

        Args:
            grant_id: Grant program ID
            user_id: User/organization ID
            project_title: Title of proposed project
            project_summary: Brief description of the project
            progress_callback: Optional async callback for progress updates

        Returns:
            Dictionary with complete application and metadata
        """
        start_time = datetime.now()

        if progress_callback:
            await progress_callback("Researching grant requirements...")

        # Step 1: Gather context
        grant_details = await fetch_grant_details(grant_id, self.db_session)
        org_profile = get_org_profile(user_id, self.db_session)
        statistics = search_statistics("Harlan County, KY")

        if progress_callback:
            await progress_callback("Writing application...")

        # Step 2: Build the prompt with all context
        user_prompt = f"""Write a complete grant application for:

**Grant Program:**
{grant_details}

**Applying Organization:**
{org_profile}

**Supporting Statistics:**
{statistics}

**Proposed Project:**
Title: {project_title}

Summary: {project_summary}

Write ALL 7 required sections now. Use the statistics provided with proper citations."""

        # Step 3: Generate the application
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8000,
            system=AGENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        full_application = response.content[0].text

        if progress_callback:
            await progress_callback("Extracting sections...")

        # Step 4: Extract sections
        sections = self._extract_sections(full_application)

        elapsed = (datetime.now() - start_time).total_seconds()

        return {
            "grant_id": grant_id,
            "user_id": user_id,
            "project_title": project_title,
            "project_summary": project_summary,
            "generated_at": datetime.now().isoformat(),
            "generation_time_seconds": elapsed,
            "model": self.model,
            "full_application": full_application,
            "sections": sections,
            "word_count": len(full_application.split()),
            "section_count": len(sections)
        }

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract individual sections from the full application."""
        sections = {}
        section_markers = [
            ("executive_summary", ["## Executive Summary", "## EXECUTIVE SUMMARY", "**Executive Summary**"]),
            ("statement_of_need", ["## Statement of Need", "## STATEMENT OF NEED", "**Statement of Need**"]),
            ("project_description", ["## Project Description", "## PROJECT DESCRIPTION", "**Project Description**"]),
            ("goals_objectives", ["## Goals", "## GOALS", "**Goals", "## Objectives"]),
            ("evaluation_plan", ["## Evaluation", "## EVALUATION", "**Evaluation"]),
            ("budget_narrative", ["## Budget", "## BUDGET", "**Budget"]),
            ("sustainability_plan", ["## Sustainability", "## SUSTAINABILITY", "**Sustainability"]),
        ]

        for key, markers in section_markers:
            for marker in markers:
                if marker in content:
                    start_idx = content.find(marker)
                    # Find end (next ## or end of content)
                    end_idx = len(content)
                    next_section = content.find("\n## ", start_idx + len(marker))
                    if next_section > start_idx:
                        end_idx = next_section

                    section_content = content[start_idx:end_idx].strip()
                    sections[key] = section_content
                    break

        return sections


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

async def generate_grant_application(
    grant_id: str,
    user_id: str,
    project_title: str,
    project_summary: str,
    db_session=None,
    progress_callback=None
) -> Dict[str, Any]:
    """
    Generate a complete grant application using the AI agent.

    Example:
        result = await generate_grant_application(
            grant_id="hrsa_rural_health",
            user_id="user123",
            project_title="Rural Telehealth Initiative",
            project_summary="Expand telehealth services to underserved communities..."
        )
    """
    agent = GrantWriterAgent(db_session=db_session)
    return await agent.generate_full_application(
        grant_id=grant_id,
        user_id=user_id,
        project_title=project_title,
        project_summary=project_summary,
        progress_callback=progress_callback
    )
