"""Applications API - Create and manage grant applications."""
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
import io

from app.models.database import (
    get_db, User, Application, GrantProgram, ApplicationStatus,
    UserProfile, ApplicationSection, SectionType, BudgetLineItem, BudgetCategory
)
from app.api.auth import get_current_user
from app.services.ai_writing import ai_writing_service
from app.services.pdf_generator import generate_application_pdf, generate_grant_summary_pdf
from app.services.ai_writing_v2 import create_professional_writing_service
from app.services.quality_scorer import create_quality_scorer
from app.services.pdf_generator_v2 import create_professional_pdf_generator

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


# ============ Budget Endpoints ============

class BudgetLineItemCreate(BaseModel):
    category: str
    description: str
    unit_cost: float
    quantity: float = 1
    justification: Optional[str] = None
    is_matching: bool = False


class BudgetLineItemResponse(BaseModel):
    id: str
    category: str
    description: str
    unit_cost: float
    quantity: float
    total_cost: float
    justification: Optional[str]
    is_matching: bool

    class Config:
        from_attributes = True


@router.get("/{app_id}/budget")
async def get_application_budget(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get budget line items for an application."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    items = db.query(BudgetLineItem).filter(
        BudgetLineItem.application_id == app_id
    ).order_by(BudgetLineItem.category, BudgetLineItem.sort_order).all()

    total_request = 0
    total_match = 0

    line_items = []
    for item in items:
        total = (item.unit_cost or 0) * (item.quantity or 1)
        if item.is_matching:
            total_match += total
        else:
            total_request += total

        line_items.append({
            "id": item.id,
            "category": item.category.value if item.category else "other",
            "description": item.description,
            "unit_cost": item.unit_cost,
            "quantity": item.quantity,
            "total_cost": total,
            "justification": item.justification,
            "is_matching": item.is_matching
        })

    return {
        "application_id": app_id,
        "line_items": line_items,
        "total_request": total_request,
        "total_match": total_match,
        "grand_total": total_request + total_match
    }


