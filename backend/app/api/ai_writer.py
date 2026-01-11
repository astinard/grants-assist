"""AI Writer API - Mobile-optimized endpoints for grant narrative generation."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import (
    get_db, User, Application, SectionType, ApplicationSection
)
from app.api.auth import get_current_user
from app.services.narrative_generator import (
    create_narrative_generator, GenerationTone, SECTION_CONFIG
)

router = APIRouter(prefix="/api/ai-writer", tags=["AI Writer"])


# ============ Schemas ============

class SectionInfo(BaseModel):
    """Information about an available section."""
    type: str
    title: str
    description: str
    min_words: int
    max_words: int
    key_elements: List[str]


class GenerateSectionRequest(BaseModel):
    """Request to generate a section."""
    section_type: str
    additional_context: Optional[str] = None
    tone: Optional[str] = "professional"


class GenerateSectionResponse(BaseModel):
    """Response from section generation."""
    content: str
    word_count: int
    quality_score: float
    quality_feedback: str
    suggestions: List[str]
    model: str


class ImproveSectionRequest(BaseModel):
    """Request to improve an existing section."""
    section_type: str
    current_content: str
    improvement_focus: str


class SectionStatusResponse(BaseModel):
    """Status of a section."""
    section_type: str
    title: str
    has_content: bool
    word_count: int
    quality_score: Optional[float]
    version: int
    is_user_edited: bool


# ============ Endpoints ============

@router.get("/sections")
async def list_available_sections():
    """
    Get list of all available grant sections with metadata.

    Returns information about each section including:
    - title and description
    - word count requirements
    - key elements to include
    """
    sections = []
    for section_type, config in SECTION_CONFIG.items():
        sections.append({
            "type": section_type.value,
            "title": config["title"],
            "description": config["description"],
            "min_words": config["min_words"],
            "max_words": config["max_words"],
            "key_elements": config["key_elements"]
        })
    return {"sections": sections}


@router.get("/applications/{app_id}/status")
async def get_application_writing_status(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get writing status for all sections of an application.

    Returns which sections have been generated, their word counts,
    quality scores, and completion status.
    """
    # Verify application ownership
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get all sections for this application
    sections = db.query(ApplicationSection).filter(
        ApplicationSection.application_id == app_id
    ).all()

    section_map = {s.section_type: s for s in sections}

    # Build status for all possible sections
    statuses = []
    total_words = 0
    completed_count = 0

    for section_type, config in SECTION_CONFIG.items():
        existing = section_map.get(section_type)

        if existing and existing.content:
            statuses.append({
                "section_type": section_type.value,
                "title": config["title"],
                "has_content": True,
                "word_count": existing.word_count or 0,
                "quality_score": existing.quality_score,
                "version": existing.version or 1,
                "is_user_edited": existing.is_user_edited or False
            })
            total_words += existing.word_count or 0
            completed_count += 1
        else:
            statuses.append({
                "section_type": section_type.value,
                "title": config["title"],
                "has_content": False,
                "word_count": 0,
                "quality_score": None,
                "version": 0,
                "is_user_edited": False
            })

    # Calculate overall progress
    total_sections = len(SECTION_CONFIG)
    progress = int((completed_count / total_sections) * 100) if total_sections > 0 else 0

    return {
        "application_id": app_id,
        "sections": statuses,
        "progress": progress,
        "completed_sections": completed_count,
        "total_sections": total_sections,
        "total_words": total_words,
        "estimated_pages": round(total_words / 250, 1)  # ~250 words per page
    }


