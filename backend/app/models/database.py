"""Database models for GrantsAssist."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, Enum as SQLEnum, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.config.settings import settings

Base = declarative_base()


# ============ Enums ============

class GrantCategory(str, Enum):
    """Categories of grants supported."""
    HEALTHCARE = "healthcare"
    SMALL_BUSINESS = "small_business"
    EDUCATION = "education"  # Scholarships
    NONPROFIT = "nonprofit"
    AGRICULTURE = "agriculture"
    TECHNOLOGY = "technology"
    HOUSING = "housing"


class ApplicationStatus(str, Enum):
    """Status of a grant application."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"


class SubscriptionTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"           # 1 app/month, basic features
    PRO = "pro"             # $9.99/mo - unlimited apps, AI narratives
    BUSINESS = "business"   # $29.99/mo - team features, priority


class SectionType(str, Enum):
    """Types of professional grant sections."""
    COVER_LETTER = "cover_letter"
    EXECUTIVE_SUMMARY = "executive_summary"
    ORGANIZATIONAL_BACKGROUND = "organizational_background"
    STATEMENT_OF_NEED = "statement_of_need"
    PROJECT_DESCRIPTION = "project_description"
    GOALS_OBJECTIVES = "goals_objectives"
    EVALUATION_PLAN = "evaluation_plan"
    BUDGET_NARRATIVE = "budget_narrative"
    SUSTAINABILITY_PLAN = "sustainability_plan"
    CONCLUSION = "conclusion"


class PriorGrantStatus(str, Enum):
    """Status of prior grants."""
    AWARDED = "awarded"
    PENDING = "pending"
    DENIED = "denied"


class CommunityDataType(str, Enum):
    """Types of community data for statement of need."""
    DEMOGRAPHIC = "demographic"
    ECONOMIC = "economic"
    HEALTH = "health"
    EDUCATION = "education"
    INFRASTRUCTURE = "infrastructure"
    EMPLOYMENT = "employment"
    OTHER = "other"


class BudgetCategory(str, Enum):
    """Budget line item categories."""
    PERSONNEL = "personnel"
    FRINGE_BENEFITS = "fringe_benefits"
    TRAVEL = "travel"
    EQUIPMENT = "equipment"
    SUPPLIES = "supplies"
    CONTRACTUAL = "contractual"
    CONSTRUCTION = "construction"
    OTHER = "other"
    INDIRECT_COSTS = "indirect_costs"


# ============ Models ============

class User(Base):
    """User account - authenticated via Apple Sign-In or email."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Null if Apple Sign-In
    apple_user_id = Column(String(255), unique=True, nullable=True)

    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_expires_at = Column(DateTime, nullable=True)
    revenuecat_id = Column(String(255), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    applications = relationship("Application", back_populates="user")


class UserProfile(Base):
    """User profile - reusable info for grant applications."""
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Personal/Org Info
    full_name = Column(String(255))
    organization_name = Column(String(255))
    organization_type = Column(String(100))  # nonprofit, small_business, individual, etc.

    # Address
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    congressional_district = Column(String(10))

    # Federal IDs (for orgs)
    ein = Column(String(20))
    uei_number = Column(String(20))
    sam_registered = Column(Boolean, default=False)
    duns_number = Column(String(20))

    # Contact
    phone = Column(String(20))
    website = Column(String(255))

    # Demographics (for scholarships, some grants)
    is_veteran = Column(Boolean)
    is_minority_owned = Column(Boolean)
    is_woman_owned = Column(Boolean)
    is_rural = Column(Boolean)
    annual_revenue = Column(Float)
    employee_count = Column(Integer)
    years_in_operation = Column(Integer)

    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="profile")


class GrantProgram(Base):
    """Grant programs available in the system."""
    __tablename__ = "grant_programs"

    id = Column(String(50), primary_key=True)  # e.g., "usda_dlt", "sba_7a"
    name = Column(String(255), nullable=False)
    agency = Column(String(100))  # USDA, SBA, HHS, etc.
    category = Column(SQLEnum(GrantCategory))

    # Funding
    min_award = Column(Float)
    max_award = Column(Float)
    match_required = Column(Float)  # 0.0 to 1.0

    # Eligibility summary
    description = Column(Text)
    eligibility_summary = Column(Text)
    required_fields = Column(Text)  # JSON list of required fields

    # Deadlines
    deadline = Column(DateTime, nullable=True)
    rolling_deadline = Column(Boolean, default=False)

    # Links
    program_url = Column(String(500))
    application_url = Column(String(500))

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    applications = relationship("Application", back_populates="program")


class Application(Base):
    """A user's application for a specific grant."""
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    program_id = Column(String(50), ForeignKey("grant_programs.id"), nullable=False)

    # Status
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    completeness_score = Column(Float, default=0.0)  # 0-100

    # Application data (JSON)
    form_data = Column(Text)  # JSON blob of all form fields
    generated_narrative = Column(Text)

    # Documents
    pdf_path = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="applications")
    program = relationship("GrantProgram", back_populates="applications")


class DeviceToken(Base):
    """Device tokens for push notifications."""
    __tablename__ = "device_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    device_token = Column(String(255), nullable=False, index=True)
    platform = Column(String(20), nullable=False)  # "ios" or "android"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="device_tokens")


