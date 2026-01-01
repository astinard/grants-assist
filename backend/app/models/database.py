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


# ============ Database Setup ============

engine = create_engine(settings.database_url, echo=settings.debug)
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
