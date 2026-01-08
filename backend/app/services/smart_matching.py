"""
Smart Grant Matching Engine

Probabilistic matching that goes beyond binary eligibility to calculate:
1. Eligibility Score (0-100) - Does org meet requirements?
2. Fit Score (0-100) - How well does org align with grant goals?
3. Combined Match Score with explanations

Uses data from:
- User profile (org type, location, 501c3 status, etc.)
- Smart profile data (Census demographics, rural status)
- Grant requirements (from Grants.gov XML)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.orm import Session

from app.models.database import (
    GrantProgram, GrantCategory, UserProfile,
    OrganizationProfile, User
)
from app.services.smart_profile import (
    SmartProfileService, SmartProfileData,
    CommunityDemographics, RuralStatus
)

logger = logging.getLogger(__name__)


# =============================================================================
# ELIGIBILITY CODE MAPPINGS (from Grants.gov)
# =============================================================================

class ApplicantType(str, Enum):
    """Standard applicant types for grant eligibility."""
    STATE_GOV = "state_government"
    COUNTY_GOV = "county_government"
    CITY_GOV = "city_government"
    TRIBAL_GOV = "tribal_government"
    NONPROFIT_501C3 = "nonprofit_501c3"
    NONPROFIT_OTHER = "nonprofit_other"
    HIGHER_ED_PUBLIC = "higher_ed_public"
    HIGHER_ED_PRIVATE = "higher_ed_private"
    INDIVIDUAL = "individual"
    SMALL_BUSINESS = "small_business"
    FOR_PROFIT = "for_profit"
    OTHER = "other"


# Map Grants.gov codes to our types
GRANTS_GOV_ELIGIBILITY_CODES = {
    "00": ApplicantType.STATE_GOV,
    "01": ApplicantType.COUNTY_GOV,
    "02": ApplicantType.CITY_GOV,
    "04": ApplicantType.STATE_GOV,  # Special district
    "05": ApplicantType.STATE_GOV,  # School district
    "06": ApplicantType.HIGHER_ED_PUBLIC,
    "07": ApplicantType.TRIBAL_GOV,
    "08": ApplicantType.STATE_GOV,  # Housing authority
    "11": ApplicantType.TRIBAL_GOV,  # Tribal org
    "12": ApplicantType.NONPROFIT_501C3,
    "13": ApplicantType.NONPROFIT_OTHER,
    "20": ApplicantType.HIGHER_ED_PRIVATE,
    "21": ApplicantType.INDIVIDUAL,
    "22": ApplicantType.FOR_PROFIT,
    "23": ApplicantType.SMALL_BUSINESS,
    "25": ApplicantType.OTHER,
    "99": ApplicantType.OTHER,  # Unrestricted
}

# Map user-friendly org types to Grants.gov eligible codes
ORG_TYPE_TO_ELIGIBLE_CODES = {
    "nonprofit": ["12", "13", "99"],
    "501c3": ["12", "99"],
    "small_business": ["23", "22", "99"],
    "for_profit": ["22", "23", "99"],
    "individual": ["21", "99"],
    "government": ["00", "01", "02", "04", "05", "08", "99"],
    "tribal": ["07", "11", "99"],
    "university": ["06", "20", "99"],
    "higher_education": ["06", "20", "99"],
}


# =============================================================================
# CATEGORY MAPPINGS
# =============================================================================

CATEGORY_TO_GRANTS_GOV = {
    GrantCategory.HEALTHCARE: ["HL", "HU"],
    GrantCategory.EDUCATION: ["ED"],
    GrantCategory.SMALL_BUSINESS: ["BC"],
    GrantCategory.AGRICULTURE: ["AG", "FN"],
    GrantCategory.TECHNOLOGY: ["ST"],
    GrantCategory.HOUSING: ["HO"],
    GrantCategory.NONPROFIT: ["CD", "ISS", "O"],
}

NTEE_TO_GRANT_CATEGORY = {
    "E": GrantCategory.HEALTHCARE,  # Health
    "F": GrantCategory.HEALTHCARE,  # Mental health
    "G": GrantCategory.HEALTHCARE,  # Disease
    "H": GrantCategory.HEALTHCARE,  # Medical research
    "B": GrantCategory.EDUCATION,   # Education
    "K": GrantCategory.AGRICULTURE, # Food/Agriculture
    "L": GrantCategory.HOUSING,     # Housing
    "U": GrantCategory.TECHNOLOGY,  # Science/Tech
    "P": GrantCategory.NONPROFIT,   # Human services
    "S": GrantCategory.NONPROFIT,   # Community
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MatchReason:
    """A reason explaining part of a match score."""
    factor: str
    points: int
    explanation: str
    is_positive: bool = True


@dataclass
class MatchResult:
    """Result of matching a user profile to a grant program."""
    program_id: str
    program_name: str
    agency: str
    category: str

    # Scores
    eligibility_score: int  # 0-100: Do they meet requirements?
    fit_score: int          # 0-100: How well do they align?
    match_score: int        # 0-100: Combined score

    # Details
    eligible: bool
    match_level: str        # "excellent", "good", "fair", "poor"
    reasons: List[MatchReason] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Grant details
    min_award: Optional[float] = None
    max_award: Optional[float] = None
    deadline: Optional[str] = None
    program_url: Optional[str] = None


@dataclass
class SmartMatchRequest:
    """Request for smart matching."""
    # Basic profile
    org_name: Optional[str] = None
    org_type: Optional[str] = None  # nonprofit, small_business, individual, etc.
    ein: Optional[str] = None
    is_501c3: Optional[bool] = None

    # Location
    zip_code: Optional[str] = None
    state: Optional[str] = None

    # Federal registration
    sam_registered: Optional[bool] = None
    uei_number: Optional[str] = None

    # Preferences
    sector: Optional[str] = None  # healthcare, education, etc.
    min_funding: Optional[float] = None
    max_funding: Optional[float] = None

    # Enhanced data (from smart profile lookup)
    smart_profile: Optional[SmartProfileData] = None


# =============================================================================
# SMART MATCHING ENGINE
# =============================================================================

class SmartMatchingEngine:
    """
    Probabilistic grant matching engine.

    Calculates match scores based on:
    1. Hard eligibility (org type, 501c3, SAM registration)
    2. Soft fit (sector alignment, funding range, geography)
    3. Community need boost (high poverty, rural areas)
    """

    def __init__(self, db: Session):
        self.db = db
        self.profile_service = SmartProfileService()

    def match_grants(
        self,
        request: SmartMatchRequest,
        limit: int = 10,
        min_score: int = 30,
    ) -> List[MatchResult]:
        """
        Find best matching grants for a user profile.

        Args:
            request: SmartMatchRequest with user profile data
            limit: Max number of results to return
            min_score: Minimum match score threshold

        Returns:
            List of MatchResult sorted by match_score descending
        """
        # Enrich request with smart profile data if not already present
        if not request.smart_profile and (request.org_name or request.zip_code or request.ein):
            request.smart_profile = self.profile_service.enrich_profile(
                org_name=request.org_name,
                ein=request.ein,
                zip_code=request.zip_code,
                state=request.state,
            )

        # Get active grant programs
        programs = self.db.query(GrantProgram).filter(
            GrantProgram.is_active == True
        ).all()

        # Score each program
        results = []
        for program in programs:
            result = self._score_program(program, request)
            if result.match_score >= min_score:
                results.append(result)

        # Sort by match score descending
        results.sort(key=lambda r: r.match_score, reverse=True)

        return results[:limit]

    def match_single_program(
        self,
        program_id: str,
        request: SmartMatchRequest,
    ) -> Optional[MatchResult]:
        """Score a single program against a user profile."""
        program = self.db.query(GrantProgram).filter(
            GrantProgram.id == program_id
        ).first()

        if not program:
            return None

        # Enrich with smart profile if needed
        if not request.smart_profile and (request.org_name or request.zip_code or request.ein):
            request.smart_profile = self.profile_service.enrich_profile(
                org_name=request.org_name,
                ein=request.ein,
                zip_code=request.zip_code,
                state=request.state,
            )

        return self._score_program(program, request)

    def _score_program(
        self,
        program: GrantProgram,
        request: SmartMatchRequest,
    ) -> MatchResult:
        """Calculate match score for a single program."""
        reasons: List[MatchReason] = []
        missing: List[str] = []
        recommendations: List[str] = []

        eligibility_points = 0
        fit_points = 0

        # =================================================================
        # ELIGIBILITY SCORING (Hard requirements)
        # =================================================================

        # 1. Organization Type Match (30 points)
        org_type_match = self._check_org_type_eligibility(program, request)
        if org_type_match is True:
            eligibility_points += 30
            reasons.append(MatchReason(
                factor="org_type",
                points=30,
                explanation=f"Your organization type is eligible for this grant"
            ))
        elif org_type_match is False:
            reasons.append(MatchReason(
                factor="org_type",
                points=0,
                explanation="Your organization type may not be eligible",
                is_positive=False
            ))
            missing.append("Organization type may not match eligibility requirements")
        else:
            # Unknown - give partial credit
            eligibility_points += 15
            recommendations.append("Verify your organization type meets eligibility requirements")

        # 2. 501(c)(3) Status (20 points)
        if request.is_501c3 is True:
            eligibility_points += 20
            reasons.append(MatchReason(
                factor="501c3",
                points=20,
                explanation="501(c)(3) status verified"
            ))
        elif request.smart_profile and request.smart_profile.nonprofit:
            if request.smart_profile.nonprofit.is_501c3:
                eligibility_points += 20
                reasons.append(MatchReason(
                    factor="501c3",
                    points=20,
                    explanation="501(c)(3) status verified via ProPublica"
                ))
        else:
            if request.org_type in ["nonprofit", "501c3"]:
                missing.append("501(c)(3) status not verified")
                recommendations.append("Add your EIN to verify 501(c)(3) status")

        # 3. SAM.gov Registration (25 points for federal grants)
        is_federal = program.id.startswith("grants_gov_") or program.agency in ["NIH", "NSF", "CDC", "USDA", "HHS"]
        if is_federal:
            if request.sam_registered is True:
                eligibility_points += 25
                reasons.append(MatchReason(
                    factor="sam_registration",
                    points=25,
                    explanation="SAM.gov registration confirmed"
                ))
            elif request.uei_number:
                eligibility_points += 20
                reasons.append(MatchReason(
                    factor="uei",
                    points=20,
                    explanation="UEI number provided"
                ))
            else:
                missing.append("SAM.gov registration required for federal grants")
                recommendations.append("Register at SAM.gov to apply for federal grants")
        else:
            # Non-federal grants - give points for completeness
            if request.sam_registered or request.uei_number:
                eligibility_points += 10

        # =================================================================
        # FIT SCORING (Soft alignment)
        # =================================================================

        # 4. Sector/Category Match (25 points)
        sector_match = self._check_sector_match(program, request)
        if sector_match:
            fit_points += 25
            reasons.append(MatchReason(
                factor="sector",
                points=25,
                explanation=f"Grant category aligns with your sector"
            ))
        else:
            # Partial credit for related sectors
            fit_points += 10

        # 5. Funding Range Match (15 points)
        funding_match = self._check_funding_range(program, request)
        if funding_match is True:
            fit_points += 15
            reasons.append(MatchReason(
                factor="funding_range",
                points=15,
                explanation=f"Award amount fits your funding needs"
            ))
        elif funding_match is False:
            reasons.append(MatchReason(
                factor="funding_range",
                points=0,
                explanation="Award amount may not match your needs",
                is_positive=False
            ))
        else:
            fit_points += 8  # Unknown - partial credit

        # 6. Geographic/Rural Bonus (15 points)
        if request.smart_profile and request.smart_profile.rural_status:
            rural = request.smart_profile.rural_status

            # Check if grant favors rural areas
            is_rural_grant = self._is_rural_focused_grant(program)

            if rural.is_rural and is_rural_grant:
                fit_points += 15
                reasons.append(MatchReason(
                    factor="rural",
                    points=15,
                    explanation="Rural location qualifies you for rural-focused programs"
                ))
            elif rural.is_rural:
                fit_points += 5
                reasons.append(MatchReason(
                    factor="rural",
                    points=5,
                    explanation="Rural location may provide priority consideration"
                ))

        # 7. High-Need Community Bonus (10 points)
        if request.smart_profile and request.smart_profile.demographics:
            demo = request.smart_profile.demographics

            if demo.is_high_need:
                fit_points += 10
                if demo.poverty_rate and demo.poverty_rate > 20:
                    reasons.append(MatchReason(
                        factor="high_need",
                        points=10,
                        explanation=f"Serves high-poverty area ({demo.poverty_rate:.1f}% poverty rate)"
                    ))
                else:
                    reasons.append(MatchReason(
                        factor="high_need",
                        points=10,
                        explanation="Serves economically disadvantaged community"
                    ))

        # =================================================================
        # CALCULATE FINAL SCORES
        # =================================================================

        # Normalize to 0-100
        max_eligibility = 75  # org_type(30) + 501c3(20) + sam(25)
        max_fit = 65          # sector(25) + funding(15) + rural(15) + need(10)

        eligibility_score = min(100, int((eligibility_points / max_eligibility) * 100))
        fit_score = min(100, int((fit_points / max_fit) * 100))

        # Combined score (eligibility weighted more heavily)
        match_score = int(eligibility_score * 0.6 + fit_score * 0.4)

        # Determine eligibility and match level
        eligible = eligibility_score >= 50

        if match_score >= 80:
            match_level = "excellent"
        elif match_score >= 60:
            match_level = "good"
        elif match_score >= 40:
            match_level = "fair"
        else:
            match_level = "poor"

        return MatchResult(
            program_id=program.id,
            program_name=program.name,
            agency=program.agency or "Unknown",
            category=program.category.value if program.category else "other",
            eligibility_score=eligibility_score,
            fit_score=fit_score,
            match_score=match_score,
            eligible=eligible,
            match_level=match_level,
            reasons=reasons,
            missing_requirements=missing,
            recommendations=recommendations,
            min_award=program.min_award,
            max_award=program.max_award,
            deadline=program.deadline.isoformat() if program.deadline else None,
            program_url=program.program_url,
        )

    def _check_org_type_eligibility(
        self,
        program: GrantProgram,
        request: SmartMatchRequest,
    ) -> Optional[bool]:
        """Check if organization type matches grant eligibility."""
        if not request.org_type:
            return None

        # Get eligible codes for user's org type
        eligible_codes = ORG_TYPE_TO_ELIGIBLE_CODES.get(request.org_type.lower(), [])

        # For now, assume most grants allow common org types
        # In production, parse eligibility from program.eligibility_summary
        common_eligible = ["nonprofit", "501c3", "small_business", "government"]

        if request.org_type.lower() in common_eligible:
            return True

        # Check eligibility summary for clues
        eligibility_text = (program.eligibility_summary or "").lower()

        if request.org_type.lower() in eligibility_text:
            return True

        if "unrestricted" in eligibility_text or "all" in eligibility_text:
            return True

        return None  # Unknown

    def _check_sector_match(
        self,
        program: GrantProgram,
        request: SmartMatchRequest,
    ) -> bool:
        """Check if grant category matches user's sector."""
        if not request.sector:
            return True  # No preference = matches everything

        sector_lower = request.sector.lower()
        category = program.category

        # Direct match
        if category:
            category_name = category.value.lower()
            if sector_lower in category_name or category_name in sector_lower:
                return True

        # Check NTEE code from smart profile
        if request.smart_profile and request.smart_profile.nonprofit:
            ntee = request.smart_profile.nonprofit.ntee_code
            if ntee:
                mapped_category = NTEE_TO_GRANT_CATEGORY.get(ntee[0].upper())
                if mapped_category and mapped_category == category:
                    return True

        return False

    def _check_funding_range(
        self,
        program: GrantProgram,
        request: SmartMatchRequest,
    ) -> Optional[bool]:
        """Check if grant funding range matches user needs."""
        if not request.min_funding and not request.max_funding:
            return None

        prog_min = program.min_award or 0
        prog_max = program.max_award or float('inf')

        if request.min_funding:
            if prog_max < request.min_funding:
                return False  # Grant too small

        if request.max_funding:
            if prog_min > request.max_funding:
                return False  # Grant too big

        return True

    def _is_rural_focused_grant(self, program: GrantProgram) -> bool:
        """Check if grant specifically targets rural areas."""
        name_lower = (program.name or "").lower()
        desc_lower = (program.description or "").lower()
        agency_lower = (program.agency or "").lower()

        rural_keywords = ["rural", "usda", "agriculture", "farm", "community development"]

        for keyword in rural_keywords:
            if keyword in name_lower or keyword in desc_lower or keyword in agency_lower:
                return True

        return False

    def close(self):
        """Clean up resources."""
        self.profile_service.close()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_matching_engine(db: Session) -> SmartMatchingEngine:
    """Factory function to create SmartMatchingEngine."""
    return SmartMatchingEngine(db)