@router.post("/{app_id}/budget")
async def add_budget_line_item(
    app_id: str,
    data: BudgetLineItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a budget line item."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        category = BudgetCategory(data.category)
    except ValueError:
        category = BudgetCategory.OTHER

    # Get current max sort order
    max_order = db.query(BudgetLineItem).filter(
        BudgetLineItem.application_id == app_id
    ).count()

    item = BudgetLineItem(
        application_id=app_id,
        category=category,
        description=data.description,
        unit_cost=data.unit_cost,
        quantity=data.quantity,
        total_cost=data.unit_cost * data.quantity,
        justification=data.justification,
        is_matching=data.is_matching,
        sort_order=max_order
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "category": item.category.value,
        "description": item.description,
        "unit_cost": item.unit_cost,
        "quantity": item.quantity,
        "total_cost": item.total_cost,
        "justification": item.justification,
        "is_matching": item.is_matching
    }


@router.delete("/{app_id}/budget/{item_id}")
async def delete_budget_line_item(
    app_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a budget line item."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    item = db.query(BudgetLineItem).filter(
        BudgetLineItem.id == item_id,
        BudgetLineItem.application_id == app_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")

    db.delete(item)
    db.commit()

    return {"message": "Budget item deleted"}


# ============ Professional Generation Endpoints ============

@router.post("/{app_id}/generate-professional")
async def generate_professional_application(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a complete professional grant application using AI.

    This uses multi-phase generation to create consulting-firm quality
    narratives for all 10 standard grant sections.
    """
    app = db.query(Application).options(
        joinedload(Application.program)
    ).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Create professional writing service
    writing_service = create_professional_writing_service(db)

    # Generate all sections
    result = await writing_service.generate_professional_application(
        user_id=current_user.id,
        application_id=app_id,
        program_id=app.program_id
    )

    # Update application status
    if app.status == ApplicationStatus.DRAFT:
        app.status = ApplicationStatus.IN_PROGRESS
        db.commit()

    return {
        "message": "Professional application generated",
        "application_id": app_id,
        "sections_generated": len(result.get("sections", {})),
        "sections": {
            k: {
                "title": v.get("title", k),
                "word_count": v.get("word_count", 0),
                "order": v.get("order", 99)
            }
            for k, v in result.get("sections", {}).items()
        }
    }


@router.get("/{app_id}/sections")
async def get_application_sections(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all generated sections for an application."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    sections = db.query(ApplicationSection).filter(
        ApplicationSection.application_id == app_id
    ).order_by(ApplicationSection.section_type).all()

    return {
        "application_id": app_id,
        "sections": [
            {
                "id": s.id,
                "section_type": s.section_type.value,
                "title": s.section_type.value.replace("_", " ").title(),
                "content": s.content,
                "word_count": s.word_count,
                "quality_score": s.quality_score,
                "relevance_score": s.relevance_score,
                "evidence_score": s.evidence_score,
                "ai_feedback": s.ai_feedback,
                "version": s.version,
                "is_final": s.is_final,
                "is_user_edited": s.is_user_edited,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            for s in sections
        ],
        "total_sections": len(sections),
        "total_words": sum(s.word_count or 0 for s in sections)
    }


@router.get("/{app_id}/sections/{section_type}")
async def get_section(
    app_id: str,
    section_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific section."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        st = SectionType(section_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid section type: {section_type}")

    section = db.query(ApplicationSection).filter(
        ApplicationSection.application_id == app_id,
        ApplicationSection.section_type == st
    ).first()

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    return {
        "id": section.id,
        "section_type": section.section_type.value,
        "title": section.section_type.value.replace("_", " ").title(),
        "content": section.content,
        "word_count": section.word_count,
        "quality_score": section.quality_score,
        "relevance_score": section.relevance_score,
        "evidence_score": section.evidence_score,
        "ai_feedback": section.ai_feedback,
        "version": section.version,
        "is_final": section.is_final,
        "is_user_edited": section.is_user_edited
    }


class SectionUpdateRequest(BaseModel):
    content: str


@router.put("/{app_id}/sections/{section_type}")
async def update_section(
    app_id: str,
    section_type: str,
    data: SectionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a section's content (user edit)."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        st = SectionType(section_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid section type: {section_type}")

    section = db.query(ApplicationSection).filter(
        ApplicationSection.application_id == app_id,
        ApplicationSection.section_type == st
    ).first()

    if not section:
        # Create new section
        section = ApplicationSection(
            application_id=app_id,
            section_type=st
        )
        db.add(section)

    section.content = data.content
    section.word_count = len(data.content.split())
    section.is_user_edited = True
    section.version += 1

    db.commit()
    db.refresh(section)

    return {
        "id": section.id,
        "section_type": section.section_type.value,
        "content": section.content,
        "word_count": section.word_count,
        "version": section.version,
        "is_user_edited": section.is_user_edited
    }


@router.post("/{app_id}/sections/{section_type}/regenerate")
async def regenerate_section(
    app_id: str,
    section_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate a specific section."""
    app = db.query(Application).options(
        joinedload(Application.program)
    ).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        st = SectionType(section_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid section type: {section_type}")

    writing_service = create_professional_writing_service(db)

    result = await writing_service.generate_professional_application(
        user_id=current_user.id,
        application_id=app_id,
        program_id=app.program_id,
        sections_to_generate=[st]
    )

    section_data = result.get("sections", {}).get(st.value, {})

    return {
        "message": f"Section {section_type} regenerated",
        "section_type": section_type,
        "word_count": section_data.get("word_count", 0),
        "content": section_data.get("content", "")
    }


@router.get("/{app_id}/quality-score")
async def get_quality_score(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get quality scores for the application."""
    app = db.query(Application).options(
        joinedload(Application.program)
    ).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Create quality scorer
    scorer = create_quality_scorer(db)

    # Get program context for relevance scoring
    program_context = None
    if app.program:
        program_context = {
            "name": app.program.name,
            "agency": app.program.agency,
            "category": app.program.category.value if app.program.category else None
        }

    # Score the application
    score_result = await scorer.score_application(app_id, program_context)

    # Update application completeness score
    app.completeness_score = score_result.overall_score
    db.commit()

    return {
        "application_id": app_id,
        "overall_score": score_result.overall_score,
        "ready_for_submission": score_result.ready_for_submission,
        "strengths": score_result.strengths,
        "critical_improvements": score_result.critical_improvements,
        "section_scores": {
            k: {
                "overall": v.overall_score,
                "relevance": v.relevance_score,
                "evidence": v.evidence_score,
                "writing": v.writing_score,
                "completeness": v.completeness_score,
                "feedback": v.feedback,
                "strengths": v.strengths,
                "improvements": v.improvements
            }
            for k, v in score_result.section_scores.items()
        }
    }


@router.get("/{app_id}/generation-readiness")
async def check_generation_readiness(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if sufficient data exists for quality grant generation.
    Returns warnings for missing data that would result in generic content.
    """
    from app.services.context_assembler import ContextAssembler

    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    assembler = ContextAssembler(db)
    context = assembler.assemble_full_context(
        user_id=current_user.id,
        application_id=app_id,
        program_id=app.program_id
    )

    org = context.get("organization", {})
    summary = context.get("summary", {})

    missing_critical = []
    missing_recommended = []

    # Critical fields - without these, output will be very generic
    if not summary.get("organization_name"):
        missing_critical.append("Organization name")
    if not org.get("mission_statement"):
        missing_critical.append("Mission statement")

    # Recommended fields - improve quality significantly
    if not org.get("founding_year"):
        missing_recommended.append("Founding year")
    if not org.get("staff_count"):
        missing_recommended.append("Staff count")
    if not org.get("annual_budget"):
        missing_recommended.append("Annual budget")
    if not org.get("clients_served_annually"):
        missing_recommended.append("Clients served annually")
    if not context.get("prior_grants"):
        missing_recommended.append("Prior grant history")
    if not context.get("achievements"):
        missing_recommended.append("Organizational achievements")
    if not context.get("community_data"):
        missing_recommended.append("Community statistics/data")

    # Calculate completeness score
    total_fields = 9  # 2 critical + 7 recommended
    filled = total_fields - len(missing_critical) - len(missing_recommended)
    score = int((filled / total_fields) * 100)

    return {
        "ready": len(missing_critical) == 0,
        "completeness_score": score,
        "missing_critical": missing_critical,
        "missing_recommended": missing_recommended,
        "data_summary": {
            "has_organization_name": bool(summary.get("organization_name")),
            "has_mission": bool(org.get("mission_statement")),
            "has_founding_year": bool(org.get("founding_year")),
            "has_staff_info": bool(org.get("staff_count")),
            "has_budget": bool(org.get("annual_budget")),
            "prior_grants_count": len(context.get("prior_grants", [])),
            "achievements_count": len(context.get("achievements", [])),
            "community_data_count": sum(len(v) for v in context.get("community_data", {}).values()),
        },
        "message": "Ready for high-quality generation" if not missing_critical else f"Please add: {', '.join(missing_critical)}"
    }


@router.get("/{app_id}/professional-pdf")
async def download_professional_pdf(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download the professional application PDF."""
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Create professional PDF generator
    pdf_generator = create_professional_pdf_generator(db)

    try:
        pdf_bytes = pdf_generator.generate_professional_application_pdf(app_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"application_{app_id[:8]}_professional.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ Delete Endpoint ============

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
