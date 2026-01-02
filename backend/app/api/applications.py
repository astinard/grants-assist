"""Applications API - Create and manage grant applications."""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
import io

from app.models.database import get_db, User, Application, GrantProgram, ApplicationStatus, UserProfile
from app.api.auth import get_current_user
from app.services.ai_writing import ai_writing_service
from app.services.pdf_generator import generate_application_pdf, generate_grant_summary_pdf

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


# ============ Helpers ============

def build_app_response(app: Application) -> ApplicationResponse:
    """Build ApplicationResponse from Application model."""
    return ApplicationResponse(
        id=app.id, program_id=app.program_id,
        program_name=app.program.name if app.program else "Unknown",
        status=app.status.value, completeness_score=app.completeness_score or 0,
        created_at=app.created_at.isoformat(), updated_at=app.updated_at.isoformat(),
        submitted_at=app.submitted_at.isoformat() if app.submitted_at else None
    )


# ============ Endpoints ============

@router.get("/", response_model=ApplicationListResponse)
async def list_applications(
    status: Optional[ApplicationStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's applications."""
    query = db.query(Application).options(joinedload(Application.program)).filter(
        Application.user_id == current_user.id
    )
    if status:
        query = query.filter(Application.status == status)
    apps = query.order_by(Application.updated_at.desc()).all()
    return ApplicationListResponse(
        total=len(apps), applications=[build_app_response(a) for a in apps]
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

    app = Application(user_id=current_user.id, program_id=data.program_id)
    db.add(app)
    db.commit()
    db.refresh(app)
    app.program = program  # Set program for build_app_response
    return build_app_response(app)


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific application."""
    app = db.query(Application).options(joinedload(Application.program)).filter(
        Application.id == app_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return build_app_response(app)


@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: str,
    updates: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an application."""
    app = db.query(Application).options(joinedload(Application.program)).filter(
        Application.id == app_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if updates.form_data:
        app.form_data = json.dumps(updates.form_data)
    if updates.status:
        app.status = updates.status
        if updates.status == ApplicationStatus.SUBMITTED:
            app.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(app)
    return build_app_response(app)


@router.get("/{app_id}/form-data")
async def get_application_form_data(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get application form data."""
    app = db.query(Application).options(joinedload(Application.program)).filter(
        Application.id == app_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    form_data = json.loads(app.form_data) if app.form_data else {}
    return {
        "application_id": app.id,
        "program_id": app.program_id,
        "program_name": app.program.name if app.program else "Unknown",
        "form_data": form_data,
        "status": app.status.value
    }


@router.post("/{app_id}/generate-narratives")
async def generate_narratives(
    app_id: str,
    project_summary: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI narratives for application sections."""
    app = db.query(Application).options(
        joinedload(Application.program)
    ).filter(
        Application.id == app_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get user profile for context
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    profile_data = {}
    if profile:
        profile_data = {
            "full_name": profile.full_name,
            "organization_name": profile.organization_name,
            "organization_type": profile.organization_type,
            "ein": profile.ein,
            "city": profile.city,
            "state": profile.state,
        }

    program_data = {}
    if app.program:
        program_data = {
            "name": app.program.name,
            "agency": app.program.agency,
            "min_award": app.program.min_award,
            "max_award": app.program.max_award,
        }

    # Generate narratives
    sections = await ai_writing_service.generate_application_sections(
        profile_data=profile_data,
        program_data=program_data,
        project_summary=project_summary
    )

    # Save to form_data
    existing_data = json.loads(app.form_data) if app.form_data else {}
    existing_data["narratives"] = sections
    app.form_data = json.dumps(existing_data)
    db.commit()

    return {"sections": sections, "message": "Narratives generated successfully"}


@router.get("/{app_id}/pdf")
async def download_application_pdf(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download application as PDF."""
    app = db.query(Application).options(
        joinedload(Application.program)
    ).filter(
        Application.id == app_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get user profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    # Build data for PDF
    form_data = json.loads(app.form_data) if app.form_data else {}

    application_data = {
        "id": app.id,
        "status": app.status.value,
        "created_at": app.created_at.isoformat(),
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "form_data": form_data,
    }

    program_data = None
    if app.program:
        program_data = {
            "name": app.program.name,
            "agency": app.program.agency,
            "description": app.program.description,
            "deadline": app.program.deadline.isoformat() if app.program.deadline else None,
            "min_award": app.program.min_award,
            "max_award": app.program.max_award,
        }

    profile_data = None
    if profile:
        profile_data = {
            "full_name": profile.full_name,
            "organization_name": profile.organization_name,
            "organization_type": profile.organization_type,
            "city": profile.city,
            "state": profile.state,
        }

    # Generate PDF
    pdf_buffer = generate_application_pdf(application_data, program_data, profile_data)

    filename = f"application_{app.id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_buffer),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
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
