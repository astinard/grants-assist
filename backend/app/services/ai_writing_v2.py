"""
Professional AI Writing Service v2 for Grant Applications

Multi-phase generation with consulting-firm quality output.
Uses Google Gemini 2.0 Flash with optimized prompts and context.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    ApplicationSection, SectionType, Application
)
from app.services.context_assembler import ContextAssembler

logger = logging.getLogger(__name__)

# Gemini client setup
try:
    from google import genai
    from google.genai import types
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    HAS_GEMINI = bool(GOOGLE_API_KEY)
except ImportError:
    HAS_GEMINI = False
    GOOGLE_API_KEY = None
    genai = None
    types = None


# Section configuration with professional requirements
SECTION_CONFIG = {
    SectionType.COVER_LETTER: {
        "title": "Cover Letter",
        "min_words": 250,
        "max_words": 400,
        "temperature": 0.7,
        "order": 1,
    },
    SectionType.EXECUTIVE_SUMMARY: {
        "title": "Executive Summary",
        "min_words": 400,
        "max_words": 600,
        "temperature": 0.6,
        "order": 2,
    },
    SectionType.ORGANIZATIONAL_BACKGROUND: {
        "title": "Organizational Background",
        "min_words": 500,
        "max_words": 800,
        "temperature": 0.5,
        "order": 3,
    },
    SectionType.STATEMENT_OF_NEED: {
        "title": "Statement of Need",
        "min_words": 600,
        "max_words": 1000,
        "temperature": 0.5,
        "order": 4,
    },
    SectionType.PROJECT_DESCRIPTION: {
        "title": "Project Description",
        "min_words": 800,
        "max_words": 1500,
        "temperature": 0.6,
        "order": 5,
    },
    SectionType.GOALS_OBJECTIVES: {
        "title": "Goals and Objectives",
        "min_words": 400,
        "max_words": 700,
        "temperature": 0.4,
        "order": 6,
    },
    SectionType.EVALUATION_PLAN: {
        "title": "Evaluation Plan",
        "min_words": 400,
        "max_words": 700,
        "temperature": 0.5,
        "order": 7,
    },
    SectionType.BUDGET_NARRATIVE: {
        "title": "Budget Narrative",
        "min_words": 400,
        "max_words": 800,
        "temperature": 0.4,
        "order": 8,
    },
    SectionType.SUSTAINABILITY_PLAN: {
        "title": "Sustainability Plan",
        "min_words": 300,
        "max_words": 600,
        "temperature": 0.6,
        "order": 9,
    },
    SectionType.CONCLUSION: {
        "title": "Conclusion",
        "min_words": 150,
        "max_words": 300,
        "temperature": 0.7,
        "order": 10,
    },
}


class ProfessionalAIWritingService:
    """
    Professional-grade AI writing service for grant applications.

    Implements multi-phase generation:
    1. Context Assembly - Gather all relevant data
    2. Outline Generation - Create detailed section outline
    3. Draft Expansion - Generate full professional content
    4. Refinement - Polish and improve flow
    """

    MODEL_NAME = "gemini-2.0-flash"

    def __init__(self, db: Session):
        self.db = db
        self.client = None
        self.context_assembler = ContextAssembler(db)

        if HAS_GEMINI and GOOGLE_API_KEY:
            try:
                self.client = genai.Client(api_key=GOOGLE_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    async def generate_professional_application(
        self,
        user_id: str,
        application_id: str,
        program_id: str,
        sections_to_generate: Optional[List[SectionType]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete professional grant application.

        Args:
            user_id: User's ID
            application_id: Application ID
            program_id: Grant program ID
            sections_to_generate: Optional list of specific sections to generate

        Returns:
            Dict with generated sections and metadata
        """
        # Phase 1: Assemble context
        context = self.context_assembler.assemble_full_context(
            user_id=user_id,
            application_id=application_id,
            program_id=program_id
        )

        # Determine which sections to generate
        if sections_to_generate is None:
            sections_to_generate = list(SectionType)

        results = {
            "application_id": application_id,
            "sections": {},
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "model": self.MODEL_NAME,
                "context_summary": context.get("summary", {}),
            }
        }

        # Generate each section
        for section_type in sections_to_generate:
            try:
                section_result = await self._generate_section(
                    section_type=section_type,
                    context=context,
                    application_id=application_id
                )
                results["sections"][section_type.value] = section_result
            except Exception as e:
                logger.error(f"Failed to generate {section_type.value}: {e}")
                results["sections"][section_type.value] = {
                    "content": self._get_fallback_content(section_type, context),
                    "error": str(e),
                    "word_count": 0,
                }

        return results

    async def _generate_section(
        self,
        section_type: SectionType,
        context: Dict[str, Any],
        application_id: str
    ) -> Dict[str, Any]:
        """
        Generate a single section using multi-phase approach.
        """
        config = SECTION_CONFIG.get(section_type, {})

        if not self.client:
            fallback_content = self._get_fallback_content(section_type, context)
            word_count = len(fallback_content.split())

            # Save fallback content to database
            await self._save_section(
                application_id=application_id,
                section_type=section_type,
                content=fallback_content,
                word_count=word_count
            )

            return {
                "content": fallback_content,
                "word_count": word_count,
                "title": config.get("title", section_type.value),
                "order": config.get("order", 99),
                "phase": "fallback",
            }

        # Phase 2: Generate outline
        outline = await self._generate_outline(section_type, context, config)

        # Phase 3: Generate full draft
        draft = await self._generate_draft(section_type, context, outline, config)

        # Phase 4: Refine and polish
        final_content = await self._refine_content(section_type, draft, context, config)

        # Count words
        word_count = len(final_content.split())

        # Save to database
        await self._save_section(
            application_id=application_id,
            section_type=section_type,
            content=final_content,
            word_count=word_count
        )

        return {
            "content": final_content,
            "word_count": word_count,
            "title": config.get("title", section_type.value),
            "order": config.get("order", 99),
        }

    async def _generate_outline(
        self,
        section_type: SectionType,
        context: Dict[str, Any],
        config: Dict[str, Any]
    ) -> str:
        """Generate a detailed outline for the section."""
        prompt = self._build_outline_prompt(section_type, context, config)

        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temp for structured outline
                    max_output_tokens=1000,
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Outline generation failed: {e}")
            return ""

    async def _generate_draft(
        self,
        section_type: SectionType,
        context: Dict[str, Any],
        outline: str,
        config: Dict[str, Any]
    ) -> str:
        """Generate the full draft based on outline."""
        prompt = self._build_draft_prompt(section_type, context, outline, config)

        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=config.get("temperature", 0.6),
                    max_output_tokens=3000,
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Draft generation failed: {e}")
            return self._get_fallback_content(section_type, context)

    async def _refine_content(
        self,
        section_type: SectionType,
        draft: str,
        context: Dict[str, Any],
        config: Dict[str, Any]
    ) -> str:
        """Refine and polish the draft content."""
        if not draft or len(draft) < 100:
            return draft

        prompt = self._build_refinement_prompt(section_type, draft, context, config)

        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=3500,
                )
            )
            refined = response.text.strip()
            # Return refined if it's reasonable, otherwise return original
            if len(refined) > len(draft) * 0.5:
                return refined
            return draft
        except Exception as e:
            logger.warning(f"Refinement failed: {e}")
            return draft

    def _build_outline_prompt(
        self,
        section_type: SectionType,
        context: Dict[str, Any],
        config: Dict[str, Any]
    ) -> str:
        """Build prompt for outline generation."""
        summary = context.get("summary", {})
        org = context.get("organization", {})

        base_context = self._format_base_context(context)

        outline_prompts = {
            SectionType.COVER_LETTER: f"""
Create an outline for a professional grant cover letter.

{base_context}

The cover letter should include:
1. Professional greeting and introduction
2. Clear statement of funding request
3. Brief organizational credibility statement
4. Connection to funder's mission/priorities
5. Compelling reason why this grant matters
6. Professional closing with contact information

Create a detailed outline with specific points to include in each section.
""",
            SectionType.EXECUTIVE_SUMMARY: f"""
Create an outline for a compelling executive summary for a grant application.

{base_context}

The executive summary should include:
1. Opening hook that captures attention
2. Organization introduction (1-2 sentences)
3. Problem/need statement (with key statistic)
4. Proposed solution overview
5. Funding request and use of funds
6. Expected outcomes and impact metrics
7. Organizational qualifications (brief)
8. Closing call to action

Create a detailed outline with specific data points and key messages.
""",
            SectionType.ORGANIZATIONAL_BACKGROUND: f"""
Create an outline for the organizational background section.

{base_context}

Prior Grants: {len(context.get('prior_grants', []))} awarded grants totaling ${summary.get('total_prior_funding', 0):,.0f}
Achievements: {len(context.get('achievements', []))} documented achievements
Years Operating: {summary.get('years_operating', 'N/A')}

The section should cover:
1. Organization history and founding story
2. Mission and vision alignment with grant
3. Key programs and services
4. Track record of success (prior grants, outcomes)
5. Organizational capacity (staff, budget, partnerships)
6. Why we're qualified to execute this project

Create a detailed outline incorporating available data.
""",
            SectionType.STATEMENT_OF_NEED: f"""
Create an outline for a data-driven statement of need.

{base_context}

Available Community Data:
{self._format_community_data(context.get('community_data', {}))}

The statement should:
1. Open with compelling local story or statistic
2. Define the problem clearly
3. Present 3-5 key data points with sources
4. Show local vs. national comparisons
5. Explain why the need is urgent
6. Connect need to target population
7. Show gap in current services
8. Transition to proposed solution

Create an outline that weaves data into a compelling narrative.
""",
            SectionType.PROJECT_DESCRIPTION: f"""
Create an outline for a comprehensive project description.

{base_context}

Budget Total: ${summary.get('budget_total', 0):,.0f}
Funding Request: ${summary.get('budget_request', 0):,.0f}

The project description should include:
1. Project overview and purpose
2. Target population and selection criteria
3. Project activities (Phase 1, 2, 3)
4. Timeline with milestones
5. Staffing and roles
6. Partnerships and collaborations
7. Innovation or unique approach
8. Expected outputs and deliverables

Create a detailed outline with specific activities and timeline.
""",
            SectionType.GOALS_OBJECTIVES: f"""
Create an outline for SMART goals and objectives.

{base_context}

The section should include:
1. 2-3 overarching goals (broad outcomes)
2. 4-6 SMART objectives per goal:
   - Specific: What exactly will be accomplished?
   - Measurable: What metrics will track progress?
   - Achievable: Is this realistic?
   - Relevant: How does it connect to the need?
   - Time-bound: When will it be achieved?
3. Key performance indicators (KPIs)
4. Data collection methods for each objective

Create an outline with draft SMART objective language.
""",
            SectionType.EVALUATION_PLAN: f"""
Create an outline for a comprehensive evaluation plan.

{base_context}

The evaluation should cover:
1. Evaluation purpose and questions
2. Logic model summary (inputs → activities → outputs → outcomes)
3. Process evaluation methods
4. Outcome evaluation methods
5. Data collection tools and timeline
6. Data analysis approach
7. Use of findings for improvement
8. External evaluator (if applicable)

Create an outline with specific evaluation questions and methods.
""",
            SectionType.BUDGET_NARRATIVE: f"""
Create an outline for a detailed budget narrative.

{base_context}

Budget Summary:
{self._format_budget_summary(context.get('budget', {}))}

The narrative should:
1. Overview of budget alignment with project
2. Personnel costs justification
3. Fringe benefits explanation
4. Travel costs rationale
5. Equipment/supplies justification
6. Contractual services explanation
7. Other costs breakdown
8. Indirect costs (if applicable)
9. Cost reasonableness statement

Create an outline linking each cost category to project activities.
""",
            SectionType.SUSTAINABILITY_PLAN: f"""
Create an outline for a sustainability plan.

{base_context}

The plan should address:
1. Vision for project continuation
2. Diversified funding strategy
3. Revenue generation opportunities
4. Community and partner support
5. Organizational capacity building
6. Policy or systems change potential
7. Long-term impact preservation
8. Transition plan after grant ends

Create an outline with specific sustainability strategies.
""",
            SectionType.CONCLUSION: f"""
Create an outline for a compelling conclusion.

{base_context}

The conclusion should:
1. Restate the core need and solution
2. Summarize expected impact
3. Reinforce organizational qualifications
4. Express gratitude for consideration
5. Provide clear call to action
6. Include contact for follow-up

Create a concise outline for maximum impact.
""",
        }

        return outline_prompts.get(section_type, f"Create an outline for {section_type.value}")

    def _build_draft_prompt(
        self,
        section_type: SectionType,
        context: Dict[str, Any],
        outline: str,
        config: Dict[str, Any]
    ) -> str:
        """Build prompt for full draft generation."""
        summary = context.get("summary", {})
        min_words = config.get("min_words", 300)
        max_words = config.get("max_words", 600)

        base_context = self._format_base_context(context)

        # Include evidence based on section type
        evidence_context = ""
        if section_type == SectionType.STATEMENT_OF_NEED:
            evidence_context = f"""
Community Data to Include:
{self._format_community_data_for_writing(context.get('community_data', {}))}
"""
        elif section_type in [SectionType.ORGANIZATIONAL_BACKGROUND, SectionType.EXECUTIVE_SUMMARY]:
            evidence_context = f"""
Prior Grant Success:
{self._format_prior_grants_for_writing(context.get('prior_grants', []))}

Key Achievements:
{self._format_achievements_for_writing(context.get('achievements', []))}
"""
        elif section_type == SectionType.BUDGET_NARRATIVE:
            evidence_context = f"""
Budget Details:
{self._format_budget_for_writing(context.get('budget', {}))}
"""

        return f"""
You are a professional grant writer with 20+ years of experience writing successful federal and foundation grants.
Write a {config.get('title', section_type.value)} section for this grant application.

{base_context}

{evidence_context}

OUTLINE TO FOLLOW:
{outline if outline else "Generate a logical structure based on best practices."}

REQUIREMENTS:
- Write {min_words}-{max_words} words
- Use professional, formal tone appropriate for federal grants
- Include specific data, statistics, and evidence where appropriate
- Use strong action verbs and clear, confident language
- Avoid jargon and ensure accessibility
- Create smooth transitions between paragraphs
- Every claim should be supported or supportable
- DO NOT use placeholder text like [insert here] - write complete content

Write the complete {config.get('title', section_type.value)} section now:
"""

    def _build_refinement_prompt(
        self,
        section_type: SectionType,
        draft: str,
        context: Dict[str, Any],
        config: Dict[str, Any]
    ) -> str:
        """Build prompt for content refinement."""
        return f"""
You are a senior grant writing consultant reviewing and polishing a draft section.

DRAFT TO REFINE:
{draft}

REFINEMENT TASKS:
1. Improve flow and transitions between paragraphs
2. Strengthen weak arguments with more specific language
3. Ensure professional tone throughout
4. Fix any grammar, spelling, or punctuation issues
5. Ensure word count is within {config.get('min_words', 300)}-{config.get('max_words', 600)} words
6. Make the opening more compelling
7. Strengthen the closing
8. Ensure all statements sound confident and authoritative
9. Remove any redundancy or repetition

Do NOT change:
- Specific data points or statistics
- Organization name or key details
- Overall structure

Return the polished, refined version of the text:
"""

    def _format_base_context(self, context: Dict[str, Any]) -> str:
        """Format base organizational context."""
        org = context.get("organization", {})
        program = context.get("program", {})
        summary = context.get("summary", {})

        lines = [
            "ORGANIZATION CONTEXT:",
            f"Organization: {org.get('name', '[Organization]')}",
            f"Type: {org.get('type', 'nonprofit')}",
            f"Location: {org.get('location', '')}",
        ]

        if org.get("mission_statement"):
            lines.append(f"Mission: {org.get('mission_statement')}")

        if org.get("years_in_operation"):
            lines.append(f"Years in Operation: {org.get('years_in_operation')}")
        elif org.get("founding_year"):
            lines.append(f"Founded: {org.get('founding_year')}")

        if org.get("staff_count"):
            lines.append(f"Staff: {org.get('staff_count')}")

        if org.get("annual_budget"):
            lines.append(f"Annual Budget: ${org.get('annual_budget'):,.0f}")

        if org.get("clients_served_annually"):
            lines.append(f"Clients Served Annually: {org.get('clients_served_annually'):,}")

        lines.extend([
            "",
            "GRANT PROGRAM:",
            f"Program: {program.get('name', '')}",
            f"Agency: {program.get('agency', '')}",
            f"Funding Range: {summary.get('funding_range', '')}",
        ])

        if program.get("match_required"):
            lines.append(f"Match Required: {program.get('match_required') * 100:.0f}%")

        return "\n".join(lines)

    def _format_community_data(self, community_data: Dict[str, List]) -> str:
        """Format community data for outline prompt."""
        if not community_data:
            return "No community data available"

        lines = []
        for data_type, items in community_data.items():
            lines.append(f"\n{data_type.upper()}:")
            for item in items[:3]:  # Limit to 3 per category
                lines.append(f"  - {item.get('indicator')}: {item.get('statistic')} ({item.get('source')}, {item.get('source_year', '')})")
                if item.get("comparison_value"):
                    lines.append(f"    Comparison: {item.get('comparison_value')}")

        return "\n".join(lines) if lines else "No community data available"

    def _format_community_data_for_writing(self, community_data: Dict[str, List]) -> str:
        """Format community data for draft writing."""
        if not community_data:
            return "Use general statements about community need."

        lines = ["Incorporate these statistics naturally into the narrative:"]
        for data_type, items in community_data.items():
            for item in items:
                stat_line = f"- {item.get('indicator')}: {item.get('statistic')}"
                if item.get("comparison_value"):
                    stat_line += f" (vs. {item.get('comparison_value')})"
                stat_line += f" - Source: {item.get('source')}"
                if item.get("source_year"):
                    stat_line += f", {item.get('source_year')}"
                lines.append(stat_line)

        return "\n".join(lines)

    def _format_prior_grants_for_writing(self, prior_grants: List[Dict]) -> str:
        """Format prior grants for writing."""
        if not prior_grants:
            return "No prior grant history documented."

        lines = []
        for grant in prior_grants[:5]:  # Top 5
            if grant.get("status") == "awarded":
                line = f"- {grant.get('funder_name')}"
                if grant.get("amount"):
                    line += f": ${grant.get('amount'):,.0f}"
                if grant.get("year"):
                    line += f" ({grant.get('year')})"
                if grant.get("outcomes_achieved"):
                    line += f"\n  Outcome: {grant.get('outcomes_achieved')[:150]}..."
                lines.append(line)

        return "\n".join(lines) if lines else "No prior grants to highlight."

    def _format_achievements_for_writing(self, achievements: List[Dict]) -> str:
        """Format achievements for writing."""
        if not achievements:
            return "No specific achievements documented."

        lines = []
        for ach in achievements[:5]:
            line = f"- {ach.get('title')}"
            if ach.get("metric_value") and ach.get("metric_unit"):
                line += f": {ach.get('metric_value'):,.0f} {ach.get('metric_unit')}"
            if ach.get("year"):
                line += f" ({ach.get('year')})"
            lines.append(line)

        return "\n".join(lines)

    def _format_budget_summary(self, budget: Dict[str, Any]) -> str:
        """Format budget summary for outline."""
        lines = [
            f"Total Request: ${budget.get('total_request', 0):,.0f}",
            f"Total Match: ${budget.get('total_match', 0):,.0f}",
            f"Grand Total: ${budget.get('grand_total', 0):,.0f}",
            "",
            "By Category:"
        ]

        for category, items in budget.get("by_category", {}).items():
            category_total = sum(item.get("total", 0) for item in items)
            lines.append(f"  {category}: ${category_total:,.0f}")

        return "\n".join(lines)

    def _format_budget_for_writing(self, budget: Dict[str, Any]) -> str:
        """Format budget details for budget narrative writing."""
        lines = []
        for category, items in budget.get("by_category", {}).items():
            lines.append(f"\n{category.upper()}:")
            for item in items:
                line = f"  - {item.get('description')}: ${item.get('total', 0):,.0f}"
                if item.get("justification"):
                    line += f"\n    Justification: {item.get('justification')}"
                lines.append(line)

        return "\n".join(lines) if lines else "No budget details available."

    async def _save_section(
        self,
        application_id: str,
        section_type: SectionType,
        content: str,
        word_count: int
    ):
        """Save generated section to database."""
        try:
            # Check for existing section
            existing = self.db.query(ApplicationSection).filter(
                ApplicationSection.application_id == application_id,
                ApplicationSection.section_type == section_type
            ).first()

            if existing:
                existing.content = content
                existing.word_count = word_count
                existing.version += 1
                existing.generation_model = self.MODEL_NAME
                existing.updated_at = datetime.utcnow()
            else:
                section = ApplicationSection(
                    application_id=application_id,
                    section_type=section_type,
                    content=content,
                    word_count=word_count,
                    generation_model=self.MODEL_NAME,
                )
                self.db.add(section)

            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save section: {e}")
            self.db.rollback()

    def _get_fallback_content(self, section_type: SectionType, context: Dict[str, Any]) -> str:
        """Return professional template when AI is unavailable."""
        org_name = context.get("summary", {}).get("organization_name", "[Organization Name]")
        program_name = context.get("program", {}).get("name", "[Grant Program]")

        fallbacks = {
            SectionType.COVER_LETTER: f"""
Dear Grant Review Committee,

{org_name} is pleased to submit this application for the {program_name} opportunity. Our organization has a demonstrated commitment to serving our community, and this funding would significantly enhance our capacity to deliver meaningful outcomes.

We believe our track record, expertise, and strategic approach align well with the program's objectives. This application outlines our proposed project, expected outcomes, and organizational qualifications.

We welcome the opportunity to discuss this proposal further and answer any questions you may have.

Respectfully submitted,

[Authorized Official Name]
[Title]
{org_name}
""",
            SectionType.EXECUTIVE_SUMMARY: f"""
{org_name} respectfully requests funding through the {program_name} to address critical needs in our service area. This project will [describe primary outcomes] through [brief methodology].

Our organization brings [X] years of experience in [relevant field], having successfully served [number] individuals and secured [amount] in prior grant funding. This demonstrated capacity positions us to execute the proposed project effectively.

With the requested funding, we will achieve [specific measurable outcomes] within [timeframe]. These outcomes directly align with [funder's] priorities and will create lasting positive impact in our community.
""",
            SectionType.ORGANIZATIONAL_BACKGROUND: f"""
{org_name} was founded in [year] with a mission to [mission statement]. Over [X] years, we have grown from [origins] to become a [current description] serving [geographic area].

Our organization currently operates [X] programs serving [number] individuals annually. Our team of [X] staff members and [X] volunteers brings expertise in [relevant areas].

We have successfully managed [amount] in grant funding from sources including [funders], demonstrating our capacity for fiscal responsibility and program delivery. Key accomplishments include [achievements].

Our strategic partnerships with [partners] strengthen our ability to serve the community effectively. This infrastructure positions us well to implement the proposed project.
""",
            SectionType.STATEMENT_OF_NEED: f"""
[Geographic area] faces significant challenges that demand immediate attention. According to [source], [key statistic] of residents experience [problem], compared to [comparison statistic] nationally.

The root causes of this disparity include [factors]. These conditions disproportionately affect [target population], creating barriers to [outcomes].

Current services in the region are insufficient to meet demand. [Evidence of service gap]. Without intervention, these conditions will continue to [negative trajectory].

{org_name}'s proposed project directly addresses this need through [approach], targeting the most affected populations with evidence-based strategies.
""",
            SectionType.PROJECT_DESCRIPTION: f"""
{org_name} proposes to implement [project name] to address [need] in [service area]. This [duration] project will serve [number] individuals through [methodology].

Project Activities:
Phase 1 (Months 1-3): [Activities]
Phase 2 (Months 4-9): [Activities]
Phase 3 (Months 10-12): [Activities]

Key personnel include [roles and qualifications]. Our partnership with [collaborators] provides [value].

The project incorporates evidence-based practices including [approaches], which have demonstrated effectiveness in similar settings.

Expected deliverables include [outputs]. These activities will result in [outcomes] for program participants.
""",
            SectionType.GOALS_OBJECTIVES: f"""
Goal 1: [Broad outcome statement]
- Objective 1.1: By [date], [X%] of participants will [measurable outcome], as measured by [data source].
- Objective 1.2: By [date], [number] participants will [measurable outcome], as documented by [method].

Goal 2: [Broad outcome statement]
- Objective 2.1: By [date], [X%] of participants will [measurable outcome], as measured by [data source].
- Objective 2.2: By [date], [number] participants will [measurable outcome], as documented by [method].

Performance will be tracked through [methods] with data reported [frequency].
""",
            SectionType.EVALUATION_PLAN: f"""
{org_name} will implement a comprehensive evaluation plan to assess both process and outcomes.

Evaluation Questions:
1. To what extent did the project achieve its stated objectives?
2. What factors facilitated or hindered success?
3. How can the program be improved for greater impact?

Methods:
- Process Evaluation: [methods for tracking implementation]
- Outcome Evaluation: [methods for measuring results]

Data Collection: [tools and timeline]

Analysis: Data will be analyzed [frequency] using [methods] to identify trends and inform continuous improvement.

Findings will be used to [application] and shared with [stakeholders].
""",
            SectionType.BUDGET_NARRATIVE: f"""
The proposed budget reflects the true costs of implementing this project effectively while demonstrating responsible stewardship of grant funds.

Personnel: Staff costs support [positions] essential for project implementation. Salaries are based on [methodology] and include [X]% fringe benefits.

Travel: Travel costs support [purpose]. Rates are based on [GSA/organizational] standards.

Supplies: Materials support [activities] and are necessary for [outcomes].

Contractual: [Contracted services] provide [value/expertise] not available internally.

All costs are reasonable, allowable, and directly connected to achieving project objectives. Cost-sharing of [amount/percentage] demonstrates organizational commitment.
""",
            SectionType.SUSTAINABILITY_PLAN: f"""
{org_name} is committed to sustaining project outcomes beyond the grant period through multiple strategies:

Diversified Funding: We will pursue [funding sources] to continue operations. Our development plan includes [strategies].

Revenue Generation: [If applicable, describe earned revenue approaches]

Partnerships: Collaboration with [partners] will provide ongoing resources and support.

Capacity Building: Grant activities will strengthen organizational infrastructure through [specific improvements].

Systems Change: The project will contribute to [policy/practice changes] that create lasting impact.

By grant end, we will have established [sustainability mechanisms] to ensure continued service delivery.
""",
            SectionType.CONCLUSION: f"""
{org_name} is prepared to execute this project effectively and achieve meaningful outcomes for [target population]. Our experience, partnerships, and commitment position us as a strong steward of these funds.

This investment will result in [key outcomes], creating lasting positive change in our community. We are grateful for your consideration and confident in our ability to deliver on these promises.

We welcome the opportunity to discuss this proposal further. Please contact [name] at [email/phone] with questions.
""",
        }

        return fallbacks.get(section_type, f"[Please complete the {section_type.value} section]").strip()


# Factory function for creating service instance
def create_professional_writing_service(db: Session) -> ProfessionalAIWritingService:
    """Create a new ProfessionalAIWritingService instance."""
    return ProfessionalAIWritingService(db)
