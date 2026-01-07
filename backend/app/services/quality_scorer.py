"""
Quality Scoring Service for Grant Applications

Evaluates grant application sections against professional standards
and provides improvement suggestions.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import ApplicationSection, SectionType

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


@dataclass
class SectionScore:
    """Score for a single section."""
    section_type: str
    overall_score: float
    relevance_score: float
    evidence_score: float
    writing_score: float
    completeness_score: float
    feedback: str
    strengths: List[str]
    improvements: List[str]


@dataclass
class ApplicationScore:
    """Overall application score."""
    overall_score: float
    section_scores: Dict[str, SectionScore]
    strengths: List[str]
    critical_improvements: List[str]
    ready_for_submission: bool


# Section-specific scoring criteria
SCORING_CRITERIA = {
    SectionType.COVER_LETTER: {
        "min_words": 200,
        "max_words": 450,
        "required_elements": ["greeting", "funding request", "organizational credibility", "contact information"],
        "key_phrases": ["respectfully", "request", "funding", "mission", "impact"],
    },
    SectionType.EXECUTIVE_SUMMARY: {
        "min_words": 350,
        "max_words": 650,
        "required_elements": ["problem statement", "solution", "funding amount", "expected outcomes"],
        "key_phrases": ["impact", "outcomes", "serve", "community", "measurable"],
    },
    SectionType.ORGANIZATIONAL_BACKGROUND: {
        "min_words": 450,
        "max_words": 850,
        "required_elements": ["history", "mission", "programs", "track record", "capacity"],
        "key_phrases": ["founded", "mission", "served", "experience", "capacity"],
    },
    SectionType.STATEMENT_OF_NEED: {
        "min_words": 500,
        "max_words": 1100,
        "required_elements": ["problem definition", "statistics", "target population", "urgency"],
        "key_phrases": ["according to", "percent", "data", "need", "gap", "compared to"],
    },
    SectionType.PROJECT_DESCRIPTION: {
        "min_words": 700,
        "max_words": 1600,
        "required_elements": ["activities", "timeline", "staffing", "methodology"],
        "key_phrases": ["implement", "activities", "phase", "timeline", "staff", "deliver"],
    },
    SectionType.GOALS_OBJECTIVES: {
        "min_words": 350,
        "max_words": 750,
        "required_elements": ["goals", "SMART objectives", "metrics"],
        "key_phrases": ["by", "percent", "will", "measured", "objective", "goal"],
    },
    SectionType.EVALUATION_PLAN: {
        "min_words": 350,
        "max_words": 750,
        "required_elements": ["evaluation questions", "methods", "data collection", "analysis"],
        "key_phrases": ["evaluate", "measure", "data", "track", "assess", "indicators"],
    },
    SectionType.BUDGET_NARRATIVE: {
        "min_words": 350,
        "max_words": 850,
        "required_elements": ["personnel", "justification", "cost reasonableness"],
        "key_phrases": ["cost", "budget", "necessary", "support", "reasonable"],
    },
    SectionType.SUSTAINABILITY_PLAN: {
        "min_words": 250,
        "max_words": 650,
        "required_elements": ["future funding", "partnerships", "capacity building"],
        "key_phrases": ["sustain", "continue", "funding", "partnership", "long-term"],
    },
    SectionType.CONCLUSION: {
        "min_words": 125,
        "max_words": 350,
        "required_elements": ["summary", "call to action", "contact information"],
        "key_phrases": ["grateful", "impact", "confident", "contact", "welcome"],
    },
}


class QualityScorer:
    """
    Evaluates grant application sections for quality and completeness.
    """

    MODEL_NAME = "gemini-2.0-flash"

    def __init__(self, db: Session):
        self.db = db
        self.client = None
        if HAS_GEMINI and GOOGLE_API_KEY:
            try:
                self.client = genai.Client(api_key=GOOGLE_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    async def score_application(
        self,
        application_id: str,
        program_context: Optional[Dict[str, Any]] = None
    ) -> ApplicationScore:
        """
        Score an entire application.

        Args:
            application_id: The application to score
            program_context: Optional grant program context for relevance scoring

        Returns:
            ApplicationScore with overall and per-section scores
        """
        sections = self.db.query(ApplicationSection).filter(
            ApplicationSection.application_id == application_id
        ).all()

        section_scores = {}
        total_score = 0
        scored_count = 0

        for section in sections:
            score = await self.score_section(section, program_context)
            section_scores[section.section_type.value] = score
            total_score += score.overall_score
            scored_count += 1

            # Update section in database
            section.quality_score = score.overall_score
            section.relevance_score = score.relevance_score
            section.evidence_score = score.evidence_score
            section.ai_feedback = score.feedback

        self.db.commit()

        # Calculate overall score
        overall_score = total_score / scored_count if scored_count > 0 else 0

        # Compile strengths and improvements
        all_strengths = []
        all_improvements = []
        for score in section_scores.values():
            all_strengths.extend(score.strengths[:2])  # Top 2 from each
            all_improvements.extend(score.improvements[:2])

        # Sort improvements by priority (low-scoring sections first)
        critical_improvements = sorted(
            all_improvements,
            key=lambda x: next(
                (s.overall_score for s in section_scores.values()
                 if any(imp in x for imp in s.improvements)),
                50
            )
        )[:5]

        return ApplicationScore(
            overall_score=overall_score,
            section_scores=section_scores,
            strengths=list(set(all_strengths))[:5],
            critical_improvements=critical_improvements,
            ready_for_submission=overall_score >= 80 and all(
                s.overall_score >= 70 for s in section_scores.values()
            )
        )

    async def score_section(
        self,
        section: ApplicationSection,
        program_context: Optional[Dict[str, Any]] = None
    ) -> SectionScore:
        """
        Score a single section.

        Args:
            section: The section to score
            program_context: Optional grant program context

        Returns:
            SectionScore with detailed scoring and feedback
        """
        content = section.content or ""
        section_type = section.section_type
        criteria = SCORING_CRITERIA.get(section_type, {})

        # Rule-based scoring
        word_count = len(content.split())
        completeness_score = self._score_completeness(content, word_count, criteria)
        evidence_score = self._score_evidence(content, section_type)
        writing_score = self._score_writing_quality(content)

        # AI-based relevance and quality scoring
        if self.client and content:
            ai_scores = await self._get_ai_scores(content, section_type, program_context)
            relevance_score = ai_scores.get("relevance", 70)
            ai_feedback = ai_scores.get("feedback", "")
            strengths = ai_scores.get("strengths", [])
            improvements = ai_scores.get("improvements", [])
        else:
            relevance_score = 70  # Default
            ai_feedback = self._generate_rule_based_feedback(content, section_type, criteria)
            strengths, improvements = self._get_rule_based_suggestions(
                content, section_type, criteria, word_count
            )

        # Calculate overall score (weighted average)
        overall_score = (
            relevance_score * 0.25 +
            evidence_score * 0.25 +
            writing_score * 0.25 +
            completeness_score * 0.25
        )

        return SectionScore(
            section_type=section_type.value,
            overall_score=round(overall_score, 1),
            relevance_score=round(relevance_score, 1),
            evidence_score=round(evidence_score, 1),
            writing_score=round(writing_score, 1),
            completeness_score=round(completeness_score, 1),
            feedback=ai_feedback,
            strengths=strengths,
            improvements=improvements,
        )

    def _score_completeness(
        self,
        content: str,
        word_count: int,
        criteria: Dict[str, Any]
    ) -> float:
        """Score based on word count and required elements."""
        if not content:
            return 0

        score = 50  # Base score

        # Word count scoring
        min_words = criteria.get("min_words", 200)
        max_words = criteria.get("max_words", 600)

        if word_count < min_words * 0.5:
            score -= 30
        elif word_count < min_words:
            score -= 15
        elif min_words <= word_count <= max_words:
            score += 25
        elif word_count > max_words * 1.2:
            score -= 10

        # Required elements scoring
        required_elements = criteria.get("required_elements", [])
        elements_found = 0
        content_lower = content.lower()

        for element in required_elements:
            # Check for element presence (simplified)
            element_words = element.lower().split()
            if any(word in content_lower for word in element_words):
                elements_found += 1

        if required_elements:
            element_ratio = elements_found / len(required_elements)
            score += element_ratio * 25

        return min(100, max(0, score))

    def _score_evidence(self, content: str, section_type: SectionType) -> float:
        """Score based on use of evidence and data."""
        if not content:
            return 0

        score = 50

        # Check for statistics and numbers
        number_pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?(?:%|percent)?\b'
        numbers_found = len(re.findall(number_pattern, content))

        if numbers_found >= 5:
            score += 25
        elif numbers_found >= 3:
            score += 15
        elif numbers_found >= 1:
            score += 5

        # Check for citations/sources
        citation_patterns = [
            r'according to',
            r'based on',
            r'data from',
            r'source:',
            r'census',
            r'survey',
            r'study',
            r'report',
        ]

        citations_found = sum(
            1 for pattern in citation_patterns
            if re.search(pattern, content, re.IGNORECASE)
        )

        if citations_found >= 3:
            score += 25
        elif citations_found >= 2:
            score += 15
        elif citations_found >= 1:
            score += 5

        # Adjust expectations by section type
        if section_type == SectionType.STATEMENT_OF_NEED:
            # Higher expectations for data
            if numbers_found < 3:
                score -= 15
        elif section_type in [SectionType.COVER_LETTER, SectionType.CONCLUSION]:
            # Lower expectations for data
            score = min(score + 10, 100)

        return min(100, max(0, score))

    def _score_writing_quality(self, content: str) -> float:
        """Score writing quality using heuristics."""
        if not content:
            return 0

        score = 60  # Base score

        # Check paragraph structure
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) >= 3:
            score += 10
        elif len(paragraphs) == 1:
            score -= 10

        # Check sentence variety
        sentences = re.split(r'[.!?]+', content)
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 12 <= avg_sentence_length <= 25:
                score += 10
            elif avg_sentence_length < 8 or avg_sentence_length > 35:
                score -= 10

        # Check for weak language
        weak_phrases = [
            'very', 'really', 'basically', 'actually', 'just',
            'i think', 'we hope', 'we believe', 'maybe', 'probably'
        ]
        content_lower = content.lower()
        weak_count = sum(1 for phrase in weak_phrases if phrase in content_lower)
        if weak_count > 5:
            score -= 15
        elif weak_count > 2:
            score -= 5

        # Check for strong action verbs
        strong_verbs = [
            'implement', 'achieve', 'deliver', 'establish', 'create',
            'develop', 'provide', 'serve', 'increase', 'reduce',
            'expand', 'strengthen', 'demonstrate', 'ensure', 'engage'
        ]
        strong_count = sum(1 for verb in strong_verbs if verb in content_lower)
        if strong_count >= 5:
            score += 15
        elif strong_count >= 3:
            score += 10

        # Check for professional tone
        unprofessional_patterns = [
            r'\b(gonna|wanna|gotta|kinda|sorta)\b',
            r'!!+',
            r'\?\?+',
            r'\.\.\.+',
        ]
        for pattern in unprofessional_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                score -= 10

        return min(100, max(0, score))

    async def _get_ai_scores(
        self,
        content: str,
        section_type: SectionType,
        program_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get AI-powered quality assessment."""
        if not self.client:
            return {}

        program_info = ""
        if program_context:
            program_info = f"""
Grant Program: {program_context.get('name', '')}
Agency: {program_context.get('agency', '')}
Category: {program_context.get('category', '')}
"""

        prompt = f"""
Evaluate this {section_type.value.replace('_', ' ')} section from a grant application.
Provide a quality assessment.

{program_info}

CONTENT TO EVALUATE:
{content[:3000]}  # Limit content length

Provide your assessment in this exact format:
RELEVANCE_SCORE: [0-100]
FEEDBACK: [2-3 sentences of specific feedback]
STRENGTHS:
- [strength 1]
- [strength 2]
IMPROVEMENTS:
- [improvement 1]
- [improvement 2]
"""

        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                )
            )

            return self._parse_ai_response(response.text)
        except Exception as e:
            logger.warning(f"AI scoring failed: {e}")
            return {}

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI scoring response."""
        result = {
            "relevance": 70,
            "feedback": "",
            "strengths": [],
            "improvements": [],
        }

        try:
            # Extract relevance score
            relevance_match = re.search(r'RELEVANCE_SCORE:\s*(\d+)', response)
            if relevance_match:
                result["relevance"] = min(100, int(relevance_match.group(1)))

            # Extract feedback
            feedback_match = re.search(r'FEEDBACK:\s*(.+?)(?=STRENGTHS:|$)', response, re.DOTALL)
            if feedback_match:
                result["feedback"] = feedback_match.group(1).strip()

            # Extract strengths
            strengths_match = re.search(r'STRENGTHS:\s*(.+?)(?=IMPROVEMENTS:|$)', response, re.DOTALL)
            if strengths_match:
                strengths_text = strengths_match.group(1)
                result["strengths"] = [
                    s.strip().lstrip('- ')
                    for s in strengths_text.split('\n')
                    if s.strip() and s.strip() != '-'
                ][:3]

            # Extract improvements
            improvements_match = re.search(r'IMPROVEMENTS:\s*(.+?)$', response, re.DOTALL)
            if improvements_match:
                improvements_text = improvements_match.group(1)
                result["improvements"] = [
                    s.strip().lstrip('- ')
                    for s in improvements_text.split('\n')
                    if s.strip() and s.strip() != '-'
                ][:3]

        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")

        return result

    def _generate_rule_based_feedback(
        self,
        content: str,
        section_type: SectionType,
        criteria: Dict[str, Any]
    ) -> str:
        """Generate feedback without AI."""
        if not content:
            return "This section is empty and needs content."

        word_count = len(content.split())
        min_words = criteria.get("min_words", 200)
        max_words = criteria.get("max_words", 600)

        feedback_parts = []

        if word_count < min_words:
            feedback_parts.append(
                f"The section is under the recommended minimum of {min_words} words. "
                "Consider expanding with more detail and evidence."
            )
        elif word_count > max_words:
            feedback_parts.append(
                f"The section exceeds the recommended {max_words} words. "
                "Consider condensing to focus on key points."
            )
        else:
            feedback_parts.append("The section length is appropriate.")

        return " ".join(feedback_parts)

    def _get_rule_based_suggestions(
        self,
        content: str,
        section_type: SectionType,
        criteria: Dict[str, Any],
        word_count: int
    ) -> tuple:
        """Generate strengths and improvements without AI."""
        strengths = []
        improvements = []

        if not content:
            improvements.append("Add content to this section")
            return strengths, improvements

        min_words = criteria.get("min_words", 200)
        max_words = criteria.get("max_words", 600)

        # Check word count
        if min_words <= word_count <= max_words:
            strengths.append("Appropriate section length")
        elif word_count < min_words:
            improvements.append(f"Expand to at least {min_words} words")

        # Check for statistics
        if re.search(r'\d+(?:%|percent)', content, re.IGNORECASE):
            strengths.append("Includes quantitative data")
        elif section_type == SectionType.STATEMENT_OF_NEED:
            improvements.append("Add statistics to strengthen the case")

        # Check paragraph structure
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) >= 3:
            strengths.append("Well-structured with clear paragraphs")
        else:
            improvements.append("Break content into more paragraphs for readability")

        return strengths[:3], improvements[:3]


def create_quality_scorer(db: Session) -> QualityScorer:
    """Create a new QualityScorer instance."""
    return QualityScorer(db)
