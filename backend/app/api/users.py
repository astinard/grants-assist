"""User profile API."""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, User, UserProfile
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])


# ============ Schemas ============

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    organization_name: Optional[str] = None
    organization_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    ein: Optional[str] = None
    uei_number: Optional[str] = None
    sam_registered: Optional[bool] = None
    is_veteran: Optional[bool] = None
    is_minority_owned: Optional[bool] = None
    is_woman_owned: Optional[bool] = None
    is_rural: Optional[bool] = None
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    years_in_operation: Optional[int] = None


class ProfileResponse(BaseModel):
    id: str
    full_name: Optional[str]
    organization_name: Optional[str]
    organization_type: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    congressional_district: Optional[str]
    ein: Optional[str]
    uei_number: Optional[str]
    sam_registered: bool
    is_rural: Optional[bool]
    completeness: float  # 0-100

    class Config:
        from_attributes = True


# ============ Helpers ============

def calculate_profile_completeness(profile: UserProfile) -> float:
    """Calculate how complete a profile is."""
    fields = [profile.full_name, profile.organization_name, profile.address,
              profile.city, profile.state, profile.zip_code, profile.phone,
              profile.ein, profile.uei_number]
    return round((sum(1 for f in fields if f) / len(fields)) * 100, 1)


def build_profile_response(profile: UserProfile) -> ProfileResponse:
    """Build ProfileResponse from UserProfile model."""
    return ProfileResponse(
        id=profile.id, full_name=profile.full_name,
        organization_name=profile.organization_name, organization_type=profile.organization_type,
        address=profile.address, city=profile.city, state=profile.state,
        zip_code=profile.zip_code, congressional_district=profile.congressional_district,
        ein=profile.ein, uei_number=profile.uei_number,
        sam_registered=profile.sam_registered or False, is_rural=profile.is_rural,
        completeness=calculate_profile_completeness(profile)
    )


# ============ Endpoints ============

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        # Create empty profile
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return build_profile_response(profile)


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    updates: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return build_profile_response(profile)
