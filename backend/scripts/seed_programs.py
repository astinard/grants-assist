"""Seed sample grant programs for development."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from app.models.database import SessionLocal, GrantProgram, GrantCategory

SAMPLE_PROGRAMS = [
    # Small Business
    {
        "id": "sba_7a",
        "name": "SBA 7(a) Loan Program",
        "agency": "Small Business Administration",
        "category": GrantCategory.SMALL_BUSINESS,
        "min_award": 5000,
        "max_award": 5000000,
        "match_required": 0.0,
        "description": "The 7(a) loan program is the SBA's primary program for providing financial assistance to small businesses. Funds can be used for working capital, equipment, inventory, or real estate.",
        "eligibility_summary": "Must be a for-profit business operating in the US, meet SBA size standards, demonstrate need for financing, and have reasonable owner equity.",
        "rolling_deadline": True,
        "program_url": "https://www.sba.gov/funding-programs/loans/7a-loans",
        "is_active": True,
    },
    {
        "id": "sba_microloan",
        "name": "SBA Microloan Program",
        "agency": "Small Business Administration",
        "category": GrantCategory.SMALL_BUSINESS,
        "min_award": 500,
        "max_award": 50000,
        "match_required": 0.0,
        "description": "Provides small, short-term loans to small businesses and certain nonprofit childcare centers. Can be used for working capital, inventory, supplies, furniture, fixtures, or equipment.",
        "eligibility_summary": "Must be a small business or nonprofit childcare center. Startups and new businesses are eligible.",
        "rolling_deadline": True,
        "program_url": "https://www.sba.gov/funding-programs/loans/microloans",
        "is_active": True,
    },
    {
        "id": "sba_womens_biz",
        "name": "Women's Business Center Grants",
        "agency": "Small Business Administration",
        "category": GrantCategory.SMALL_BUSINESS,
        "min_award": 10000,
        "max_award": 150000,
        "match_required": 0.5,
        "description": "Grants to support organizations that provide business training and counseling to women entrepreneurs.",
        "eligibility_summary": "Must be a woman-owned small business or nonprofit serving women entrepreneurs.",
        "deadline": datetime.now() + timedelta(days=90),
        "rolling_deadline": False,
        "program_url": "https://www.sba.gov/local-assistance/womens-business-centers",
        "is_active": True,
    },
    # Healthcare
    {
        "id": "hrsa_rural_health",
        "name": "Rural Health Clinic Grant Program",
        "agency": "Health Resources & Services Administration",
        "category": GrantCategory.HEALTHCARE,
        "min_award": 25000,
        "max_award": 200000,
        "match_required": 0.0,
        "description": "Supports rural health clinics in improving quality of care, expanding services, and implementing new technologies.",
        "eligibility_summary": "Must be a certified Rural Health Clinic located in a designated rural area with demonstrated healthcare access needs.",
        "deadline": datetime.now() + timedelta(days=60),
        "rolling_deadline": False,
        "program_url": "https://www.hrsa.gov/rural-health",
        "is_active": True,
    },
    {
        "id": "hrsa_community_health",
        "name": "Community Health Center Expansion",
        "agency": "Health Resources & Services Administration",
        "category": GrantCategory.HEALTHCARE,
        "min_award": 100000,
        "max_award": 1000000,
        "match_required": 0.0,
        "description": "Funding to expand access to comprehensive primary health care services in underserved communities.",
        "eligibility_summary": "Must be a Federally Qualified Health Center (FQHC) or organization applying for FQHC status.",
        "deadline": datetime.now() + timedelta(days=120),
        "rolling_deadline": False,
        "program_url": "https://www.hrsa.gov/grants/find-funding",
        "is_active": True,
    },
    # Education / Scholarships
    {
        "id": "pell_grant",
        "name": "Federal Pell Grant",
        "agency": "Department of Education",
        "category": GrantCategory.EDUCATION,
        "min_award": 750,
        "max_award": 7395,
        "match_required": 0.0,
        "description": "Need-based grants for undergraduate students pursuing their first bachelor's degree. Does not need to be repaid.",
        "eligibility_summary": "Must demonstrate exceptional financial need, be a US citizen or eligible noncitizen, and be enrolled in an eligible degree program.",
        "rolling_deadline": True,
        "program_url": "https://studentaid.gov/understand-aid/types/grants/pell",
        "is_active": True,
    },
    {
        "id": "teach_grant",
        "name": "TEACH Grant",
        "agency": "Department of Education",
        "category": GrantCategory.EDUCATION,
        "min_award": 1000,
        "max_award": 4000,
        "match_required": 0.0,
        "description": "Grants for students who intend to teach in high-need fields at schools serving low-income students.",
        "eligibility_summary": "Must be enrolled in eligible program, maintain 3.25 GPA, and agree to teach for 4 years in a high-need field.",
        "rolling_deadline": True,
        "program_url": "https://studentaid.gov/understand-aid/types/grants/teach",
        "is_active": True,
    },
    {
        "id": "stem_scholarship",
        "name": "National STEM Scholarship",
        "agency": "National Science Foundation",
        "category": GrantCategory.EDUCATION,
        "min_award": 5000,
        "max_award": 25000,
        "match_required": 0.0,
        "description": "Scholarships for students pursuing degrees in science, technology, engineering, and mathematics fields.",
        "eligibility_summary": "Must be enrolled full-time in a STEM program, maintain 3.0 GPA, and demonstrate financial need.",
        "deadline": datetime.now() + timedelta(days=45),
        "rolling_deadline": False,
        "program_url": "https://www.nsf.gov/funding/",
        "is_active": True,
    },
    # Nonprofit
    {
        "id": "nonprofit_capacity",
        "name": "Nonprofit Capacity Building Grant",
        "agency": "Corporation for National Service",
        "category": GrantCategory.NONPROFIT,
        "min_award": 10000,
        "max_award": 75000,
        "match_required": 0.25,
        "description": "Funding to strengthen nonprofit organizations' ability to achieve their missions through improved operations and programs.",
        "eligibility_summary": "Must be a 501(c)(3) organization with at least 2 years of operation and demonstrated community impact.",
        "deadline": datetime.now() + timedelta(days=75),
        "rolling_deadline": False,
        "program_url": "https://americorps.gov/grants",
        "is_active": True,
    },
    {
        "id": "community_foundation",
        "name": "Community Development Block Grant",
        "agency": "Housing and Urban Development",
        "category": GrantCategory.NONPROFIT,
        "min_award": 25000,
        "max_award": 500000,
        "match_required": 0.0,
        "description": "Flexible funding to address community development needs including housing, economic development, and public services.",
        "eligibility_summary": "Must be a local government or nonprofit serving low-to-moderate income communities.",
        "deadline": datetime.now() + timedelta(days=100),
        "rolling_deadline": False,
        "program_url": "https://www.hud.gov/program_offices/comm_planning/cdbg",
        "is_active": True,
    },
    # Agriculture
    {
        "id": "usda_value_added",
        "name": "Value-Added Producer Grant",
        "agency": "USDA Rural Development",
        "category": GrantCategory.AGRICULTURE,
        "min_award": 10000,
        "max_award": 250000,
        "match_required": 0.5,
        "description": "Grants to help agricultural producers enter into value-added activities, develop new products, and expand marketing.",
        "eligibility_summary": "Must be an independent agricultural producer, farmer cooperative, or majority-controlled producer-based business.",
        "deadline": datetime.now() + timedelta(days=80),
        "rolling_deadline": False,
        "program_url": "https://www.rd.usda.gov/programs-services/business-programs/value-added-producer-grants",
        "is_active": True,
    },
    {
        "id": "usda_beginning_farmer",
        "name": "Beginning Farmer and Rancher Loan",
        "agency": "USDA Farm Service Agency",
        "category": GrantCategory.AGRICULTURE,
        "min_award": 5000,
        "max_award": 600000,
        "match_required": 0.0,
        "description": "Low-interest loans for beginning farmers and ranchers who cannot obtain commercial credit.",
        "eligibility_summary": "Must have operated a farm for less than 10 years, meet training requirements, and be unable to obtain credit elsewhere.",
        "rolling_deadline": True,
        "program_url": "https://www.fsa.usda.gov/programs-and-services/farm-loan-programs/beginning-farmers-and-ranchers-loans",
        "is_active": True,
    },
    # Technology
    {
        "id": "sbir_phase1",
        "name": "Small Business Innovation Research (SBIR) Phase I",
        "agency": "National Science Foundation",
        "category": GrantCategory.TECHNOLOGY,
        "min_award": 50000,
        "max_award": 275000,
        "match_required": 0.0,
        "description": "Funding for small businesses to conduct R&D with commercial potential. Phase I establishes feasibility.",
        "eligibility_summary": "Must be a US small business with fewer than 500 employees. Principal investigator must be primarily employed by the company.",
        "deadline": datetime.now() + timedelta(days=65),
        "rolling_deadline": False,
        "program_url": "https://www.sbir.gov/",
        "is_active": True,
    },
    {
        "id": "sttr_grant",
        "name": "Small Business Technology Transfer (STTR)",
        "agency": "Department of Energy",
        "category": GrantCategory.TECHNOLOGY,
        "min_award": 75000,
        "max_award": 250000,
        "match_required": 0.0,
        "description": "Funding for small businesses partnering with research institutions to move innovations from lab to market.",
        "eligibility_summary": "Must be a US small business partnering with a nonprofit research institution. At least 40% of work at small business, 30% at research institution.",
        "deadline": datetime.now() + timedelta(days=55),
        "rolling_deadline": False,
        "program_url": "https://www.sbir.gov/about/about-sttr",
        "is_active": True,
    },
    # Housing
    {
        "id": "hud_home",
        "name": "HOME Investment Partnerships Program",
        "agency": "Housing and Urban Development",
        "category": GrantCategory.HOUSING,
        "min_award": 50000,
        "max_award": 1000000,
        "match_required": 0.25,
        "description": "Grants to fund affordable housing activities including building, buying, and rehabilitating affordable housing.",
        "eligibility_summary": "Must be a state, local government, or designated Community Housing Development Organization (CHDO).",
        "deadline": datetime.now() + timedelta(days=110),
        "rolling_deadline": False,
        "program_url": "https://www.hud.gov/program_offices/comm_planning/home",
        "is_active": True,
    },
    {
        "id": "rural_housing",
        "name": "Rural Housing Repair Grant",
        "agency": "USDA Rural Development",
        "category": GrantCategory.HOUSING,
        "min_award": 1000,
        "max_award": 10000,
        "match_required": 0.0,
        "description": "Grants to very low-income homeowners to repair, improve, or modernize their homes and remove health hazards.",
        "eligibility_summary": "Must own and occupy the home in a rural area, be 62 or older, and be unable to repay a repair loan.",
        "rolling_deadline": True,
        "program_url": "https://www.rd.usda.gov/programs-services/single-family-housing-programs/single-family-housing-repair-loans-grants",
        "is_active": True,
    },
]


def seed_programs():
    """Seed sample grant programs."""
    db = SessionLocal()
    try:
        added = 0
        for program_data in SAMPLE_PROGRAMS:
            existing = db.query(GrantProgram).filter(GrantProgram.id == program_data["id"]).first()
            if not existing:
                program = GrantProgram(**program_data)
                db.add(program)
                added += 1
                print(f"  + {program_data['name']}")
            else:
                print(f"  = {program_data['name']} (exists)")

        db.commit()
        print(f"\nSeeded {added} new programs ({len(SAMPLE_PROGRAMS)} total)")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding grant programs...\n")
    seed_programs()