class NotificationPreference(Base):
    """User notification preferences."""
    __tablename__ = "notification_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)

    # Notification types
    deadline_reminders = Column(Boolean, default=True)
    application_updates = Column(Boolean, default=True)
    new_grant_alerts = Column(Boolean, default=False)

    # Reminder timing (JSON array of days before deadline)
    reminder_days_before = Column(Text, default="[7, 3, 1]")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="notification_preferences")


# ============ Professional Grant Writing Models ============

class OrganizationProfile(Base):
    """Extended organization profile for professional grant writing."""
    __tablename__ = "organization_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)

    # Mission & History
    mission_statement = Column(Text)
    vision_statement = Column(Text)
    founding_year = Column(Integer)
    service_area = Column(Text)  # Geographic area served
    service_area_population = Column(Integer)

    # Organizational Capacity
    annual_budget = Column(Float)
    staff_count = Column(Integer)
    volunteer_count = Column(Integer)
    board_size = Column(Integer)

    # Credentials
    certifications = Column(Text)  # JSON list
    accreditations = Column(Text)  # JSON list
    key_partnerships = Column(Text)  # JSON list of partner organizations

    # Impact Metrics
    clients_served_annually = Column(Integer)
    geographic_reach = Column(String(255))  # e.g., "5 counties in rural Kentucky"
    programs_offered = Column(Text)  # JSON list of program names

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="organization_profile")


class PriorGrant(Base):
    """Track prior grants for organizational credibility."""
    __tablename__ = "prior_grants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Grant Details
    funder_name = Column(String(255), nullable=False)
    grant_title = Column(String(255))
    amount = Column(Float)
    year_awarded = Column(Integer)
    status = Column(SQLEnum(PriorGrantStatus), default=PriorGrantStatus.AWARDED)

    # Outcomes
    outcomes_achieved = Column(Text)  # Description of what was accomplished
    metrics_achieved = Column(Text)  # JSON: {"people_served": 500, "jobs_created": 25}
    lessons_learned = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="prior_grants")


class Achievement(Base):
    """Quantifiable organizational achievements."""
    __tablename__ = "achievements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Achievement Details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "impact", "award", "milestone", "growth"

    # Metrics
    metric_value = Column(Float)
    metric_unit = Column(String(50))  # e.g., "people", "dollars", "percent"
    year = Column(Integer)

    # Evidence
    evidence_url = Column(String(500))
    source = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="achievements")


class CommunityData(Base):
    """Community statistics for statement of need."""
    __tablename__ = "community_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Data Classification
    data_type = Column(SQLEnum(CommunityDataType), nullable=False)
    indicator = Column(String(255), nullable=False)  # e.g., "Poverty Rate", "Unemployment"

    # Values
    statistic = Column(String(255), nullable=False)  # e.g., "23.5%", "45,000"
    comparison_value = Column(String(255))  # e.g., "National average: 11.4%"
    trend = Column(String(100))  # e.g., "increasing", "stable", "declining"

    # Source
    source = Column(String(255), nullable=False)  # e.g., "US Census Bureau"
    source_year = Column(Integer)
    source_url = Column(String(500))

    # Geography
    geographic_area = Column(String(255))  # e.g., "Harlan County, KY"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="community_data")


class BudgetLineItem(Base):
    """Individual budget line items for applications."""
    __tablename__ = "budget_line_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False)

    # Category & Description
    category = Column(SQLEnum(BudgetCategory), nullable=False)
    description = Column(String(500), nullable=False)

    # Costs
    unit_cost = Column(Float, nullable=False)
    quantity = Column(Float, default=1)
    total_cost = Column(Float)  # Calculated: unit_cost * quantity

    # Justification
    justification = Column(Text)  # Why this expense is necessary
    is_matching = Column(Boolean, default=False)  # True if this is match/cost-share

    # Order for display
    sort_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", backref="budget_line_items")


class ApplicationSection(Base):
    """Individual sections of a professional grant application."""
    __tablename__ = "application_sections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False)

    # Section Info
    section_type = Column(SQLEnum(SectionType), nullable=False)
    content = Column(Text)
    word_count = Column(Integer, default=0)

    # Quality Tracking
    quality_score = Column(Float)  # 0-100
    ai_feedback = Column(Text)  # Suggestions for improvement
    relevance_score = Column(Float)  # How relevant to funder priorities
    evidence_score = Column(Float)  # Use of data and evidence

    # Versioning
    version = Column(Integer, default=1)
    is_final = Column(Boolean, default=False)
    is_user_edited = Column(Boolean, default=False)

    # Generation metadata
    generation_prompt = Column(Text)  # Store the prompt used
    generation_model = Column(String(100))  # e.g., "gemini-2.0-flash"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    application = relationship("Application", backref="sections")


# ============ Database Setup ============

def get_database_url():
    """Get database URL, converting Railway's postgres:// to postgresql://."""
    url = settings.database_url
    # Railway uses postgres:// but SQLAlchemy 2.0+ requires postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

# Configure engine based on database type
database_url = get_database_url()

if database_url.startswith("postgresql://"):
    # PostgreSQL configuration with connection pooling
    engine = create_engine(
        database_url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
    )
else:
    # SQLite configuration (local development)
    engine = create_engine(
        database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False}  # SQLite specific
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
