"""Grant programs API."""
from typing import List, Optional
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db, GrantProgram, GrantCategory
from app.services.pdf_generator import generate_grant_summary_pdf

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


# ============ Helpers ============

def build_program_response(p: GrantProgram) -> ProgramResponse:
    """Build ProgramResponse from GrantProgram model."""
    return ProgramResponse(
        id=p.id, name=p.name, agency=p.agency,
        category=p.category.value if p.category else None,
        min_award=p.min_award, max_award=p.max_award, match_required=p.match_required,
        description=p.description, eligibility_summary=p.eligibility_summary,
        deadline=p.deadline.isoformat() if p.deadline else None,
        rolling_deadline=p.rolling_deadline, program_url=p.program_url
    )


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
        query = query.filter(GrantProgram.is_active.is_(True))

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
        total=len(programs), programs=[build_program_response(p) for p in programs]
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
        raise HTTPException(status_code=404, detail="Program not found")
    return build_program_response(program)


@router.get("/{program_id}/pdf")
async def download_program_pdf(program_id: str, db: Session = Depends(get_db)):
    """Download grant program summary as PDF."""
    program = db.query(GrantProgram).filter(GrantProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    program_data = {
        "id": program.id,
        "name": program.name,
        "agency": program.agency,
        "category": program.category.value if program.category else None,
        "description": program.description,
        "eligibility_summary": program.eligibility_summary,
        "min_award": program.min_award,
        "max_award": program.max_award,
        "match_required": program.match_required,
        "deadline": program.deadline.isoformat() if program.deadline else None,
        "rolling_deadline": program.rolling_deadline,
        "program_url": program.program_url,
    }

    pdf_buffer = generate_grant_summary_pdf(program_data)

    filename = f"grant_{program.id}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_buffer),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/seed")