@router.post("/applications/{app_id}/generate")
async def generate_section(
    app_id: str,
    request: GenerateSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a single section for an application.

    Args:
        section_type: Type of section to generate (e.g., "statement_of_need")
        additional_context: Optional extra context to include
        tone: Writing tone - "professional", "compelling", or "data_driven"

    Returns:
        Generated content with quality feedback and improvement suggestions.
    """
    # Verify application ownership
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Validate section type
    try:
        section_type = SectionType(request.section_type)
    except ValueError:
        valid_types = [st.value for st in SectionType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section type. Valid types: {valid_types}"
        )

    # Validate tone
    try:
        tone = GenerationTone(request.tone) if request.tone else GenerationTone.PROFESSIONAL
    except ValueError:
        tone = GenerationTone.PROFESSIONAL

    # Create generator and generate section
    generator = create_narrative_generator(db)

    result = await generator.generate_section(
        user_id=current_user.id,
        application_id=app_id,
        section_type=section_type,
        additional_context=request.additional_context,
        tone=tone
    )

    return {
        "application_id": app_id,
        "section_type": request.section_type,
        **result
    }


@router.post("/applications/{app_id}/improve")
async def improve_section(
    app_id: str,
    request: ImproveSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Improve an existing section based on feedback.

    Args:
        section_type: Type of section to improve
        current_content: Current content of the section
        improvement_focus: What to improve (e.g., "add more statistics", "stronger opening")

    Returns:
        Improved content.
    """
    # Verify application ownership
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Validate section type
    try:
        section_type = SectionType(request.section_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section type")

    # Create generator and improve section
    generator = create_narrative_generator(db)

    result = await generator.improve_section(
        application_id=app_id,
        section_type=section_type,
        current_content=request.current_content,
        improvement_focus=request.improvement_focus
    )

    return {
        "application_id": app_id,
        "section_type": request.section_type,
        **result
    }


@router.post("/applications/{app_id}/generate-all")
async def generate_all_sections(
    app_id: str,
    tone: Optional[str] = "professional",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate all sections for an application.

    This is a longer operation that generates all 10 standard sections.
    For mobile, consider generating section-by-section instead.
    """
    # Verify application ownership
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Validate tone
    try:
        gen_tone = GenerationTone(tone) if tone else GenerationTone.PROFESSIONAL
    except ValueError:
        gen_tone = GenerationTone.PROFESSIONAL

    generator = create_narrative_generator(db)

    results = {}
    errors = []

    # Generate sections in recommended order
    section_order = [
        SectionType.EXECUTIVE_SUMMARY,
        SectionType.STATEMENT_OF_NEED,
        SectionType.ORGANIZATIONAL_BACKGROUND,
        SectionType.PROJECT_DESCRIPTION,
        SectionType.GOALS_OBJECTIVES,
        SectionType.EVALUATION_PLAN,
        SectionType.BUDGET_NARRATIVE,
        SectionType.SUSTAINABILITY_PLAN,
        SectionType.COVER_LETTER,
        SectionType.CONCLUSION
    ]

    for section_type in section_order:
        try:
            result = await generator.generate_section(
                user_id=current_user.id,
                application_id=app_id,
                section_type=section_type,
                tone=gen_tone
            )
            results[section_type.value] = {
                "word_count": result.get("word_count", 0),
                "quality_score": result.get("quality_score", 0),
                "success": True
            }
        except Exception as e:
            errors.append({
                "section": section_type.value,
                "error": str(e)
            })
            results[section_type.value] = {
                "word_count": 0,
                "quality_score": 0,
                "success": False,
                "error": str(e)
            }

    # Calculate totals
    total_words = sum(r.get("word_count", 0) for r in results.values())
    avg_quality = sum(r.get("quality_score", 0) for r in results.values()) / len(results) if results else 0
    success_count = sum(1 for r in results.values() if r.get("success"))

    return {
        "application_id": app_id,
        "sections_generated": success_count,
        "total_sections": len(section_order),
        "total_words": total_words,
        "average_quality": round(avg_quality, 1),
        "estimated_pages": round(total_words / 250, 1),
        "results": results,
        "errors": errors if errors else None
    }


@router.get("/applications/{app_id}/sections/{section_type}")
async def get_section_content(
    app_id: str,
    section_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the content of a specific section.
    """
    # Verify application ownership
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Validate section type
    try:
        st = SectionType(section_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section type")

    section = db.query(ApplicationSection).filter(
        ApplicationSection.application_id == app_id,
        ApplicationSection.section_type == st
    ).first()

    config = SECTION_CONFIG.get(st, {})

    if not section:
        return {
            "application_id": app_id,
            "section_type": section_type,
            "title": config.get("title", section_type),
            "content": None,
            "word_count": 0,
            "quality_score": None,
            "has_content": False,
            "key_elements": config.get("key_elements", [])
        }

    return {
        "application_id": app_id,
        "section_type": section_type,
        "title": config.get("title", section_type),
        "content": section.content,
        "word_count": section.word_count or 0,
        "quality_score": section.quality_score,
        "has_content": bool(section.content),
        "version": section.version or 1,
        "is_user_edited": section.is_user_edited or False,
        "key_elements": config.get("key_elements", [])
    }


class UpdateSectionRequest(BaseModel):
    """Request to update section content."""
    content: str


@router.put("/applications/{app_id}/sections/{section_type}")
async def update_section_content(
    app_id: str,
    section_type: str,
    request: UpdateSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update/save section content (user edits).
    """
    # Verify application ownership
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Validate section type
    try:
        st = SectionType(section_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section type")

    section = db.query(ApplicationSection).filter(
        ApplicationSection.application_id == app_id,
        ApplicationSection.section_type == st
    ).first()

    word_count = len(request.content.split())

    if section:
        section.content = request.content
        section.word_count = word_count
        section.is_user_edited = True
        section.version = (section.version or 0) + 1
    else:
        section = ApplicationSection(
            application_id=app_id,
            section_type=st,
            content=request.content,
            word_count=word_count,
            is_user_edited=True,
            version=1
        )
        db.add(section)

    db.commit()
    db.refresh(section)

    return {
        "application_id": app_id,
        "section_type": section_type,
        "word_count": word_count,
        "version": section.version,
        "is_user_edited": True,
        "message": "Section saved successfully"
    }


# ============ Agent-Based Full Application Generation ============

class GenerateFullApplicationRequest(BaseModel):
    """Request for full application generation via AI agent."""
    project_title: str
    project_summary: str


class FullApplicationResponse(BaseModel):
    """Response from full application generation."""
    application_id: str
    grant_id: str
    project_title: str
    generation_time_seconds: float
    word_count: int
    section_count: int
    full_application: str
    sections: dict


@router.post("/applications/{app_id}/generate-full-agent")
async def generate_full_application_with_agent(
    app_id: str,
    request: GenerateFullApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a complete grant application using the AI Agent.

    This uses an autonomous agent that:
    1. Researches grant requirements
    2. Gathers organization context
    3. Finds supporting statistics
    4. Writes all sections with real data
    5. Returns a complete, professional application

    Note: This may take 30-60 seconds to complete.
    """
    from app.services.grant_agent import generate_grant_application

    # Verify application ownership
    app = db.query(Application).filter(
        Application.id == app_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        # Generate using agent
        result = await generate_grant_application(
            grant_id=app.program_id,
            user_id=current_user.id,
            project_title=request.project_title,
            project_summary=request.project_summary,
            db_session=db
        )

        # Store the generated application
        app.generated_narrative = result["full_application"]
        db.commit()

        # Also store individual sections
        for section_key, section_content in result["sections"].items():
            try:
                st = SectionType(section_key)
                existing = db.query(ApplicationSection).filter(
                    ApplicationSection.application_id == app_id,
                    ApplicationSection.section_type == st
                ).first()

                word_count = len(section_content.split())

                if existing:
                    existing.content = section_content
                    existing.word_count = word_count
                    existing.generation_model = result["model"]
                else:
                    new_section = ApplicationSection(
                        application_id=app_id,
                        section_type=st,
                        content=section_content,
                        word_count=word_count,
                        generation_model=result["model"]
                    )
                    db.add(new_section)
            except ValueError:
                # Skip sections that don't match our SectionType enum
                pass

        db.commit()

        # Update completeness score based on sections generated
        # 7 key sections out of 10 total = 70% base, plus quality bonus
        total_sections = 10  # Total possible sections
        generated_sections = result["section_count"]
        completeness = min(100.0, (generated_sections / total_sections) * 100)

        # Add quality bonus for word count (max 30 points)
        if result["word_count"] > 5000:
            completeness = min(100.0, completeness + 30)
        elif result["word_count"] > 3000:
            completeness = min(100.0, completeness + 20)
        elif result["word_count"] > 1500:
            completeness = min(100.0, completeness + 10)

        app.completeness_score = completeness
        app.status = ApplicationStatus.IN_PROGRESS
        db.commit()

        return {
            "application_id": app_id,
            "grant_id": app.program_id,
            "project_title": result["project_title"],
            "generation_time_seconds": result["generation_time_seconds"],
            "word_count": result["word_count"],
            "section_count": result["section_count"],
            "full_application": result["full_application"],
            "sections": list(result["sections"].keys()),
            "completeness_score": completeness,
            "message": "Complete application generated successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate application: {str(e)}"
        )
