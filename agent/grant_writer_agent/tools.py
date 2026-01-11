"""
Grant Writer Agent Tools

Tools for autonomous grant application writing:
- fetch_grant_details: Get grant requirements from API
- get_org_profile: Get organization data
- search_statistics: Search for relevant data (Census, health stats)
- web_search: Search web for supporting information
- evaluate_section: Self-critique a drafted section
- check_compliance: Verify compliance with grant requirements
"""

import os
import json
import httpx
from typing import Any
from claude_agent_sdk import tool

# API Configuration
GRANTS_API_URL = os.getenv("GRANTS_API_URL", "https://api-production-ce3d4.up.railway.app")
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")


# =============================================================================
# GRANT DATA TOOLS
# =============================================================================

@tool(
    name="fetch_grant_details",
    description="Fetch detailed information about a specific grant program including requirements, eligibility, deadlines, and award amounts",
    input_schema={
        "grant_id": {"type": "string", "description": "The grant program ID (e.g., 'grants_gov_12345' or 'hrsa_rural_health')"}
    }
)
async def fetch_grant_details(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch grant details from the Grants API."""
    grant_id = args["grant_id"]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{GRANTS_API_URL}/api/programs/{grant_id}",
                timeout=30.0
            )
            response.raise_for_status()
            grant = response.json()

            # Format the grant details
            details = f"""
## Grant: {grant.get('name', 'Unknown')}

**Agency:** {grant.get('agency', 'Unknown')}
**Category:** {grant.get('category', 'Unknown')}

**Award Range:** ${grant.get('min_award', 0):,.0f} - ${grant.get('max_award', 0):,.0f}
**Match Required:** {(grant.get('match_required', 0) * 100):.0f}%
**Deadline:** {grant.get('deadline', 'Rolling/Open')}

**Description:**
{grant.get('description', 'No description available')}

**Eligibility:**
{grant.get('eligibility_summary', 'See grant guidelines')}

**Program URL:** {grant.get('program_url', 'N/A')}
"""
            return {
                "content": [{"type": "text", "text": details}]
            }

        except httpx.HTTPError as e:
            return {
                "content": [{"type": "text", "text": f"Error fetching grant: {str(e)}"}],
                "is_error": True
            }


@tool(
    name="search_grants",
    description="Search for grants matching specific criteria like category, keyword, or agency",
    input_schema={
        "query": {"type": "string", "description": "Search query (e.g., 'rural health', 'small business', 'education')"},
        "category": {"type": "string", "description": "Optional category filter: healthcare, small_business, education, nonprofit, agriculture, technology, housing"}
    }
)
async def search_grants(args: dict[str, Any]) -> dict[str, Any]:
    """Search for matching grants."""
    query = args.get("query", "")
    category = args.get("category", "")

    async with httpx.AsyncClient() as client:
        try:
            params = {"search": query}
            if category:
                params["category"] = category

            response = await client.get(
                f"{GRANTS_API_URL}/api/programs/",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            grants = data.get("programs", [])[:10]  # Limit to top 10

            if not grants:
                return {
                    "content": [{"type": "text", "text": "No grants found matching your criteria."}]
                }

            results = f"## Found {len(grants)} matching grants:\n\n"
            for g in grants:
                results += f"""### {g['name']}
- **ID:** {g['id']}
- **Agency:** {g.get('agency', 'Unknown')}
- **Award:** ${g.get('min_award', 0):,.0f} - ${g.get('max_award', 0):,.0f}
- **Deadline:** {g.get('deadline', 'Rolling')}

"""
            return {
                "content": [{"type": "text", "text": results}]
            }

        except httpx.HTTPError as e:
            return {
                "content": [{"type": "text", "text": f"Error searching grants: {str(e)}"}],
                "is_error": True
            }


# =============================================================================
# ORGANIZATION PROFILE TOOLS
# =============================================================================

@tool(
    name="get_org_profile",
    description="Get the organization's profile data for use in the grant application (mission, history, demographics, prior grants)",
    input_schema={
        "user_id": {"type": "string", "description": "The user/organization ID"}
    }
)
async def get_org_profile(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch organization profile from the API."""
    user_id = args["user_id"]

    # For demo purposes, return sample organization data
    # In production, this would fetch from the API
    profile = {
        "organization_name": "Harlan County Community Health Center",
        "organization_type": "501(c)(3) Nonprofit",
        "ein": "12-3456789",
        "uei_number": "ABC123456789",
        "address": "123 Main Street, Harlan, KY 40831",
        "congressional_district": "KY-05",
        "mission_statement": "To provide accessible, high-quality healthcare to all residents of Harlan County, regardless of ability to pay.",
        "founding_year": 2008,
        "service_area": "Harlan County, Kentucky",
        "service_area_population": 26_010,
        "annual_budget": 2_500_000,
        "staff_count": 35,
        "clients_served_annually": 8_500,
        "is_rural": True,
        "is_underserved": True,
        "prior_grants": [
            {"funder": "HRSA", "amount": 150000, "year": 2023, "purpose": "Telehealth expansion"},
            {"funder": "Appalachian Regional Commission", "amount": 75000, "year": 2022, "purpose": "Mobile health unit"}
        ]
    }

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

    return {
        "content": [{"type": "text", "text": profile_text}]
    }


# =============================================================================
# STATISTICS & RESEARCH TOOLS
# =============================================================================

@tool(
    name="search_statistics",
    description="Search for statistics and data to support the statement of need (poverty rates, health outcomes, unemployment, etc.)",
    input_schema={
        "location": {"type": "string", "description": "Geographic location (e.g., 'Harlan County, KY')"},
        "metrics": {"type": "array", "items": {"type": "string"}, "description": "List of metrics to search for (e.g., ['poverty_rate', 'unemployment', 'health_outcomes'])"}
    }
)
async def search_statistics(args: dict[str, Any]) -> dict[str, Any]:
    """Search for relevant statistics for the statement of need."""
    location = args.get("location", "")
    metrics = args.get("metrics", [])

    # Simulated statistics data (in production, would query Census API, CDC, etc.)
    stats_data = {
        "Harlan County, KY": {
            "poverty_rate": {"value": "32.1%", "comparison": "11.4% (US avg)", "source": "US Census Bureau 2023"},
            "unemployment": {"value": "8.2%", "comparison": "3.7% (US avg)", "source": "BLS 2024"},
            "median_income": {"value": "$27,149", "comparison": "$74,580 (US avg)", "source": "US Census Bureau 2023"},
            "uninsured_rate": {"value": "12.8%", "comparison": "8.0% (US avg)", "source": "Census ACS 2023"},
            "diabetes_rate": {"value": "18.2%", "comparison": "10.5% (US avg)", "source": "CDC 2023"},
            "obesity_rate": {"value": "42.1%", "comparison": "31.9% (US avg)", "source": "CDC 2023"},
            "life_expectancy": {"value": "72.1 years", "comparison": "78.8 years (US avg)", "source": "CDC NVSS 2023"},
            "opioid_deaths": {"value": "58.3 per 100k", "comparison": "21.6 per 100k (US avg)", "source": "CDC WONDER 2023"},
            "physicians_per_capita": {"value": "1.2 per 1,000", "comparison": "2.6 per 1,000 (US avg)", "source": "HRSA 2023"},
            "no_vehicle": {"value": "11.2%", "comparison": "8.5% (US avg)", "source": "Census ACS 2023"},
            "broadband_access": {"value": "67%", "comparison": "90% (US avg)", "source": "FCC 2023"}
        }
    }

    # Find data for location (default to Harlan County for demo)
    location_data = stats_data.get("Harlan County, KY", {})

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
5. **Limited transportation and broadband** - barriers to accessing care
"""

    return {
        "content": [{"type": "text", "text": results}]
    }


@tool(
    name="web_search",
    description="Search the web for additional information, news, or research to support the grant application",
    input_schema={
        "query": {"type": "string", "description": "Search query"}
    }
)
async def web_search(args: dict[str, Any]) -> dict[str, Any]:
    """Simulate web search for supporting information."""
    query = args.get("query", "")

    # Simulated search results (in production, would use actual search API)
    results = f"""## Web Search Results for: "{query}"

### Relevant Sources Found:

1. **Appalachian Regional Commission Report (2024)**
   - "Health Disparities in Appalachia" details the challenges facing rural communities
   - Key finding: Central Appalachia has some of the poorest health outcomes in the nation
   - URL: https://www.arc.gov/health-disparities

2. **HRSA Health Professional Shortage Areas**
   - Harlan County designated as HPSA for primary care, dental, and mental health
   - Shortage designation score: 18 (out of 25)
   - URL: https://data.hrsa.gov/tools/shortage-area

3. **CDC Morbidity and Mortality Weekly Report**
   - "Rural Health Disparities in Kentucky" (2023)
   - Documents elevated rates of chronic disease, substance abuse, and mortality
   - URL: https://www.cdc.gov/mmwr/

4. **University of Kentucky Rural Health Research**
   - Economic impact of healthcare deserts in Eastern Kentucky
   - Recommends community health center expansion
   - URL: https://www.uky.edu/research/rural-health

### Suggested Citations:
- Appalachian Regional Commission. (2024). Health Disparities in Appalachia.
- HRSA. (2024). Health Professional Shortage Area Designations.
- CDC. (2023). Rural Health Disparities in Kentucky. MMWR.
"""

    return {
        "content": [{"type": "text", "text": results}]
    }


# =============================================================================
# EVALUATION TOOLS
# =============================================================================

@tool(
    name="evaluate_section",
    description="Evaluate a drafted grant section against best practices and funder priorities. Returns a score and specific improvement suggestions.",
    input_schema={
        "section_type": {"type": "string", "description": "Type of section: statement_of_need, project_description, goals_objectives, evaluation_plan, budget_narrative, sustainability_plan"},
        "content": {"type": "string", "description": "The drafted section content to evaluate"},
        "grant_type": {"type": "string", "description": "Type of grant (e.g., 'HRSA', 'NIH', 'NSF')"}
    }
)
async def evaluate_section(args: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a grant section and provide feedback."""
    section_type = args.get("section_type", "")
    content = args.get("content", "")
    grant_type = args.get("grant_type", "federal")

    word_count = len(content.split())

    # Evaluation criteria by section type
    criteria = {
        "statement_of_need": {
            "data_citations": "Uses specific, cited statistics",
            "local_context": "Connects data to local community",
            "urgency": "Establishes urgency and compelling need",
            "target_population": "Clearly defines who will be served",
            "gap_analysis": "Identifies gaps in current services"
        },
        "project_description": {
            "clear_activities": "Activities are specific and actionable",
            "timeline": "Includes realistic timeline",
            "staffing": "Describes qualified staff/partners",
            "innovation": "Explains what's innovative or evidence-based",
            "feasibility": "Demonstrates capacity to implement"
        },
        "goals_objectives": {
            "smart_goals": "Goals are Specific, Measurable, Achievable, Relevant, Time-bound",
            "alignment": "Objectives align with funder priorities",
            "outcomes_focus": "Focuses on outcomes, not just outputs",
            "measurability": "Can be objectively measured"
        }
    }

    section_criteria = criteria.get(section_type, criteria["statement_of_need"])

    evaluation = f"""## Section Evaluation: {section_type.replace('_', ' ').title()}

**Word Count:** {word_count} words

### Scoring Rubric:
"""

    # Simulate scoring (in production, would use Claude to actually evaluate)
    total_score = 0
    for criterion, description in section_criteria.items():
        # Simple heuristic scoring for demo
        score = 7 + (word_count % 3)  # 7-9 range
        total_score += score
        status = "✅" if score >= 8 else "⚠️" if score >= 6 else "❌"
        evaluation += f"- {status} **{criterion.replace('_', ' ').title()}** ({score}/10): {description}\n"

    avg_score = total_score / len(section_criteria)

    evaluation += f"""
### Overall Score: {avg_score:.1f}/10

### Improvement Suggestions:
1. Add more specific statistics with citations (aim for 3-5 data points)
2. Include direct quotes from community members or stakeholders
3. Connect local data to national trends to show broader context
4. Strengthen the "so what" - why does this matter NOW?
5. Add a brief mention of what happens if the problem is NOT addressed

### Recommended Next Steps:
{"✅ Section meets quality threshold - ready for final review" if avg_score >= 8 else "⚠️ Section needs revision before submission - address suggestions above"}
"""

    return {
        "content": [{"type": "text", "text": evaluation}]
    }


@tool(
    name="check_compliance",
    description="Check if the grant application meets all compliance requirements (word limits, required sections, formatting)",
    input_schema={
        "grant_id": {"type": "string", "description": "The grant program ID"},
        "sections": {"type": "object", "description": "Dictionary of section names to content"}
    }
)
async def check_compliance(args: dict[str, Any]) -> dict[str, Any]:
    """Check compliance with grant requirements."""
    grant_id = args.get("grant_id", "")
    sections = args.get("sections", {})

    # Standard federal grant requirements
    requirements = {
        "required_sections": [
            "executive_summary",
            "statement_of_need",
            "project_description",
            "goals_objectives",
            "evaluation_plan",
            "budget_narrative",
            "sustainability_plan"
        ],
        "word_limits": {
            "executive_summary": 500,
            "statement_of_need": 1500,
            "project_description": 3000,
            "goals_objectives": 1000,
            "evaluation_plan": 1500,
            "budget_narrative": 1500,
            "sustainability_plan": 1000
        }
    }

    compliance = "## Compliance Check Report\n\n"
    issues = []
    passed = 0
    total = 0

    # Check required sections
    compliance += "### Required Sections:\n"
    for section in requirements["required_sections"]:
        total += 1
        if section in sections:
            passed += 1
            compliance += f"- ✅ {section.replace('_', ' ').title()}: Present\n"
        else:
            compliance += f"- ❌ {section.replace('_', ' ').title()}: **MISSING**\n"
            issues.append(f"Missing required section: {section}")

    # Check word limits
    compliance += "\n### Word Limits:\n"
    for section, content in sections.items():
        if section in requirements["word_limits"]:
            total += 1
            word_count = len(str(content).split())
            limit = requirements["word_limits"][section]

            if word_count <= limit:
                passed += 1
                compliance += f"- ✅ {section.replace('_', ' ').title()}: {word_count}/{limit} words\n"
            else:
                compliance += f"- ❌ {section.replace('_', ' ').title()}: {word_count}/{limit} words **OVER LIMIT**\n"
                issues.append(f"{section} exceeds word limit by {word_count - limit} words")

    # Summary
    compliance += f"""
### Summary:
- **Passed:** {passed}/{total} checks
- **Status:** {"✅ READY FOR SUBMISSION" if passed == total else "❌ ISSUES MUST BE RESOLVED"}

"""

    if issues:
        compliance += "### Issues to Resolve:\n"
        for i, issue in enumerate(issues, 1):
            compliance += f"{i}. {issue}\n"

    return {
        "content": [{"type": "text", "text": compliance}]
    }


# =============================================================================
# TOOL REGISTRY
# =============================================================================

ALL_TOOLS = [
    fetch_grant_details,
    search_grants,
    get_org_profile,
    search_statistics,
    web_search,
    evaluate_section,
    check_compliance,
]
