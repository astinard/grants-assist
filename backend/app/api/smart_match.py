"""
Smart Match API Endpoints

Provides intelligent grant matching with:
- Auto-profile enrichment from org name/EIN/ZIP
- Probabilistic matching with explanations
- Top recommendations with actionable insights
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.smart_profile import (
    SmartProfileService,
    quick_nonprofit_lookup,
    quick_zip_lookup,
)
from app.services.smart_matching import (
    SmartMatchingEngine,
    SmartMatchRequest,
    quick_match,
)

router = APIRouter(prefix="/api/smart-match", tags=["Smart Matching"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class NonprofitSearchResult(BaseModel):
    """Nonprofit search result from ProPublica."""
    ein: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    is_501c3: bool = False
    ntee_code: Optional[str] = None
    total_revenue: Optional[float] = None
    total_assets: Optional[float] = None


class DemographicsResult(BaseModel):
    """Demographics for a ZIP code."""
    location_name: Optional[str] = None
    population: Optional[int] = None
    median_income: Optional[float] = None
    poverty_rate: Optional[float] = None
    is_high_need: bool = False
    income_vs_national: Optional[float] = None


class RuralStatusResult(BaseModel):
    """Rural status for a ZIP code."""
    is_rural: bool = False
    rucc_code: Optional[int] = None
    description: Optional[str] = None
    qualifies_usda: bool = False
    qualifies_hrsa: bool = False


class ZipLookupResponse(BaseModel):
    """Response for ZIP code lookup."""
    zip_code: str
    confidence_score: float
    data_sources: List[str]
    demographics: Optional[DemographicsResult] = None
    rural_status: Optional[RuralStatusResult] = None


class MatchReasonResponse(BaseModel):
    """A reason explaining part of a match score."""
    factor: str
    points: int
    explanation: str


class GrantMatchResponse(BaseModel):
    """A single grant match result."""
    program_id: str
    program_name: str
    agency: str
    category: str

    match_score: int = Field(..., ge=0, le=100)
    eligibility_score: int = Field(..., ge=0, le=100)
    fit_score: int = Field(..., ge=0, le=100)
    match_level: str  # excellent, good, fair, poor

    eligible: bool
    reasons: List[MatchReasonResponse]
    missing_requirements: List[str]
    recommendations: List[str]

    max_award: Optional[float] = None
    deadline: Optional[str] = None
    program_url: Optional[str] = None


class SmartMatchRequestBody(BaseModel):
    """Request body for smart matching."""
    # Organization info
    org_name: Optional[str] = Field(None, description="Organization name for lookup")
    org_type: Optional[str] = Field(None, description="Type: nonprofit, small_business, individual, government")
    ein: Optional[str] = Field(None, description="EIN for nonprofit verification")
    is_501c3: Optional[bool] = Field(None, description="501(c)(3) status")

    # Location
    zip_code: Optional[str] = Field(None, description="ZIP code for demographics lookup")
    state: Optional[str] = Field(None, description="State code (e.g., CA, TX)")

    # Federal registration
    sam_registered: Optional[bool] = Field(None, description="SAM.gov registration status")
    uei_number: Optional[str] = Field(None, description="Unique Entity ID")

    # Preferences
    sector: Optional[str] = Field(None, description="Sector: healthcare, education, agriculture, etc.")
    min_funding: Optional[float] = Field(None, description="Minimum funding needed")
    max_funding: Optional[float] = Field(None, description="Maximum funding needed")


class SmartMatchResponse(BaseModel):
    """Response for smart matching."""
    profile_confidence: float = Field(..., description="How complete/confident the profile data is (0-100)")
    total_matches: int
    matches: List[GrantMatchResponse]

    # Auto-enriched data
    auto_detected: Optional[dict] = Field(None, description="Data auto-detected from lookups")


class OnboardingQuestion(BaseModel):
    """A question for smart onboarding."""
    id: str
    question: str
    type: str  # text, select, boolean
    options: Optional[List[str]] = None
    required: bool = True
    help_text: Optional[str] = None


class OnboardingResponse(BaseModel):
    """Response with onboarding questions."""
    questions: List[OnboardingQuestion]
    estimated_matches: int = Field(..., description="Estimated grants after answering")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/lookup/nonprofit", response_model=List[NonprofitSearchResult])
async def lookup_nonprofit(
    name: str = Query(..., description="Organization name to search"),
    state: Optional[str] = Query(None, description="State to filter results"),
):
    """
    Search for nonprofits by name using ProPublica.

    Returns matching organizations with EIN, 501(c)(3) status, and financials.
    Use this for auto-completing organization profiles.
    """
    results = quick_nonprofit_lookup(name, state)
    return [NonprofitSearchResult(**r) for r in results]


@router.get("/lookup/zip", response_model=ZipLookupResponse)
async def lookup_zip(
    zip_code: str = Query(..., description="5-digit ZIP code"),
):
    """
    Get demographics and rural status for a ZIP code.

    Returns population, poverty rate, median income, and rural eligibility.
    Use this to auto-populate community need data.
    """
    result = quick_zip_lookup(zip_code)

    return ZipLookupResponse(
        zip_code=result["zip_code"],
        confidence_score=result["confidence_score"],
        data_sources=result["data_sources"],
        demographics=DemographicsResult(**result["demographics"]) if result.get("demographics") else None,
        rural_status=RuralStatusResult(**result["rural_status"]) if result.get("rural_status") else None,
    )


@router.post("/find", response_model=SmartMatchResponse)
async def find_matching_grants(
    request: SmartMatchRequestBody,
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    min_score: int = Query(30, ge=0, le=100, description="Minimum match score"),
    db: Session = Depends(get_db),
):
    """
    Find best matching grants based on profile.

    This endpoint:
    1. Auto-enriches profile using ProPublica (if org_name/EIN provided)
    2. Auto-enriches with Census data (if ZIP provided)
    3. Calculates probabilistic match scores
    4. Returns top matches with explanations

    Scores:
    - eligibility_score: Does the org meet hard requirements?
    - fit_score: How well does the org align with grant goals?
    - match_score: Combined score (eligibility weighted 60%, fit 40%)
    """
    engine = SmartMatchingEngine(db)
    try:
        match_request = SmartMatchRequest(
            org_name=request.org_name,
            org_type=request.org_type,
            ein=request.ein,
            is_501c3=request.is_501c3,
            zip_code=request.zip_code,
            state=request.state,
            sam_registered=request.sam_registered,
            uei_number=request.uei_number,
            sector=request.sector,
            min_funding=request.min_funding,
            max_funding=request.max_funding,
        )

        results = engine.match_grants(match_request, limit=limit, min_score=min_score)

        # Build auto-detected data summary
        auto_detected = {}
        if match_request.smart_profile:
            sp = match_request.smart_profile

            if sp.nonprofit:
                auto_detected["nonprofit"] = {
                    "ein": sp.nonprofit.ein,
                    "name": sp.nonprofit.name,
                    "is_501c3": sp.nonprofit.is_501c3,
                    "total_revenue": sp.nonprofit.total_revenue,
                }

            if sp.demographics:
                auto_detected["demographics"] = {
                    "poverty_rate": round(sp.demographics.poverty_rate, 1) if sp.demographics.poverty_rate else None,
                    "median_income": sp.demographics.median_household_income,
                    "is_high_need": sp.demographics.is_high_need,
                }

            if sp.rural_status:
                auto_detected["rural"] = {
                    "is_rural": sp.rural_status.is_rural,
                    "qualifies_usda": sp.rural_status.qualifies_usda,
                }

        # Calculate profile confidence
        profile_confidence = 0.0
        if match_request.smart_profile:
            profile_confidence = match_request.smart_profile.confidence_score
        else:
            # Estimate based on fields provided
            if request.org_type:
                profile_confidence += 20
            if request.is_501c3 is not None:
                profile_confidence += 15
            if request.zip_code:
                profile_confidence += 20
            if request.sam_registered is not None:
                profile_confidence += 25
            if request.sector:
                profile_confidence += 10

        # Convert results to response format
        match_responses = [
            GrantMatchResponse(
                program_id=r.program_id,
                program_name=r.program_name,
                agency=r.agency,
                category=r.category,
                match_score=r.match_score,
                eligibility_score=r.eligibility_score,
                fit_score=r.fit_score,
                match_level=r.match_level,
                eligible=r.eligible,
                reasons=[
                    MatchReasonResponse(
                        factor=rr.factor,
                        points=rr.points,
                        explanation=rr.explanation
                    )
                    for rr in r.reasons
                ],
                missing_requirements=r.missing_requirements,
                recommendations=r.recommendations,
                max_award=r.max_award,
                deadline=r.deadline,
                program_url=r.program_url,
            )
            for r in results
        ]

        return SmartMatchResponse(
            profile_confidence=profile_confidence,
            total_matches=len(match_responses),
            matches=match_responses,
            auto_detected=auto_detected if auto_detected else None,
        )

    finally:
        engine.close()


@router.get("/onboarding", response_model=OnboardingResponse)
async def get_onboarding_questions(
    db: Session = Depends(get_db),
):
    """
    Get smart onboarding questions.

    Returns 5 key questions that can populate 80% of a profile
    through API lookups and inference.
    """
    from app.models.database import GrantProgram

    # Count active grants for estimate
    total_grants = db.query(GrantProgram).filter(GrantProgram.is_active == True).count()

    questions = [
        OnboardingQuestion(
            id="org_name",
            question="What's your organization name?",
            type="text",
            required=True,
            help_text="We'll look up your EIN and verify 501(c)(3) status automatically"
        ),
        OnboardingQuestion(
            id="zip_code",
            question="What's your ZIP code?",
            type="text",
            required=True,
            help_text="We'll determine rural eligibility and community need automatically"
        ),
        OnboardingQuestion(
            id="sector",
            question="What sector do you work in?",
            type="select",
            options=["Healthcare", "Education", "Agriculture", "Small Business", "Housing", "Technology", "Other"],
            required=True,
            help_text="This helps us find grants in your field"
        ),
        OnboardingQuestion(
            id="funding_range",
            question="How much funding are you seeking?",
            type="select",
            options=["Under $50,000", "$50,000 - $250,000", "$250,000 - $1 million", "Over $1 million"],
            required=True,
            help_text="We'll match grants in your target range"
        ),
        OnboardingQuestion(
            id="sam_registered",
            question="Are you registered on SAM.gov?",
            type="select",
            options=["Yes", "No", "Don't know"],
            required=True,
            help_text="Required for most federal grants"
        ),
    ]

    return OnboardingResponse(
        questions=questions,
        estimated_matches=total_grants,
    )


@router.post("/quick", response_model=SmartMatchResponse)
async def quick_smart_match(
    org_name: str = Query(None, description="Organization name"),
    zip_code: str = Query(None, description="ZIP code"),
    sector: str = Query(None, description="Sector (healthcare, education, etc.)"),
    org_type: str = Query("nonprofit", description="Organization type"),
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """
    Quick match endpoint with GET parameters.

    Simplified version for quick lookups - just provide org name,
    ZIP code, and sector to get top 3 matches.
    """
    request = SmartMatchRequestBody(
        org_name=org_name,
        zip_code=zip_code,
        sector=sector,
        org_type=org_type,
    )

    return await find_matching_grants(request, limit=limit, min_score=20, db=db)


@router.get("/top3")
async def get_top_3_matches(
    org_name: str = Query(..., description="Organization name"),
    zip_code: str = Query(..., description="ZIP code"),
    sector: str = Query(..., description="Sector"),
    db: Session = Depends(get_db),
):
    """
    Get top 3 grant matches with full explanations.

    This is the primary endpoint for the iOS app's smart matching feature.
    Returns the 3 best matches with:
    - Match scores and explanations
    - Missing requirements
    - Actionable recommendations
    """
    engine = SmartMatchingEngine(db)
    try:
        request = SmartMatchRequest(
            org_name=org_name,
            zip_code=zip_code,
            sector=sector.lower(),
            org_type="nonprofit",  # Default assumption
        )

        results = engine.match_grants(request, limit=3, min_score=20)

        # Format for simple consumption
        top_3 = []
        for i, r in enumerate(results):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""

            # Build explanation string
            positive_reasons = [rr for rr in r.reasons if rr.is_positive]
            explanation = "; ".join([rr.explanation for rr in positive_reasons[:3]])

            top_3.append({
                "rank": i + 1,
                "medal": medal,
                "program_id": r.program_id,
                "program_name": r.program_name,
                "agency": r.agency,
                "match_score": r.match_score,
                "match_level": r.match_level,
                "explanation": explanation,
                "award_range": f"${r.max_award:,.0f}" if r.max_award else "Varies",
                "deadline": r.deadline or "Rolling",
                "missing": r.missing_requirements[:2] if r.missing_requirements else [],
                "next_steps": r.recommendations[:2] if r.recommendations else [],
            })

        # Auto-detected summary
        auto_summary = {}
        if request.smart_profile:
            sp = request.smart_profile
            if sp.nonprofit and sp.nonprofit.is_501c3:
                auto_summary["501c3_verified"] = True
            if sp.rural_status and sp.rural_status.is_rural:
                auto_summary["rural_eligible"] = True
            if sp.demographics and sp.demographics.is_high_need:
                auto_summary["high_need_community"] = True

        return {
            "org_name": org_name,
            "zip_code": zip_code,
            "sector": sector,
            "auto_detected": auto_summary,
            "top_matches": top_3,
            "total_potential_matches": len(results),
        }

    finally:
        engine.close()