async def seed_programs(db: Session = Depends(get_db)):
    """Seed database with sample grant programs."""
    from datetime import datetime, timedelta

    # Check if already seeded
    existing = db.query(GrantProgram).count()
    if existing > 0:
        return {"message": f"Database already has {existing} programs", "seeded": 0}

    SAMPLE_PROGRAMS = [
        # Small Business
        {"id": "sba_7a", "name": "SBA 7(a) Loan Program", "agency": "Small Business Administration",
         "category": GrantCategory.SMALL_BUSINESS, "min_award": 5000, "max_award": 5000000,
         "description": "The 7(a) loan program is the SBA's primary program for providing financial assistance to small businesses.",
         "eligibility_summary": "Must be a for-profit business operating in the US, meet SBA size standards.",
         "rolling_deadline": True, "program_url": "https://www.sba.gov/funding-programs/loans/7a-loans", "is_active": True},
        {"id": "sba_microloan", "name": "SBA Microloan Program", "agency": "Small Business Administration",
         "category": GrantCategory.SMALL_BUSINESS, "min_award": 500, "max_award": 50000,
         "description": "Provides small, short-term loans to small businesses and certain nonprofit childcare centers.",
         "eligibility_summary": "Must be a small business or nonprofit childcare center. Startups eligible.",
         "rolling_deadline": True, "program_url": "https://www.sba.gov/funding-programs/loans/microloans", "is_active": True},
        {"id": "sbir_phase1", "name": "Small Business Innovation Research (SBIR) Phase I", "agency": "National Science Foundation",
         "category": GrantCategory.SMALL_BUSINESS, "min_award": 50000, "max_award": 275000,
         "description": "Funding for small businesses to conduct R&D with commercial potential.",
         "eligibility_summary": "US small business with fewer than 500 employees.",
         "deadline": datetime.now() + timedelta(days=65), "rolling_deadline": False,
         "program_url": "https://www.sbir.gov/", "is_active": True},

        # Healthcare
        {"id": "hrsa_rural_health", "name": "Rural Health Clinic Grant Program", "agency": "HRSA",
         "category": GrantCategory.HEALTHCARE, "min_award": 25000, "max_award": 200000,
         "description": "Supports rural health clinics in improving quality of care and expanding services.",
         "eligibility_summary": "Must be a certified Rural Health Clinic in a designated rural area.",
         "deadline": datetime.now() + timedelta(days=60), "rolling_deadline": False,
         "program_url": "https://www.hrsa.gov/rural-health", "is_active": True},
        {"id": "hrsa_community_health", "name": "Community Health Center Expansion", "agency": "HRSA",
         "category": GrantCategory.HEALTHCARE, "min_award": 100000, "max_award": 1000000,
         "description": "Funding to expand access to comprehensive primary health care services in underserved communities.",
         "eligibility_summary": "Must be a Federally Qualified Health Center (FQHC).",
         "deadline": datetime.now() + timedelta(days=120), "rolling_deadline": False,
         "program_url": "https://www.hrsa.gov/grants/find-funding", "is_active": True},
        {"id": "cdc_preventive", "name": "Preventive Health Services Block Grant", "agency": "CDC",
         "category": GrantCategory.HEALTHCARE, "min_award": 50000, "max_award": 500000, "match_required": 0.25,
         "description": "Provides funding to address gaps in health services at the community level.",
         "eligibility_summary": "State/local health departments, tribal organizations, community health centers.",
         "rolling_deadline": True, "program_url": "https://www.cdc.gov/phhsblockgrant/", "is_active": True},

        # Education
        {"id": "pell_grant", "name": "Federal Pell Grant", "agency": "Department of Education",
         "category": GrantCategory.EDUCATION, "min_award": 750, "max_award": 7395,
         "description": "Need-based grants for undergraduate students pursuing their first bachelor's degree.",
         "eligibility_summary": "Must demonstrate exceptional financial need, be a US citizen or eligible noncitizen.",
         "rolling_deadline": True, "program_url": "https://studentaid.gov/understand-aid/types/grants/pell", "is_active": True},
        {"id": "teach_grant", "name": "TEACH Grant", "agency": "Department of Education",
         "category": GrantCategory.EDUCATION, "min_award": 1000, "max_award": 4000,
         "description": "Grants for students who intend to teach in high-need fields at schools serving low-income students.",
         "eligibility_summary": "Must maintain 3.25 GPA and agree to teach for 4 years in a high-need field.",
         "rolling_deadline": True, "program_url": "https://studentaid.gov/understand-aid/types/grants/teach", "is_active": True},
        {"id": "fulbright", "name": "Fulbright U.S. Student Program", "agency": "State Department",
         "category": GrantCategory.EDUCATION, "min_award": 15000, "max_award": 50000,
         "description": "Scholarships for U.S. students to study, teach, or conduct research abroad.",
         "eligibility_summary": "U.S. citizens with a bachelor's degree by the start of the grant.",
         "deadline": datetime.now() + timedelta(days=180), "rolling_deadline": False,
         "program_url": "https://us.fulbrightonline.org/", "is_active": True},

        # Nonprofit
        {"id": "americorps_state", "name": "AmeriCorps State and National Grants", "agency": "CNCS",
         "category": GrantCategory.NONPROFIT, "min_award": 100000, "max_award": 1500000, "match_required": 0.24,
         "description": "Supports organizations engaging AmeriCorps members in evidence-based interventions.",
         "eligibility_summary": "Nonprofit organizations, higher education institutions, state/local governments.",
         "deadline": datetime.now() + timedelta(days=45), "rolling_deadline": False,
         "program_url": "https://americorps.gov/funding-opportunity", "is_active": True},
        {"id": "neh_humanities", "name": "NEH Humanities Connections Planning Grants", "agency": "NEH",
         "category": GrantCategory.NONPROFIT, "min_award": 25000, "max_award": 50000,
         "description": "Supports planning of programs that integrate humanities into STEM and career education.",
         "eligibility_summary": "Accredited colleges, universities, and nonprofit cultural organizations.",
         "deadline": datetime.now() + timedelta(days=100), "rolling_deadline": False,
         "program_url": "https://www.neh.gov/grants", "is_active": True},
        {"id": "fema_bric", "name": "Building Resilient Infrastructure and Communities", "agency": "FEMA",
         "category": GrantCategory.NONPROFIT, "min_award": 75000, "max_award": 50000000, "match_required": 0.25,
         "description": "Supports pre-disaster mitigation projects for communities.",
         "eligibility_summary": "State, local, tribal governments, and nonprofits in declared disaster areas.",
         "deadline": datetime.now() + timedelta(days=150), "rolling_deadline": False,
         "program_url": "https://www.fema.gov/grants/mitigation/building-resilient-infrastructure-communities", "is_active": True},

        # Agriculture
        {"id": "usda_value_added", "name": "Value-Added Producer Grant", "agency": "USDA Rural Development",
         "category": GrantCategory.AGRICULTURE, "min_award": 10000, "max_award": 250000, "match_required": 0.5,
         "description": "Helps agricultural producers enter value-added activities and develop new products.",
         "eligibility_summary": "Independent agricultural producers, farmer cooperatives.",
         "deadline": datetime.now() + timedelta(days=80), "rolling_deadline": False,
         "program_url": "https://www.rd.usda.gov/programs-services/business-programs/value-added-producer-grants", "is_active": True},
        {"id": "usda_beginning_farmer", "name": "Beginning Farmer and Rancher Loan", "agency": "USDA FSA",
         "category": GrantCategory.AGRICULTURE, "min_award": 5000, "max_award": 600000,
         "description": "Low-interest loans for beginning farmers who cannot obtain commercial credit.",
         "eligibility_summary": "Must have operated a farm for less than 10 years.",
         "rolling_deadline": True, "program_url": "https://www.fsa.usda.gov/programs-and-services/farm-loan-programs", "is_active": True},
        {"id": "usda_specialty_crop", "name": "Specialty Crop Block Grant Program", "agency": "USDA AMS",
         "category": GrantCategory.AGRICULTURE, "min_award": 10000, "max_award": 500000,
         "description": "Enhances competitiveness of specialty crops including fruits, vegetables, nursery crops.",
         "eligibility_summary": "State departments of agriculture distributing funds to specialty crop producers.",
         "deadline": datetime.now() + timedelta(days=120), "rolling_deadline": False,
         "program_url": "https://www.ams.usda.gov/services/grants/scbgp", "is_active": True},

        # Technology
        {"id": "nsf_sttr", "name": "NSF Small Business Technology Transfer (STTR)", "agency": "NSF",
         "category": GrantCategory.TECHNOLOGY, "min_award": 50000, "max_award": 300000,
         "description": "Funds collaborative research between small businesses and research institutions.",
         "eligibility_summary": "US small businesses partnered with nonprofit research institutions.",
         "deadline": datetime.now() + timedelta(days=80), "rolling_deadline": False,
         "program_url": "https://seedfund.nsf.gov/", "is_active": True},
        {"id": "doe_arpa_e", "name": "ARPA-E Exploratory Topics", "agency": "DOE",
         "category": GrantCategory.TECHNOLOGY, "min_award": 250000, "max_award": 5000000, "match_required": 0.2,
         "description": "Funds transformational energy technologies too early for private-sector investment.",
         "eligibility_summary": "Universities, national labs, businesses of all sizes, nonprofits.",
         "deadline": datetime.now() + timedelta(days=45), "rolling_deadline": False,
         "program_url": "https://arpa-e.energy.gov/", "is_active": True},
        {"id": "ntia_broadband", "name": "Broadband Equity, Access, and Deployment (BEAD)", "agency": "NTIA",
         "category": GrantCategory.TECHNOLOGY, "min_award": 100000, "max_award": 100000000, "match_required": 0.25,
         "description": "Funds broadband infrastructure deployment to unserved and underserved areas.",
         "eligibility_summary": "State broadband offices, municipalities, cooperatives, and ISPs.",
         "deadline": datetime.now() + timedelta(days=200), "rolling_deadline": False,
         "program_url": "https://broadbandusa.ntia.doc.gov/funding-programs", "is_active": True},

        # Housing
        {"id": "hud_cdbg", "name": "Community Development Block Grant (CDBG)", "agency": "HUD",
         "category": GrantCategory.HOUSING, "min_award": 100000, "max_award": 3000000,
         "description": "Provides resources to address housing and community development needs.",
         "eligibility_summary": "Cities, counties, and states. 70% must benefit low/moderate-income persons.",
         "rolling_deadline": True, "program_url": "https://www.hud.gov/program_offices/comm_planning/cdbg", "is_active": True},
        {"id": "hud_home", "name": "HOME Investment Partnerships Program", "agency": "HUD",
         "category": GrantCategory.HOUSING, "min_award": 50000, "max_award": 5000000, "match_required": 0.25,
         "description": "Formula grants for affordable housing activities.",
         "eligibility_summary": "State and local governments (participating jurisdictions).",
         "rolling_deadline": True, "program_url": "https://www.hud.gov/program_offices/comm_planning/home", "is_active": True},
        {"id": "usda_rural_housing", "name": "USDA Section 502 Direct Loan Program", "agency": "USDA",
         "category": GrantCategory.HOUSING, "min_award": 20000, "max_award": 400000,
         "description": "Payment assistance to low and very-low income homebuyers in rural areas.",
         "eligibility_summary": "Low-income individuals in eligible rural areas without decent housing.",
         "rolling_deadline": True, "program_url": "https://www.rd.usda.gov/programs-services/single-family-housing-programs", "is_active": True},
    ]

    added = 0
    for data in SAMPLE_PROGRAMS:
        program = GrantProgram(**data)
        db.add(program)
        added += 1

    db.commit()
    return {"message": f"Successfully seeded {added} grant programs", "seeded": added}
