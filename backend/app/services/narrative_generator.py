"""
AI Narrative Generator Service using Claude API

Mobile-optimized service for generating grant application sections
with real-time feedback and quality scoring.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from sqlalchemy.orm import Session

from app.models import (
    ApplicationSection, SectionType, Application,
    UserProfile, OrganizationProfile, CommunityData,
    PriorGrant, Achievement, GrantProgram
)
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Anthropic client setup
try:
    import anthropic
    HAS_ANTHROPIC = bool(settings.anthropic_api_key)
except ImportError:
    HAS_ANTHROPIC = False
    anthropic = None


class GenerationTone(str, Enum):
    """Writing tone options."""
    PROFESSIONAL = "professional"
    COMPELLING = "compelling"
    DATA_DRIVEN = "data_driven"


# Section configurations
SECTION_CONFIG = {
    SectionType.STATEMENT_OF_NEED: {
        "title": "Statement of Need",
        "description": "Data-driven case for why funding is needed",
        "min_words": 400,
        "max_words": 800,
        "key_elements": [
            "Local statistics with sources",
            "Comparison to state/national data",
            "Impact on target population",
            "Current service gaps",
            "Urgency of the need"
        ]
    },
    SectionType.EXECUTIVE_SUMMARY: {
        "title": "Executive Summary",
        "description": "Compelling overview of your proposal",
        "min_words": 300,
        "max_words": 500,
        "key_elements": [
            "Hook/opening statement",
            "Organization introduction",
            "Problem summary",
            "Solution overview",
            "Funding request",
            "Expected outcomes"
        ]
    },
    SectionType.ORGANIZATIONAL_BACKGROUND: {
        "title": "Organizational Background",
        "description": "Your organization's credibility and track record",
        "min_words": 400,
        "max_words": 700,
        "key_elements": [
            "History and mission",
            "Key accomplishments",
            "Prior grant success",
            "Staff expertise",
            "Community partnerships"
        ]
    },
    SectionType.PROJECT_DESCRIPTION: {
        "title": "Project Description",
        "description": "Detailed plan for how you'll use the funding",
        "min_words": 500,
        "max_words": 1000,
        "key_elements": [
            "Project overview",
            "Target population",
            "Activities and timeline",
            "Staffing plan",
            "Innovation/unique approach"
        ]
    },
    SectionType.GOALS_OBJECTIVES: {
        "title": "Goals & Objectives",
        "description": "SMART goals with measurable outcomes",
        "min_words": 300,
        "max_words": 600,
        "key_elements": [
            "2-3 overarching goals",
            "SMART objectives for each",
            "Key performance indicators",
            "Data collection methods"
        ]
    },
    SectionType.EVALUATION_PLAN: {
        "title": "Evaluation Plan",
        "description": "How you'll measure and report success",
        "min_words": 300,
        "max_words": 600,
        "key_elements": [
            "Evaluation questions",
            "Data collection methods",
            "Analysis approach",
            "Reporting schedule",
            "Use of findings"
        ]
    },
    SectionType.BUDGET_NARRATIVE: {
        "title": "Budget Narrative",
        "description": "Justification for each expense",
        "min_words": 300,
        "max_words": 600,
        "key_elements": [
            "Personnel justification",
            "Operating costs rationale",
            "Equipment needs",
            "Cost reasonableness",
            "Match/leverage details"
        ]
    },
    SectionType.SUSTAINABILITY_PLAN: {
        "title": "Sustainability Plan",
        "description": "How the project will continue after funding",
        "min_words": 250,
        "max_words": 500,
        "key_elements": [
            "Diversified funding strategy",
            "Revenue generation",
            "Community support",
            "Long-term capacity building"
        ]
    },
    SectionType.COVER_LETTER: {
        "title": "Cover Letter",
        "description": "Professional introduction to your proposal",
        "min_words": 200,
        "max_words": 350,
        "key_elements": [
            "Formal greeting",
            "Funding request",
            "Organization credibility",
            "Alignment with funder",
            "Contact information"
        ]
    },
    SectionType.CONCLUSION: {
        "title": "Conclusion",
        "description": "Strong closing that reinforces your case",
        "min_words": 150,
        "max_words": 300,
        "key_elements": [
            "Restate the need",
            "Summarize impact",
            "Call to action",
            "Gratitude"
        ]
    }
}


class NarrativeGeneratorService:
    """
    Claude-powered narrative generator for grant applications.

    Provides:
    - Section-by-section generation
    - Quality feedback
    - Improvement suggestions
    - Mobile-optimized responses
    """

    MODEL = "claude-sonnet-4-20250514"

    def __init__(self, db: Session):
        self.db = db
        self.client = None

        if HAS_ANTHROPIC and settings.anthropic_api_key:
            try:
                self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

    def get_available_sections(self) -> List[Dict[str, Any]]:
        """Get list of available sections with metadata."""
        return [
            {
                "type": section_type.value,
                "title": config["title"],
                "description": config["description"],
                "min_words": config["min_words"],
                "max_words": config["max_words"],
                "key_elements": config["key_elements"]
            }
            for section_type, config in SECTION_CONFIG.items()
        ]

    async def generate_section(
        self,
        user_id: str,
        application_id: str,
        section_type: SectionType,
        additional_context: Optional[str] = None,
        tone: GenerationTone = GenerationTone.PROFESSIONAL
    ) -> Dict[str, Any]:
        """
        Generate a single section with Claude.

        Returns:
            Dict with content, word_count, quality_feedback, and suggestions
        """
        # Gather context
        context = self._gather_context(user_id, application_id)
        config = SECTION_CONFIG.get(section_type, {})

        if not self.client:
            # Return fallback content
            fallback = self._get_fallback_content(section_type, context)
            return {
                "content": fallback,
                "word_count": len(fallback.split()),
                "quality_score": 60,
                "quality_feedback": "Generated using template. Add more organizational data for better results.",
                "suggestions": [
                    "Add your organization's mission statement",
                    "Include prior grant history for credibility",
                    "Add community statistics for a stronger case"
                ],
                "model": "fallback"
            }

        # Build the prompt
        prompt = self._build_generation_prompt(
            section_type=section_type,
            context=context,
            config=config,
            additional_context=additional_context,
            tone=tone
        )

        try:
            # Generate with Claude
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text.strip()
            word_count = len(content.split())

            # Get quality feedback
            feedback = await self._get_quality_feedback(content, section_type, context)

            # Save to database
            await self._save_section(
                application_id=application_id,
                section_type=section_type,
                content=content,
                word_count=word_count,
                quality_score=feedback.get("score", 0)
            )

            return {
                "content": content,
                "word_count": word_count,
                "quality_score": feedback.get("score", 75),
                "quality_feedback": feedback.get("summary", ""),
                "suggestions": feedback.get("suggestions", []),
                "model": self.MODEL
            }

        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            fallback = self._get_fallback_content(section_type, context)
            return {
                "content": fallback,
                "word_count": len(fallback.split()),
                "quality_score": 50,
                "quality_feedback": f"AI generation failed. Using template. Error: {str(e)[:100]}",
                "suggestions": ["Try regenerating the section"],
                "model": "fallback"
            }

    async def improve_section(
        self,
        application_id: str,
        section_type: SectionType,
        current_content: str,
        improvement_focus: str
    ) -> Dict[str, Any]:
        """
        Improve an existing section based on feedback.

        Args:
            improvement_focus: What to improve (e.g., "add more data", "stronger opening")
        """
        if not self.client:
            return {
                "content": current_content,
                "word_count": len(current_content.split()),
                "quality_feedback": "Improvement requires AI service",
                "suggestions": []
            }

        config = SECTION_CONFIG.get(section_type, {})

        prompt = f"""You are a professional grant writer improving an existing section.

