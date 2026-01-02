"""
AI Writing Service for Grant Applications

Generates narrative content for grant applications using Google Gemini.
Provides writing assistance for various application sections.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

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

        # Generate each section
        section_types = [
            ("executive_summary", 200),
            ("statement_of_need", 400),
            ("project_description", 500),
            ("goals_and_objectives", 300),
            ("budget_justification", 300),
            ("sustainability_plan", 250),
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
        """Build a prompt for narrative generation."""

        org_name = context.get("organization_name") or context.get("full_name", "the organization")
        program_name = context.get("program_name", "this grant program")
        project_summary = context.get("project_summary", "")

        base_context = f"""
Organization: {org_name}
Organization Type: {context.get('organization_type', 'nonprofit')}
Location: {context.get('city', '')}, {context.get('state', '')}
Grant Program: {program_name}
Agency: {context.get('program_agency', '')}
"""

        if project_summary:
            base_context += f"\nProject Summary: {project_summary}"

        section_prompts = {
            "executive_summary": f"""
Write a compelling executive summary for a grant application.
{base_context}

The executive summary should:
- Briefly introduce the organization and its mission
- Clearly state the funding request and how it will be used
- Highlight the expected impact and outcomes
- Be persuasive and engaging

Write approximately {max_words} words in a {tone} tone.
""",
            "statement_of_need": f"""
Write a statement of need for a grant application.
{base_context}

The statement of need should:
- Describe the problem or gap being addressed
- Include relevant statistics or data if applicable
- Explain why this need is urgent or important
- Connect the need to the organization's mission
- Show understanding of the community being served

Write approximately {max_words} words in a {tone} tone.
""",
            "project_description": f"""
Write a project description for a grant application.
{base_context}

The project description should:
- Clearly explain what the project will accomplish
- Describe the activities and timeline
- Identify who will benefit and how
- Explain the methodology or approach
- Show how this project aligns with the funder's priorities

Write approximately {max_words} words in a {tone} tone.
""",
            "goals_and_objectives": f"""
Write goals and objectives for a grant application.
{base_context}

Include:
- 2-3 broad goals that describe the desired outcomes
- 3-5 SMART objectives (Specific, Measurable, Achievable, Relevant, Time-bound)
- Clear metrics for measuring success

Write approximately {max_words} words in a {tone} tone.
""",
            "budget_justification": f"""
Write a budget justification narrative for a grant application.
{base_context}
Funding Range: {context.get('funding_range', 'varies')}

The budget justification should:
- Explain why each major budget category is necessary
- Show how costs are reasonable and appropriate
- Demonstrate cost-effectiveness
- Align expenses with project activities

Write approximately {max_words} words in a {tone} tone.
""",
            "sustainability_plan": f"""
Write a sustainability plan for a grant application.
{base_context}

The sustainability plan should:
- Explain how the project will continue after grant funding ends
- Identify potential future funding sources
- Describe organizational capacity for long-term operation
- Show commitment to lasting impact

Write approximately {max_words} words in a {tone} tone.
""",
        }

        return section_prompts.get(section_type, f"Write a {section_type} section for a grant application.\n{base_context}")

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
        }

        return fallbacks.get(section_type, f"[Please write your {section_type} here]").strip()


# Singleton instance
ai_writing_service = AIWritingService()
