"""Applications API - Create and manage grant applications."""
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, User, Application, GrantProgram, ApplicationStatus
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/applications", tags=["Applications"])


# ============ Schemas ============

class ApplicationCreate(BaseModel):
    program_id: str


class ApplicationUpdate(BaseModel):
    form_data: Optional[dict] = None
    status: Optional[ApplicationStatus] = None


class ApplicationResponse(BaseModel):
    id: str
    program_id: str
    program_name: str
    status: str
    completeness_score: float
    created_at: str
    updated_at: str
    submitted_at: Optional[str]

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    total: int
    applications: List[ApplicationResponse]


# ============ Endpoints ============

@router.get("/", response_model=ApplicationListResponse)
async def list_applications(
    status: Optional[ApplicationStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's applications."""
    query = db.query(Application).filter(Application.user_id == current_user.id)

    if status:
        query = query.filter(Application.status == status)

    apps = query.order_by(Application.updated_at.desc()).all()

    return ApplicationListResponse(
        total=len(apps),
        applications=[
            ApplicationResponse(
                id=a.id,
                program_id=a.program_id,
                program_name=a.program.name if a.program else "Unknown",
                status=a.status.value,
                completeness_score=a.completeness_score or 0,
                created_at=a.created_at.isoformat(),
                updated_at=a.updated_at.isoformat(),
                submitted_at=a.submitted_at.isoformat() if a.submitted_at else None
            )
            for a in apps
        ]
    )


@router.post("/", response_model=ApplicationResponse)
async def create_application(
    data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new application for a grant program."""
    # Verify program exists
    program = db.query(GrantProgram).filter(GrantProgram.id == data.program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Check for existing draft
    existing = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.program_id == data.program_id,
        Application.status == ApplicationStatus.DRAFT
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="You already have a draft application for this program")

    app = Application(
        user_id=current_user.id,
        program_id=data.program_id
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    return ApplicationResponse(
        id=app.id,
        program_id=app.program_id,
        program_name=program.name,
        status=app.status.value,
        completeness_score=0,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
        submitted_at=None
    )


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific application."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return ApplicationResponse(
        id=app.id,
        program_id=app.program_id,
        program_name=app.program.name if app.program else "Unknown",
        status=app.status.value,
        completeness_score=app.completeness_score or 0,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
        submitted_at=app.submitted_at.isoformat() if app.submitted_at else None
    )


@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: str,
    updates: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an application."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if updates.form_data:
        app.form_data = json.dumps(updates.form_data)
        # TODO: Recalculate completeness score

    if updates.status:
        app.status = updates.status
        if updates.status == ApplicationStatus.SUBMITTED:
            app.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(app)

    return ApplicationResponse(
        id=app.id,
        program_id=app.program_id,
        program_name=app.program.name if app.program else "Unknown",
        status=app.status.value,
        completeness_score=app.completeness_score or 0,
        created_at=app.created_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
        submitted_at=app.submitted_at.isoformat() if app.submitted_at else None
    )


@router.delete("/{app_id}")
async def delete_application(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a draft application."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != ApplicationStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only delete draft applications")

    db.delete(app)
    db.commit()

    return {"message": "Application deleted"}
