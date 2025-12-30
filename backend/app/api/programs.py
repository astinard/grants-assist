"""Grant programs API."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, GrantProgram, GrantCategory

router = APIRouter(prefix="/api/programs", tags=["Grant Programs"])


# ============ Schemas ============

class ProgramResponse(BaseModel):
    id: str
    name: str
    agency: Optional[str]
    category: str
    min_award: Optional[float]
    max_award: Optional[float]
    match_required: Optional[float]
    description: Optional[str]
    eligibility_summary: Optional[str]
    deadline: Optional[str]
    rolling_deadline: bool
    program_url: Optional[str]

    class Config:
        from_attributes = True


class ProgramListResponse(BaseModel):
    total: int
    programs: List[ProgramResponse]


# ============ Endpoints ============

@router.get("/", response_model=ProgramListResponse)
async def list_programs(
    category: Optional[GrantCategory] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List available grant programs."""
    query = db.query(GrantProgram)

    if active_only:
        query = query.filter(GrantProgram.is_active == True)

    if category:
        query = query.filter(GrantProgram.category == category)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            GrantProgram.name.ilike(search_term) |
            GrantProgram.description.ilike(search_term)
        )

    programs = query.order_by(GrantProgram.name).all()

    return ProgramListResponse(
        total=len(programs),
        programs=[
            ProgramResponse(
                id=p.id,
                name=p.name,
                agency=p.agency,
                category=p.category.value if p.category else None,
                min_award=p.min_award,
                max_award=p.max_award,
                match_required=p.match_required,
                description=p.description,
                eligibility_summary=p.eligibility_summary,
                deadline=p.deadline.isoformat() if p.deadline else None,
                rolling_deadline=p.rolling_deadline,
                program_url=p.program_url
            )
            for p in programs
        ]
    )


@router.get("/categories")
async def list_categories():
    """List all grant categories."""
    return {
        "categories": [
            {"id": c.value, "name": c.value.replace("_", " ").title()}
            for c in GrantCategory
        ]
    }


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(program_id: str, db: Session = Depends(get_db)):
    """Get a specific program by ID."""
    program = db.query(GrantProgram).filter(GrantProgram.id == program_id).first()
    if not program:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Program not found")

    return ProgramResponse(
        id=program.id,
        name=program.name,
        agency=program.agency,
        category=program.category.value if program.category else None,
        min_award=program.min_award,
        max_award=program.max_award,
        match_required=program.match_required,
        description=program.description,
        eligibility_summary=program.eligibility_summary,
        deadline=program.deadline.isoformat() if program.deadline else None,
        rolling_deadline=program.rolling_deadline,
        program_url=program.program_url
    )