def quick_match(
    db: Session,
    org_type: str = None,
    zip_code: str = None,
    sector: str = None,
    is_501c3: bool = None,
    sam_registered: bool = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Quick matching function returning dict format.

    Example:
        results = quick_match(
            db,
            org_type="nonprofit",
            zip_code="40831",
            sector="healthcare",
            is_501c3=True,
            limit=3
        )
    """
    engine = create_matching_engine(db)
    try:
        request = SmartMatchRequest(
            org_type=org_type,
            zip_code=zip_code,
            sector=sector,
            is_501c3=is_501c3,
            sam_registered=sam_registered,
        )

        results = engine.match_grants(request, limit=limit)

        return [
            {
                "program_id": r.program_id,
                "program_name": r.program_name,
                "agency": r.agency,
                "category": r.category,
                "match_score": r.match_score,
                "eligibility_score": r.eligibility_score,
                "fit_score": r.fit_score,
                "match_level": r.match_level,
                "eligible": r.eligible,
                "reasons": [
                    {"factor": rr.factor, "points": rr.points, "explanation": rr.explanation}
                    for rr in r.reasons
                ],
                "missing_requirements": r.missing_requirements,
                "recommendations": r.recommendations,
                "max_award": r.max_award,
                "deadline": r.deadline,
                "program_url": r.program_url,
            }
            for r in results
        ]
    finally:
        engine.close()
