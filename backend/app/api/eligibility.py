"""Eligibility API - Check user eligibility for programs."""
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, User, UserProfile, GrantProgram
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/eligibility", tags=["Eligibility"])


# ============ Schemas ============

class EligibilityCheck(BaseModel):
    program_id: str
    eligible: bool
    match_score: float  # 0-100
    missing_requirements: List[str]
    notes: Optional[str] = None


class EligibilityResponse(BaseModel):
    total_programs: int
    eligible_count: int
    programs: List[EligibilityCheck]


# ============ Helpers ============

def check_program_eligibility(profile: UserProfile, program: GrantProgram) -> EligibilityCheck:
    """Check if a user profile is eligible for a program."""
    missing = []
    score = 100.0

    # Basic requirements for most grants
    if not profile.organization_name and program.category.value != "education":
        missing.append("Organization name required")
        score -= 20

    if not profile.ein and program.category.value not in ["education", "individual"]:
        missing.append("EIN (Tax ID) required for federal grants")
        score -= 15

    if not profile.address or not profile.city or not profile.state:
        missing.append("Complete address required")
        score -= 10

    # SAM.gov registration for federal grants
    if program.agency in ["USDA", "SBA", "HHS", "DOC"] and not profile.sam_registered:
        missing.append("SAM.gov registration required")
        score -= 15

    if not profile.uei_number and program.agency in ["USDA", "SBA", "HHS", "DOC"]:
        missing.append("UEI number required for federal grants")
        score -= 15

    # Category-specific checks
    if program.category.value == "small_business":
        if not profile.annual_revenue:
            missing.append("Annual revenue information needed")
            score -= 10
        if not profile.employee_count:
            missing.append("Employee count needed")
            score -= 10

    if program.category.value == "healthcare":
        if profile.organization_type not in ["healthcare", "nonprofit", "hospital", "clinic"]:
            missing.append("Must be healthcare organization")
            score -= 30

    score = max(0, score)
    eligible = len(missing) == 0 or score >= 70

    return EligibilityCheck(
        program_id=program.id,
        eligible=eligible,
        match_score=score,
        missing_requirements=missing,
        notes=f"Match score: {score}%" if missing else "You appear to meet all requirements"
    )


# ============ Endpoints ============

@router.get("/check", response_model=EligibilityResponse)
async def check_eligibility(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check eligibility for all active programs."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        return EligibilityResponse(
            total_programs=0,
            eligible_count=0,
            programs=[]
        )

    programs = db.query(GrantProgram).filter(GrantProgram.is_active == True).all()

    results = [check_program_eligibility(profile, p) for p in programs]
    eligible_count = sum(1 for r in results if r.eligible)

    # Sort by match score descending
    results.sort(key=lambda x: x.match_score, reverse=True)

    return EligibilityResponse(
        total_programs=len(programs),
        eligible_count=eligible_count,
        programs=results
    )


@router.get("/check/{program_id}", response_model=EligibilityCheck)
async def check_program_eligibility_endpoint(
    program_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check eligibility for a specific program."""
    from fastapi import HTTPException

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    program = db.query(GrantProgram).filter(GrantProgram.id == program_id).first()

    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    if not profile:
        return EligibilityCheck(
            program_id=program_id,
            eligible=False,
            match_score=0,
            missing_requirements=["Please complete your profile first"],
            notes="Complete your profile to check eligibility"
        )

    return check_program_eligibility(profile, program)
