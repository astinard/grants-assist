"""
AI Writing Service for Grant Applications

Generates compelling, evidence-based narrative content for grant applications
using Google Gemini. Leverages organization context, prior grant success,
achievements, and community data to create persuasive proposals.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Agency-specific writing preferences
AGENCY_STYLES = {
    "NIH": {
        "tone": "scientific",
        "emphasis": ["research methodology", "scientific rigor", "measurable outcomes", "innovation"],
        "keywords": ["evidence-based", "data-driven", "hypothesis", "clinical significance"],
    },
    "NSF": {
        "tone": "academic",
        "emphasis": ["intellectual merit", "broader impacts", "transformative potential"],
        "keywords": ["novel approach", "paradigm shift", "interdisciplinary", "STEM education"],
    },
    "USDA": {
        "tone": "practical",
        "emphasis": ["agricultural impact", "rural communities", "food security", "sustainability"],
        "keywords": ["producers", "farmers", "rural development", "agricultural innovation"],
    },
    "HHS": {
        "tone": "community-focused",
        "emphasis": ["health equity", "underserved populations", "community partnerships"],
        "keywords": ["health disparities", "social determinants", "community health", "prevention"],
    },
    "DOE": {
        "tone": "technical",
        "emphasis": ["energy efficiency", "environmental impact", "technology transfer"],
        "keywords": ["clean energy", "carbon reduction", "innovation", "scalability"],
    },
    "ED": {
        "tone": "educational",
        "emphasis": ["student outcomes", "educational equity", "evidence-based practices"],
        "keywords": ["achievement gap", "learning outcomes", "professional development", "curriculum"],
    },
}

# Try to import Gemini client
try:
    from google import genai
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    HAS_GEMINI = bool(GOOGLE_API_KEY)
except ImportError:
    HAS_GEMINI = False
    GOOGLE_API_KEY = None


class AIWritingService:
    """
    AI-powered writing assistance for grant applications.
    Uses Gemini 2.0 Flash for generation with fallback templates.
    """

    MODEL_NAME = "gemini-2.0-flash"

    def __init__(self):
        self.client = None
        if HAS_GEMINI and GOOGLE_API_KEY:
            try:
                self.client = genai.Client(api_key=GOOGLE_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    async def generate_narrative(
        self,
        section_type: str,
        context: Dict[str, Any],
        max_words: int = 500,
        tone: str = "professional"
    ) -> str:
        """
        Generate a narrative section for a grant application.

        Args:
            section_type: Type of section (executive_summary, statement_of_need,
                         project_description, budget_justification, sustainability)
            context: Dict with relevant context (org_name, project_goals, etc.)
            max_words: Maximum word count for the section
            tone: Writing tone (professional, formal, conversational)

        Returns:
            Generated narrative text
        """
        if not self.client:
            return self._get_fallback_narrative(section_type, context)

        prompt = self._build_prompt(section_type, context, max_words, tone)

        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return self._get_fallback_narrative(section_type, context)

    async def improve_text(
        self,
        text: str,
        improvement_type: str = "clarity",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Improve existing text.

        Args:
            text: Text to improve
            improvement_type: Type of improvement (clarity, conciseness,
                            persuasion, grammar, professionalism)
            context: Optional additional context

        Returns:
            Improved text
        """
        if not self.client:
            return text  # Return original if no AI available

        prompts = {
            "clarity": "Rewrite this text to be clearer and easier to understand, while maintaining the same meaning:",
            "conciseness": "Make this text more concise without losing important information:",
            "persuasion": "Make this text more persuasive and compelling for a grant application:",
            "grammar": "Fix any grammar, spelling, or punctuation errors in this text:",
            "professionalism": "Rewrite this text to sound more professional and formal:",
        }

        prompt = f"{prompts.get(improvement_type, prompts['clarity'])}\n\n{text}"

        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Text improvement failed: {e}")
            return text

    async def generate_application_sections(
        self,
        profile_data: Dict[str, Any],
        program_data: Dict[str, Any],
        project_summary: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate all narrative sections for a grant application.

        Args:
            profile_data: User's profile information
            program_data: Grant program details
            project_summary: Optional user-provided project summary

        Returns:
            Dict with section names as keys and narratives as values
        """
        context = {
            **profile_data,
            "program_name": program_data.get("name", ""),
            "program_agency": program_data.get("agency", ""),
            "funding_range": f"${program_data.get('min_award', 0):,} - ${program_data.get('max_award', 0):,}",
            "project_summary": project_summary or "",
        }

        sections = {}

        # Generate each section with appropriate word counts
        section_types = [
            ("executive_summary", 250),
            ("statement_of_need", 500),
            ("project_description", 600),
            ("goals_and_objectives", 350),
            ("organizational_capacity", 400),
            ("budget_justification", 350),
            ("evaluation_plan", 300),
            ("sustainability_plan", 300),
        ]

        for section_type, max_words in section_types:
            sections[section_type] = await self.generate_narrative(
                section_type=section_type,
                context=context,
                max_words=max_words
            )

        return sections

    def _build_prompt(
        self,
        section_type: str,
        context: Dict[str, Any],
        max_words: int,
        tone: str
    ) -> str:
        """Build an enhanced prompt leveraging full organizational context."""

        # Extract organization info
        org_name = context.get("organization_name") or context.get("full_name", "the organization")
        program_name = context.get("program_name", "this grant program")
        project_summary = context.get("project_summary", "")
        agency = context.get("program_agency", "")

        # Get agency-specific style if available
        agency_style = None
        for agency_key in AGENCY_STYLES:
            if agency_key in agency.upper():
                agency_style = AGENCY_STYLES[agency_key]
                break

        # Build rich organizational context
        org_context = self._build_org_context(context)
        prior_grants_context = self._build_prior_grants_context(context)
        achievements_context = self._build_achievements_context(context)
        community_context = self._build_community_context(context)
        budget_context = self._build_budget_context(context)

        # Agency-specific instructions
        agency_instructions = ""
        if agency_style:
            agency_instructions = f"""
AGENCY-SPECIFIC GUIDANCE ({agency}):
- Writing tone: {agency_style['tone']}
- Emphasize: {', '.join(agency_style['emphasis'])}
- Use keywords like: {', '.join(agency_style['keywords'])}
"""

        base_context = f"""
=== ORGANIZATION PROFILE ===
{org_context}

=== GRANT OPPORTUNITY ===
Program: {program_name}
Agency: {agency}
Funding Range: {context.get('funding_range', 'varies')}
{agency_instructions}
"""

        if project_summary:
            base_context += f"\n=== PROJECT OVERVIEW ===\n{project_summary}\n"

        if prior_grants_context:
            base_context += f"\n=== PRIOR GRANT SUCCESS ===\n{prior_grants_context}\n"

        if achievements_context:
            base_context += f"\n=== ORGANIZATIONAL ACHIEVEMENTS ===\n{achievements_context}\n"

        if community_context:
            base_context += f"\n=== COMMUNITY DATA ===\n{community_context}\n"

        section_prompts = {
            "executive_summary": f"""
You are an expert grant writer. Write a compelling executive summary for {org_name}'s grant application.

{base_context}

WRITING INSTRUCTIONS:
1. Open with a powerful hook that captures attention
2. Introduce the organization with its mission and track record
3. Clearly state the funding request amount and primary use
4. Highlight 2-3 measurable outcomes using specific numbers
5. Reference prior grant success or achievements as credibility
6. End with a compelling statement about community impact

STYLE REQUIREMENTS:
- Lead with impact, not process
- Use active voice and strong verbs
- Include at least one specific statistic or data point
- Write approximately {max_words} words in a {tone} tone
- Do NOT use placeholder text like [brackets] - write complete content

Generate the executive summary now:
""",
            "statement_of_need": f"""
You are an expert grant writer. Write a data-driven statement of need for {org_name}'s grant application.

{base_context}

WRITING INSTRUCTIONS:
1. Open with a compelling statistic or fact about the problem
2. Define the specific problem or gap being addressed
3. Quantify the need with local/regional data when available
4. Explain root causes and contributing factors
5. Describe who is affected and how (be specific about demographics)
6. Show urgency - why must this be addressed now?
7. Connect to the funder's mission and priorities
8. Position your organization as the solution

DATA TO INCORPORATE:
{community_context if community_context else "- Use general demographic and need statistics relevant to your service area"}

STYLE REQUIREMENTS:
- Build an evidence-based case with statistics
- Show deep understanding of the community
- Create emotional resonance while maintaining professionalism
- Write approximately {max_words} words in a {tone} tone
- Do NOT use placeholder text - write complete content

Generate the statement of need now:
""",
            "project_description": f"""
You are an expert grant writer. Write a detailed project description for {org_name}'s grant application.

{base_context}

WRITING INSTRUCTIONS:
1. Describe the project approach and methodology clearly
2. Break down activities into logical phases or components
3. Specify who will deliver services (staff qualifications)
4. Identify target beneficiaries with numbers
5. Explain how activities address the documented needs
6. Include a realistic timeline with milestones
7. Describe partnerships or collaborations
8. Connect methods to evidence-based practices

PROJECT FRAMEWORK:
- What: Specific activities and services
- Who: Target population and staff
- Where: Service locations
- When: Timeline and phases
- How: Methodology and approach
- Why: Connection to need and funder priorities

STYLE REQUIREMENTS:
- Be specific and concrete, avoid vague language
- Show innovation while demonstrating feasibility
- Reference the organization's experience with similar projects
- Write approximately {max_words} words in a {tone} tone
- Do NOT use placeholder text - write complete content

Generate the project description now:
""",
            "goals_and_objectives": f"""
You are an expert grant writer. Write SMART goals and objectives for {org_name}'s grant application.

{base_context}

WRITING INSTRUCTIONS:
Create 2-3 broad GOALS (long-term outcomes) and 3-5 OBJECTIVES per goal.

Each OBJECTIVE must be SMART:
- Specific: Exactly what will be accomplished
- Measurable: Quantifiable target (numbers, percentages)
- Achievable: Realistic given resources
- Relevant: Connected to stated need and funder priorities
- Time-bound: Clear deadline or timeframe

EXAMPLE FORMAT:
GOAL 1: [Broad outcome statement]
  Objective 1.1: By [date], increase/decrease [metric] by [amount] through [activity]
  Objective 1.2: Within [timeframe], serve [number] [population] achieving [outcome]

Include:
- Baseline data where available
- Clear success metrics
- Evaluation methods for each objective

STYLE REQUIREMENTS:
- Use strong action verbs (increase, reduce, implement, train)
- Include specific numbers and percentages
- Tie each objective to activities in project description
- Write approximately {max_words} words in a {tone} tone

Generate the goals and objectives now:
""",
            "budget_justification": f"""
You are an expert grant writer. Write a compelling budget justification for {org_name}'s grant application.

{base_context}
{budget_context if budget_context else ""}

WRITING INSTRUCTIONS:
For each budget category, explain:
1. WHAT: Specific line items and costs
2. WHY: How each expense supports project objectives
3. HOW: Basis for cost calculations (market rates, quotes, historical data)

BUDGET CATEGORIES TO ADDRESS:
- Personnel: Positions, FTE, qualifications, and why each role is essential
- Fringe Benefits: Rate basis and included benefits
- Equipment: Items over $5,000, why needed, quotes obtained
- Supplies: Categories of supplies and connection to activities
- Contractual: Subcontractors, consultants, and selection basis
- Travel: Purpose, destinations, and cost basis
- Other: Any additional direct costs
- Indirect: Rate and basis (if applicable)

KEY PRINCIPLES:
- Show costs are reasonable (market rates, competitive bids)
- Demonstrate cost-effectiveness and efficiency
- Connect every expense to specific project activities
- Explain any matching or in-kind contributions

STYLE REQUIREMENTS:
- Be specific about quantities and rates
- Reference industry standards or organizational history
- Show you've done thorough cost research
- Write approximately {max_words} words in a {tone} tone

Generate the budget justification now:
""",
            "sustainability_plan": f"""
You are an expert grant writer. Write a credible sustainability plan for {org_name}'s grant application.

{base_context}

WRITING INSTRUCTIONS:
Demonstrate how the project will continue after grant funding ends:

1. DIVERSIFIED FUNDING STRATEGY:
   - Other grants being pursued
   - Individual donor cultivation
   - Corporate sponsorships
   - Government contracts
   - Earned revenue opportunities

2. ORGANIZATIONAL CAPACITY:
   - Staff expertise and retention plans
   - Board development for fundraising
   - Infrastructure and systems
   - Prior success sustaining grant-funded programs

3. COMMUNITY INTEGRATION:
   - Partnerships that will continue
   - How program becomes embedded in community
   - Stakeholder investment and ownership

4. REVENUE GENERATION (if applicable):
   - Fee-for-service models
   - Social enterprise opportunities
   - Sliding scale structures

5. SPECIFIC COMMITMENTS:
   - Timeline for transition to sustainable funding
   - Percentage goals for diversification
   - Letters of support or MOUs from partners

CREDIBILITY FACTORS:
{prior_grants_context if prior_grants_context else "- Reference any prior sustained programs"}

STYLE REQUIREMENTS:
- Be specific about funding sources and amounts
- Show realistic timeline for sustainability
- Demonstrate organizational commitment
- Write approximately {max_words} words in a {tone} tone

Generate the sustainability plan now:
""",
            "organizational_capacity": f"""
You are an expert grant writer. Write an organizational capacity statement for {org_name}'s grant application.

{base_context}

WRITING INSTRUCTIONS:
Demonstrate why your organization is qualified to implement this project:

1. ORGANIZATIONAL HISTORY:
   - Years of operation
   - Mission alignment with project
   - Service area and population served

2. RELEVANT EXPERIENCE:
   - Similar projects successfully completed
   - Track record with this type of work
   - Specific outcomes achieved

3. LEADERSHIP & GOVERNANCE:
   - Executive leadership qualifications
   - Board composition and expertise
   - Key staff for this project

4. INFRASTRUCTURE:
   - Facilities and equipment
   - Technology and systems
   - Financial management capacity

5. PARTNERSHIPS:
   - Existing collaborations
   - Letters of support
   - Community relationships

CREDIBILITY EVIDENCE:
{achievements_context if achievements_context else ""}
{prior_grants_context if prior_grants_context else ""}

STYLE REQUIREMENTS:
- Lead with strongest qualifications
- Use specific examples and data
- Show clear connection to proposed project
- Write approximately {max_words} words in a {tone} tone

Generate the organizational capacity statement now:
""",
            "evaluation_plan": f"""
You are an expert grant writer. Write an evaluation plan for {org_name}'s grant application.

{base_context}

WRITING INSTRUCTIONS:
Create a comprehensive evaluation framework:

1. EVALUATION APPROACH:
   - Process evaluation (implementation fidelity)
   - Outcome evaluation (results achieved)
   - Internal vs. external evaluation

2. DATA COLLECTION METHODS:
   - Quantitative measures (surveys, tracking data, pre/post tests)
   - Qualitative measures (interviews, focus groups, observations)
   - Frequency of data collection

3. KEY PERFORMANCE INDICATORS:
   - Align with stated objectives
   - Baseline and target metrics
   - Data sources for each indicator

4. ANALYSIS & REPORTING:
   - How data will be analyzed
   - Reporting schedule (quarterly, annual)
   - Who receives reports

5. CONTINUOUS IMPROVEMENT:
   - How findings inform program adjustments
   - Feedback loops
   - Learning organization approach

STYLE REQUIREMENTS:
- Be specific about tools and timelines
- Show realistic data collection capacity
- Connect to project objectives
- Write approximately {max_words} words in a {tone} tone

Generate the evaluation plan now:
""",
        }

        return section_prompts.get(section_type, f"Write a {section_type} section for a grant application.\n{base_context}")

    def _build_org_context(self, context: Dict[str, Any]) -> str:
        """Build rich organizational context from profile data."""
        parts = []

        org_name = context.get("organization_name") or context.get("full_name", "Organization")
        parts.append(f"Name: {org_name}")

        if context.get("organization_type"):
            parts.append(f"Type: {context['organization_type']}")

        if context.get("mission_statement"):
            parts.append(f"Mission: {context['mission_statement']}")

        if context.get("city") and context.get("state"):
            parts.append(f"Location: {context['city']}, {context['state']}")

        if context.get("annual_budget"):
            budget = context["annual_budget"]
            parts.append(f"Annual Budget: ${budget:,.0f}")

        if context.get("staff_count"):
            parts.append(f"Staff: {context['staff_count']} employees")

        if context.get("year_founded"):
            years_operating = datetime.now().year - context["year_founded"]
            parts.append(f"Years Operating: {years_operating} years (founded {context['year_founded']})")

        if context.get("ein"):
            parts.append(f"EIN: {context['ein']}")

        if context.get("sam_uei"):
            parts.append(f"SAM.gov UEI: {context['sam_uei']} (Federal registration complete)")

        certifications = []
        if context.get("has_501c3"):
            certifications.append("501(c)(3)")
        if context.get("is_minority_owned"):
            certifications.append("Minority-Owned")
        if context.get("is_woman_owned"):
            certifications.append("Woman-Owned")
        if context.get("is_veteran_owned"):
            certifications.append("Veteran-Owned")
        if certifications:
            parts.append(f"Certifications: {', '.join(certifications)}")

        return "\n".join(parts)

    def _build_prior_grants_context(self, context: Dict[str, Any]) -> str:
        """Build context from prior grant history."""
        prior_grants = context.get("prior_grants", [])
        if not prior_grants:
            return ""

        parts = []
        total_awarded = sum(g.get("amount_awarded", 0) for g in prior_grants if g.get("status") == "awarded")
        awarded_count = sum(1 for g in prior_grants if g.get("status") == "awarded")

        if awarded_count > 0:
            parts.append(f"Grant Track Record: {awarded_count} grants totaling ${total_awarded:,.0f}")

        # List recent successful grants
        recent_awarded = [g for g in prior_grants if g.get("status") == "awarded"][:3]
        if recent_awarded:
            parts.append("Recent Grant Success:")
            for grant in recent_awarded:
                parts.append(f"  - {grant.get('program_name', 'Grant')}: ${grant.get('amount_awarded', 0):,.0f}")

        return "\n".join(parts)

    def _build_achievements_context(self, context: Dict[str, Any]) -> str:
        """Build context from organizational achievements."""
        achievements = context.get("achievements", [])
        if not achievements:
            return ""

        parts = ["Key Achievements:"]
        for achievement in achievements[:5]:
            if achievement.get("metric_value") and achievement.get("metric_type"):
                parts.append(f"  - {achievement.get('title', '')}: {achievement['metric_value']} {achievement['metric_type']}")
            else:
                parts.append(f"  - {achievement.get('title', '')}: {achievement.get('description', '')[:100]}")

        return "\n".join(parts)

    def _build_community_context(self, context: Dict[str, Any]) -> str:
        """Build context from community data."""
        community_data = context.get("community_data", [])
        if not community_data:
            return ""

        parts = ["Community Statistics:"]
        for data in community_data[:6]:
            parts.append(f"  - {data.get('data_type', 'Metric')}: {data.get('value', '')} ({data.get('source', 'Local data')})")

        return "\n".join(parts)

    def _build_budget_context(self, context: Dict[str, Any]) -> str:
        """Build context from budget data."""
        budget_items = context.get("budget_items", [])
        if not budget_items:
            return ""

        parts = ["Proposed Budget Categories:"]

        # Group by category
        categories = {}
        for item in budget_items:
            cat = item.get("category", "Other")
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += item.get("amount", 0)

        for cat, amount in categories.items():
            parts.append(f"  - {cat}: ${amount:,.0f}")

        total = sum(categories.values())
        parts.append(f"  Total Request: ${total:,.0f}")

        return "\n".join(parts)

    def _get_fallback_narrative(self, section_type: str, context: Dict[str, Any]) -> str:
        """Return fallback template text when AI is unavailable."""

        org_name = context.get("organization_name") or context.get("full_name", "[Organization Name]")
        program_name = context.get("program_name", "[Grant Program]")

        fallbacks = {
            "executive_summary": f"""
{org_name} respectfully requests funding from {program_name} to support our ongoing mission
and expand our services to the community. This funding will enable us to [describe primary
use of funds], directly benefiting [target population] in [service area].

Our organization has a proven track record of [key achievements], and we are well-positioned
to deliver measurable outcomes with this investment. We anticipate that this project will
[describe expected impact].
""",
            "statement_of_need": f"""
[Describe the problem or gap your project addresses]

Our community faces significant challenges including [specific issues]. According to
[cite relevant data or statistics], this need affects [number/percentage] of residents
in our service area.

{org_name} is uniquely positioned to address this need because [explain organizational
qualifications and community connections].
""",
            "project_description": f"""
{org_name} proposes to [brief project description] through the {program_name} opportunity.

Project Activities:
- [Activity 1]
- [Activity 2]
- [Activity 3]

Timeline:
- Month 1-3: [Phase 1 activities]
- Month 4-6: [Phase 2 activities]
- Month 7-12: [Phase 3 activities]

This project will serve [target population] and result in [expected outcomes].
""",
            "goals_and_objectives": f"""
Goal 1: [Broad outcome statement]
- Objective 1.1: [Specific, measurable objective]
- Objective 1.2: [Specific, measurable objective]

Goal 2: [Broad outcome statement]
- Objective 2.1: [Specific, measurable objective]
- Objective 2.2: [Specific, measurable objective]

Success will be measured through [describe evaluation methods and metrics].
""",
            "budget_justification": f"""
Personnel: Funds will support [positions] essential for project implementation and oversight.

Equipment/Supplies: [Describe necessary purchases] are required to [explain purpose].

Other Costs: [Describe additional budget items] support [explain how they enable project success].

All costs are based on [market rates/organizational standards] and are necessary for
achieving project objectives.
""",
            "sustainability_plan": f"""
{org_name} is committed to sustaining this project beyond the grant period through:

1. Diversified Funding: We will pursue [other funding sources] to continue operations.

2. Community Partnerships: Collaborations with [partners] will provide ongoing support.

3. Revenue Generation: [If applicable, describe earned revenue strategies]

4. Organizational Capacity: Our established infrastructure and experienced team ensure
   long-term viability.
""",
            "organizational_capacity": f"""
{org_name} has demonstrated the organizational capacity to successfully implement this project:

ORGANIZATIONAL HISTORY:
Founded in [year], {org_name} has [X] years of experience serving [target population].
Our mission aligns directly with this project's goals.

RELEVANT EXPERIENCE:
- [Previous similar project with outcomes]
- [Track record in this service area]
- [Partnerships and collaborations]

LEADERSHIP & STAFF:
- Executive Director: [qualifications]
- Project Manager: [qualifications]
- Key Staff: [relevant experience]

INFRASTRUCTURE:
We maintain [facilities, technology, systems] necessary for project implementation and
have established financial management practices including [annual audits, etc.].
""",
            "evaluation_plan": f"""
{org_name} will implement a comprehensive evaluation plan to measure project success:

EVALUATION APPROACH:
We will conduct both process and outcome evaluation to assess implementation fidelity
and measure results against stated objectives.

DATA COLLECTION:
- Quantitative: [surveys, tracking data, pre/post assessments]
- Qualitative: [interviews, focus groups, observations]
- Collection frequency: [monthly, quarterly, etc.]

KEY PERFORMANCE INDICATORS:
- [KPI 1]: Baseline [X], Target [Y]
- [KPI 2]: Baseline [X], Target [Y]
- [KPI 3]: Baseline [X], Target [Y]

REPORTING:
Quarterly progress reports will be submitted to [funder], with a comprehensive
final report documenting outcomes, lessons learned, and recommendations.
""",
        }

        return fallbacks.get(section_type, f"[Please write your {section_type} here]").strip()


# Singleton instance
ai_writing_service = AIWritingService()