CURRENT SECTION ({config.get('title', section_type.value)}):
{current_content}

IMPROVEMENT REQUEST:
{improvement_focus}

REQUIREMENTS:
- Keep the core content and facts intact
- Focus specifically on the requested improvement
- Maintain professional grant writing tone
- Word count: {config.get('min_words', 300)}-{config.get('max_words', 600)} words

Return ONLY the improved section, no explanations."""

        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            improved = response.content[0].text.strip()

            return {
                "content": improved,
                "word_count": len(improved.split()),
                "quality_feedback": f"Improved based on: {improvement_focus}",
                "suggestions": []
            }

        except Exception as e:
            logger.error(f"Improvement failed: {e}")
            return {
                "content": current_content,
                "error": str(e)
            }

    async def _get_quality_feedback(
        self,
        content: str,
        section_type: SectionType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get quality feedback on generated content."""
        if not self.client:
            return {"score": 70, "summary": "Unable to analyze", "suggestions": []}

        config = SECTION_CONFIG.get(section_type, {})
        key_elements = config.get("key_elements", [])

        prompt = f"""Analyze this grant {config.get('title', 'section')} and provide quality feedback.

CONTENT:
{content}

KEY ELEMENTS TO CHECK:
{chr(10).join(f'- {e}' for e in key_elements)}

Respond in this exact JSON format:
{{
    "score": <0-100>,
    "summary": "<1 sentence summary of quality>",
    "suggestions": ["<improvement 1>", "<improvement 2>", "<improvement 3>"]
}}

Be constructive. Score 80+ if most key elements are present and well-written."""

        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            text = response.content[0].text.strip()
            # Extract JSON from response
            if "{" in text:
                json_str = text[text.find("{"):text.rfind("}")+1]
                return json.loads(json_str)

            return {"score": 75, "summary": "Generated successfully", "suggestions": []}

        except Exception as e:
            logger.warning(f"Quality feedback failed: {e}")
            return {"score": 75, "summary": "Generated successfully", "suggestions": []}

    def _gather_context(self, user_id: str, application_id: str) -> Dict[str, Any]:
        """Gather all relevant context for generation."""
        context = {
            "organization": {},
            "program": {},
            "community_data": [],
            "prior_grants": [],
            "achievements": []
        }

        # Get user profile
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        if profile:
            context["organization"] = {
                "name": profile.organization_name or profile.full_name or "",
                "type": profile.organization_type or "",
                "city": profile.city or "",
                "state": profile.state or "",
                "years_in_operation": profile.years_in_operation,
                "employee_count": profile.employee_count,
                "annual_revenue": profile.annual_revenue,
                "ein": profile.ein or "",
                "is_rural": profile.is_rural,
                "is_minority_owned": profile.is_minority_owned,
                "is_woman_owned": profile.is_woman_owned
            }

        # Get organization profile
        org_profile = self.db.query(OrganizationProfile).filter(
            OrganizationProfile.user_id == user_id
        ).first()

        if org_profile:
            context["organization"].update({
                "mission_statement": org_profile.mission_statement or "",
                "vision_statement": org_profile.vision_statement or "",
                "founding_year": org_profile.founding_year,
                "service_area": org_profile.service_area or "",
                "annual_budget": org_profile.annual_budget,
                "staff_count": org_profile.staff_count,
                "clients_served_annually": org_profile.clients_served_annually,
                "programs_offered": org_profile.programs_offered or ""
            })

        # Get application and program
        app = self.db.query(Application).filter(
            Application.id == application_id
        ).first()

        if app:
            program = self.db.query(GrantProgram).filter(
                GrantProgram.id == app.program_id
            ).first()

            if program:
                context["program"] = {
                    "name": program.name,
                    "agency": program.agency or "",
                    "category": program.category.value if program.category else "",
                    "min_award": program.min_award,
                    "max_award": program.max_award,
                    "match_required": program.match_required,
                    "description": program.description or "",
                    "eligibility_summary": program.eligibility_summary or ""
                }

        # Get community data
        community_data = self.db.query(CommunityData).filter(
            CommunityData.user_id == user_id
        ).all()

        context["community_data"] = [
            {
                "type": d.data_type.value if d.data_type else "other",
                "indicator": d.indicator,
                "statistic": d.statistic,
                "comparison": d.comparison_value,
                "source": d.source,
                "year": d.source_year
            }
            for d in community_data
        ]

        # Get prior grants
        prior_grants = self.db.query(PriorGrant).filter(
            PriorGrant.user_id == user_id
        ).order_by(PriorGrant.year_awarded.desc()).limit(5).all()

        context["prior_grants"] = [
            {
                "funder": g.funder_name,
                "amount": g.amount,
                "year": g.year_awarded,
                "outcomes": g.outcomes_achieved or ""
            }
            for g in prior_grants
        ]

        # Get achievements
        achievements = self.db.query(Achievement).filter(
            Achievement.user_id == user_id
        ).limit(5).all()

        context["achievements"] = [
            {
                "title": a.title,
                "value": a.metric_value,
                "unit": a.metric_unit,
                "year": a.year
            }
            for a in achievements
        ]

        return context

    def _build_generation_prompt(
        self,
        section_type: SectionType,
        context: Dict[str, Any],
        config: Dict[str, Any],
        additional_context: Optional[str],
        tone: GenerationTone
    ) -> str:
        """Build the generation prompt for Claude."""
        org = context.get("organization", {})
        program = context.get("program", {})
        community = context.get("community_data", [])
        prior_grants = context.get("prior_grants", [])
        achievements = context.get("achievements", [])

        # Format organization info
        org_info = f"""
ORGANIZATION:
- Name: {org.get('name', 'Our Organization')}
- Type: {org.get('type', 'nonprofit')}
- Location: {org.get('city', '')}, {org.get('state', '')}
- Mission: {org.get('mission_statement', 'Serving our community')}
"""
        if org.get('founding_year'):
            org_info += f"- Founded: {org['founding_year']}\n"
        if org.get('staff_count'):
            org_info += f"- Staff: {org['staff_count']} employees\n"
        if org.get('annual_budget'):
            org_info += f"- Annual Budget: ${org['annual_budget']:,.0f}\n"
        if org.get('clients_served_annually'):
            org_info += f"- Clients Served: {org['clients_served_annually']:,}/year\n"

        # Format program info
        program_info = f"""
GRANT PROGRAM:
- Name: {program.get('name', 'Grant Program')}
- Agency: {program.get('agency', '')}
- Funding Range: ${program.get('min_award', 0):,.0f} - ${program.get('max_award', 0):,.0f}
"""
        if program.get('match_required'):
            program_info += f"- Match Required: {program['match_required'] * 100:.0f}%\n"

        # Format community data
        community_info = ""
        if community:
            community_info = "\nCOMMUNITY DATA (use these statistics):\n"
            for d in community[:6]:
                community_info += f"- {d['indicator']}: {d['statistic']}"
                if d.get('comparison'):
                    community_info += f" (vs. {d['comparison']})"
                community_info += f" - Source: {d['source']}"
                if d.get('year'):
                    community_info += f", {d['year']}"
                community_info += "\n"

        # Format prior grants
        grants_info = ""
        if prior_grants:
            grants_info = "\nPRIOR GRANT SUCCESS:\n"
            for g in prior_grants[:3]:
                grants_info += f"- {g['funder']}: ${g['amount']:,.0f} ({g['year']})\n"
                if g.get('outcomes'):
                    grants_info += f"  Outcome: {g['outcomes'][:100]}...\n"

        # Format achievements
        achieve_info = ""
        if achievements:
            achieve_info = "\nKEY ACHIEVEMENTS:\n"
            for a in achievements[:3]:
                achieve_info += f"- {a['title']}"
                if a.get('value') and a.get('unit'):
                    achieve_info += f": {a['value']:,.0f} {a['unit']}"
                if a.get('year'):
                    achieve_info += f" ({a['year']})"
                achieve_info += "\n"

        # Tone instructions
        tone_instructions = {
            GenerationTone.PROFESSIONAL: "Use formal, professional language suitable for federal grants.",
            GenerationTone.COMPELLING: "Use persuasive, emotionally engaging language while maintaining professionalism.",
            GenerationTone.DATA_DRIVEN: "Lead with statistics and evidence, using data to support every claim."
        }

        prompt = f"""You are an expert grant writer with 20+ years of experience writing successful federal and foundation grants.

Write a {config.get('title', section_type.value)} section for this grant application.

{org_info}
{program_info}
{community_info}
{grants_info}
{achieve_info}

SECTION REQUIREMENTS:
- Title: {config.get('title', section_type.value)}
- Word count: {config.get('min_words', 300)}-{config.get('max_words', 600)} words
- Key elements to include:
{chr(10).join(f'  * {e}' for e in config.get('key_elements', []))}

WRITING STYLE:
{tone_instructions.get(tone, tone_instructions[GenerationTone.PROFESSIONAL])}

CRITICAL RULES:
1. Use ONLY the data provided above - do not invent statistics or facts
2. NEVER use placeholder text like [Organization Name] or [insert here]
3. Write complete, polished content ready for submission
4. Every claim should be supported by the data provided
5. If data is missing, write general but confident statements

{f'ADDITIONAL CONTEXT: {additional_context}' if additional_context else ''}

Write the complete {config.get('title', section_type.value)} section now:"""

        return prompt

    async def _save_section(
        self,
        application_id: str,
        section_type: SectionType,
        content: str,
        word_count: int,
        quality_score: float = 0
    ):
        """Save generated section to database."""
        try:
            existing = self.db.query(ApplicationSection).filter(
                ApplicationSection.application_id == application_id,
                ApplicationSection.section_type == section_type
            ).first()

            if existing:
                existing.content = content
                existing.word_count = word_count
                existing.quality_score = quality_score
                existing.version += 1
                existing.generation_model = self.MODEL
                existing.updated_at = datetime.utcnow()
            else:
                section = ApplicationSection(
                    application_id=application_id,
                    section_type=section_type,
                    content=content,
                    word_count=word_count,
                    quality_score=quality_score,
                    generation_model=self.MODEL
                )
                self.db.add(section)

            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save section: {e}")
            self.db.rollback()

    def _get_fallback_content(self, section_type: SectionType, context: Dict[str, Any]) -> str:
        """Generate fallback content when AI is unavailable."""
        org = context.get("organization", {})
        program = context.get("program", {})

        org_name = org.get("name", "Our organization")
        location = f"{org.get('city', '')}, {org.get('state', '')}".strip(", ") or "our community"
        mission = org.get("mission_statement", "serving those in need")
        program_name = program.get("name", "this grant program")

        templates = {
            SectionType.STATEMENT_OF_NEED: f"""{location} faces significant challenges that directly impact community members. {org_name} has worked within this community and witnessed firsthand the growing need for services.

Our service area experiences higher-than-average rates of poverty and unemployment, creating barriers to stability for families and individuals. These challenges disproportionately affect vulnerable populations.

Without intervention, these trends will continue to worsen. {org_name} is positioned to address these needs through our established programs and deep community relationships. The proposed project will create pathways to improved outcomes for those we serve.""",

            SectionType.EXECUTIVE_SUMMARY: f"""{org_name} respectfully requests funding through {program_name} to address critical needs in {location}.

Our organization has built a strong track record of {mission}. With dedicated staff and demonstrated financial capacity, we have the organizational strength to execute this project effectively.

The proposed project will directly benefit our community by expanding our capacity to serve those most in need. We are confident that this investment will generate meaningful, lasting impact.""",

            SectionType.ORGANIZATIONAL_BACKGROUND: f"""{org_name} was established with a mission of {mission}. Since our founding, we have grown to serve an expanding community with dedicated programs and services.

Our organization maintains strong financial management practices and has built the infrastructure necessary for responsible growth. Our leadership team brings significant experience in nonprofit management and community engagement.

These qualities, combined with our deep roots in {location}, position us to effectively implement the proposed project and deliver meaningful results."""
        }

        return templates.get(section_type, f"{org_name} is committed to excellence in serving {location}. Through {program_name}, we will expand our impact and serve more community members in need.")


def create_narrative_generator(db: Session) -> NarrativeGeneratorService:
    """Factory function to create NarrativeGeneratorService instance."""
    return NarrativeGeneratorService(db)
