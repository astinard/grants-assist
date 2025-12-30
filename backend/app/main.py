"""
GrantsAssist API - Consumer grant application assistance platform
Supports: Scholarships, Small Business, Healthcare, and more
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, users, programs, applications, eligibility
from app.config.settings import settings
from app.models.database import init_db

app = FastAPI(
    title="GrantsAssist API",
    description="Help individuals and small organizations find and apply for grants",
    version="0.1.0",
)

# CORS for iOS app and web
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(programs.router)
app.include_router(applications.router)
app.include_router(eligibility.router)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    print("GrantsAssist API starting...")
    init_db()
    print("Database ready")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
