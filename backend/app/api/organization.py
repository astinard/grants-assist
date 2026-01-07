"""
Organization API - Manage organization profiles and evidence data.

Endpoints for:
- Organization profile (extended profile data)
- Prior grants history
- Achievements
- Community data
- Budget templates
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import (
    get_db, User, OrganizationProfile, PriorGrant, Achievement,
    CommunityData, PriorGrantStatus, CommunityDataType
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/organization", tags=["Organization"])


# ============ Schemas ============

# Organization Profile
class OrganizationProfileCreate(BaseModel):
    mission_statement: Optional[str] = None
    vision_statement: Optional[str] = None
    founding_year: Optional[int] = None
    service_area: Optional[str] = None
    service_area_population: Optional[int] = None
    annual_budget: Optional[float] = None
    staff_count: Optional[int] = None
    volunteer_count: Optional[int] = None
    board_size: Optional[int] = None
    certifications: Optional[List[str]] = None
    accreditations: Optional[List[str]] = None
    key_partnerships: Optional[List[str]] = None
    clients_served_annually: Optional[int] = None
    geographic_reach: Optional[str] = None
    programs_offered: Optional[List[str]] = None


class OrganizationProfileResponse(BaseModel):
    id: str
    mission_statement: Optional[str]
    vision_statement: Optional[str]
    founding_year: Optional[int]
    service_area: Optional[str]
    service_area_population: Optional[int]
    annual_budget: Optional[float]
    staff_count: Optional[int]
    volunteer_count: Optional[int]
    board_size: Optional[int]
    certifications: List[str]
    accreditations: List[str]
    key_partnerships: List[str]
    clients_served_annually: Optional[int]
    geographic_reach: Optional[str]
    programs_offered: List[str]

    class Config:
        from_attributes = True


# Prior Grants
class PriorGrantCreate(BaseModel):
    funder_name: str
    grant_title: Optional[str] = None
    amount: Optional[float] = None
    year_awarded: Optional[int] = None
    status: Optional[str] = "awarded"
    outcomes_achieved: Optional[str] = None
    metrics_achieved: Optional[dict] = None
    lessons_learned: Optional[str] = None


class PriorGrantResponse(BaseModel):
    id: str
    funder_name: str
    grant_title: Optional[str]
    amount: Optional[float]
    year_awarded: Optional[int]
    status: str
    outcomes_achieved: Optional[str]
    metrics_achieved: Optional[dict]
    lessons_learned: Optional[str]

    class Config:
        from_attributes = True


# Achievements
class AchievementCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    metric_value: Optional[float] = None
    metric_unit: Optional[str] = None
    year: Optional[int] = None
    evidence_url: Optional[str] = None
    source: Optional[str] = None


class AchievementResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    category: Optional[str]
    metric_value: Optional[float]
    metric_unit: Optional[str]
    year: Optional[int]
    evidence_url: Optional[str]
    source: Optional[str]

    class Config:
        from_attributes = True


# Community Data
class CommunityDataCreate(BaseModel):
    data_type: str  # demographic, economic, health, etc.
    indicator: str
    statistic: str
    comparison_value: Optional[str] = None
    trend: Optional[str] = None
    source: str
    source_year: Optional[int] = None
    source_url: Optional[str] = None
    geographic_area: Optional[str] = None


class CommunityDataResponse(BaseModel):
    id: str
    data_type: str
    indicator: str
    statistic: str
    comparison_value: Optional[str]
    trend: Optional[str]
    source: str
    source_year: Optional[int]
    source_url: Optional[str]
    geographic_area: Optional[str]

    class Config:
        from_attributes = True


# ============ Helper Functions ============

def parse_json_field(value: Optional[str]) -> List:
    """Parse a JSON field or return empty list."""
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        return []


def serialize_json_field(value: Optional[List]) -> Optional[str]:
    """Serialize a list to JSON string."""
    if not value:
        return None
    return json.dumps(value)


# ============ Organization Profile Endpoints ============

@router.get("/profile", response_model=OrganizationProfileResponse)
async def get_organization_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the user's organization profile."""
    profile = db.query(OrganizationProfile).filter(
        OrganizationProfile.user_id == current_user.id
    ).first()

    if not profile:
        # Return empty profile
        return OrganizationProfileResponse(
            id="",
            mission_statement=None,
            vision_statement=None,
            founding_year=None,
            service_area=None,
            service_area_population=None,
            annual_budget=None,
            staff_count=None,
            volunteer_count=None,
            board_size=None,
            certifications=[],
            accreditations=[],
            key_partnerships=[],
            clients_served_annually=None,
            geographic_reach=None,
            programs_offered=[]
        )

    return OrganizationProfileResponse(
        id=profile.id,
        mission_statement=profile.mission_statement,
        vision_statement=profile.vision_statement,
        founding_year=profile.founding_year,
        service_area=profile.service_area,
        service_area_population=profile.service_area_population,
        annual_budget=profile.annual_budget,
        staff_count=profile.staff_count,
        volunteer_count=profile.volunteer_count,
        board_size=profile.board_size,
        certifications=parse_json_field(profile.certifications),
        accreditations=parse_json_field(profile.accreditations),
        key_partnerships=parse_json_field(profile.key_partnerships),
        clients_served_annually=profile.clients_served_annually,
        geographic_reach=profile.geographic_reach,
        programs_offered=parse_json_field(profile.programs_offered)
    )


@router.post("/profile", response_model=OrganizationProfileResponse)
async def create_or_update_profile(
    data: OrganizationProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update organization profile."""
    profile = db.query(OrganizationProfile).filter(
        OrganizationProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = OrganizationProfile(user_id=current_user.id)
        db.add(profile)

    # Update fields
    if data.mission_statement is not None:
        profile.mission_statement = data.mission_statement
    if data.vision_statement is not None:
        profile.vision_statement = data.vision_statement
    if data.founding_year is not None:
        profile.founding_year = data.founding_year
    if data.service_area is not None:
        profile.service_area = data.service_area
    if data.service_area_population is not None:
        profile.service_area_population = data.service_area_population
    if data.annual_budget is not None:
        profile.annual_budget = data.annual_budget
    if data.staff_count is not None:
        profile.staff_count = data.staff_count
    if data.volunteer_count is not None:
        profile.volunteer_count = data.volunteer_count
    if data.board_size is not None:
        profile.board_size = data.board_size
    if data.certifications is not None:
        profile.certifications = serialize_json_field(data.certifications)
    if data.accreditations is not None:
        profile.accreditations = serialize_json_field(data.accreditations)
    if data.key_partnerships is not None:
        profile.key_partnerships = serialize_json_field(data.key_partnerships)
    if data.clients_served_annually is not None:
        profile.clients_served_annually = data.clients_served_annually
    if data.geographic_reach is not None:
        profile.geographic_reach = data.geographic_reach
    if data.programs_offered is not None:
        profile.programs_offered = serialize_json_field(data.programs_offered)

    db.commit()
    db.refresh(profile)

    return OrganizationProfileResponse(
        id=profile.id,
        mission_statement=profile.mission_statement,
        vision_statement=profile.vision_statement,
        founding_year=profile.founding_year,
        service_area=profile.service_area,
        service_area_population=profile.service_area_population,
        annual_budget=profile.annual_budget,
        staff_count=profile.staff_count,
        volunteer_count=profile.volunteer_count,
        board_size=profile.board_size,
        certifications=parse_json_field(profile.certifications),
        accreditations=parse_json_field(profile.accreditations),
        key_partnerships=parse_json_field(profile.key_partnerships),
        clients_served_annually=profile.clients_served_annually,
        geographic_reach=profile.geographic_reach,
        programs_offered=parse_json_field(profile.programs_offered)
    )


# ============ Prior Grants Endpoints ============

@router.get("/prior-grants", response_model=List[PriorGrantResponse])
async def list_prior_grants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all prior grants."""
    grants = db.query(PriorGrant).filter(
        PriorGrant.user_id == current_user.id
    ).order_by(PriorGrant.year_awarded.desc()).all()

    return [
        PriorGrantResponse(
            id=g.id,
            funder_name=g.funder_name,
            grant_title=g.grant_title,
            amount=g.amount,
            year_awarded=g.year_awarded,
            status=g.status.value if g.status else "awarded",
            outcomes_achieved=g.outcomes_achieved,
            metrics_achieved=parse_json_field(g.metrics_achieved) if isinstance(g.metrics_achieved, str) else g.metrics_achieved,
            lessons_learned=g.lessons_learned
        )
        for g in grants
    ]


@router.post("/prior-grants", response_model=PriorGrantResponse)
async def create_prior_grant(
    data: PriorGrantCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a prior grant."""
    status = PriorGrantStatus(data.status) if data.status else PriorGrantStatus.AWARDED

    grant = PriorGrant(
        user_id=current_user.id,
        funder_name=data.funder_name,
        grant_title=data.grant_title,
        amount=data.amount,
        year_awarded=data.year_awarded,
        status=status,
        outcomes_achieved=data.outcomes_achieved,
        metrics_achieved=json.dumps(data.metrics_achieved) if data.metrics_achieved else None,
        lessons_learned=data.lessons_learned
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)

    return PriorGrantResponse(
        id=grant.id,
        funder_name=grant.funder_name,
        grant_title=grant.grant_title,
        amount=grant.amount,
        year_awarded=grant.year_awarded,
        status=grant.status.value,
        outcomes_achieved=grant.outcomes_achieved,
        metrics_achieved=data.metrics_achieved,
        lessons_learned=grant.lessons_learned
    )


@router.delete("/prior-grants/{grant_id}")
async def delete_prior_grant(
    grant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a prior grant."""
    grant = db.query(PriorGrant).filter(
        PriorGrant.id == grant_id,
        PriorGrant.user_id == current_user.id
    ).first()

    if not grant:
        raise HTTPException(status_code=404, detail="Prior grant not found")

    db.delete(grant)
    db.commit()

    return {"message": "Prior grant deleted"}


# ============ Achievements Endpoints ============

@router.get("/achievements", response_model=List[AchievementResponse])
async def list_achievements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all achievements."""
    achievements = db.query(Achievement).filter(
        Achievement.user_id == current_user.id
    ).order_by(Achievement.year.desc()).all()

    return [
        AchievementResponse(
            id=a.id,
            title=a.title,
            description=a.description,
            category=a.category,
            metric_value=a.metric_value,
            metric_unit=a.metric_unit,
            year=a.year,
            evidence_url=a.evidence_url,
            source=a.source
        )
        for a in achievements
    ]


@router.post("/achievements", response_model=AchievementResponse)
async def create_achievement(
    data: AchievementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an achievement."""
    achievement = Achievement(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        metric_value=data.metric_value,
        metric_unit=data.metric_unit,
        year=data.year,
        evidence_url=data.evidence_url,
        source=data.source
    )
    db.add(achievement)
    db.commit()
    db.refresh(achievement)

    return AchievementResponse(
        id=achievement.id,
        title=achievement.title,
        description=achievement.description,
        category=achievement.category,
        metric_value=achievement.metric_value,
        metric_unit=achievement.metric_unit,
        year=achievement.year,
        evidence_url=achievement.evidence_url,
        source=achievement.source
    )


@router.delete("/achievements/{achievement_id}")
async def delete_achievement(
    achievement_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an achievement."""
    achievement = db.query(Achievement).filter(
        Achievement.id == achievement_id,
        Achievement.user_id == current_user.id
    ).first()

    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")

    db.delete(achievement)
    db.commit()

    return {"message": "Achievement deleted"}


# ============ Community Data Endpoints ============

@router.get("/community-data", response_model=List[CommunityDataResponse])
async def list_community_data(
    data_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all community data, optionally filtered by type."""
    query = db.query(CommunityData).filter(
        CommunityData.user_id == current_user.id
    )

    if data_type:
        try:
            dt = CommunityDataType(data_type)
            query = query.filter(CommunityData.data_type == dt)
        except ValueError:
            pass

    data = query.all()

    return [
        CommunityDataResponse(
            id=d.id,
            data_type=d.data_type.value if d.data_type else "other",
            indicator=d.indicator,
            statistic=d.statistic,
            comparison_value=d.comparison_value,
            trend=d.trend,
            source=d.source,
            source_year=d.source_year,
            source_url=d.source_url,
            geographic_area=d.geographic_area
        )
        for d in data
    ]


@router.post("/community-data", response_model=CommunityDataResponse)
async def create_community_data(
    data: CommunityDataCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add community data."""
    try:
        data_type = CommunityDataType(data.data_type)
    except ValueError:
        data_type = CommunityDataType.OTHER

    community_data = CommunityData(
        user_id=current_user.id,
        data_type=data_type,
        indicator=data.indicator,
        statistic=data.statistic,
        comparison_value=data.comparison_value,
        trend=data.trend,
        source=data.source,
        source_year=data.source_year,
        source_url=data.source_url,
        geographic_area=data.geographic_area
    )
    db.add(community_data)
    db.commit()
    db.refresh(community_data)

    return CommunityDataResponse(
        id=community_data.id,
        data_type=community_data.data_type.value,
        indicator=community_data.indicator,
        statistic=community_data.statistic,
        comparison_value=community_data.comparison_value,
        trend=community_data.trend,
        source=community_data.source,
        source_year=community_data.source_year,
        source_url=community_data.source_url,
        geographic_area=community_data.geographic_area
    )


@router.delete("/community-data/{data_id}")
async def delete_community_data(
    data_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete community data."""
    data = db.query(CommunityData).filter(
        CommunityData.id == data_id,
        CommunityData.user_id == current_user.id
    ).first()

    if not data:
        raise HTTPException(status_code=404, detail="Community data not found")

    db.delete(data)
    db.commit()

    return {"message": "Community data deleted"}
