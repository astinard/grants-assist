"""GrantsAssist API - Consumer grant application assistance platform."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, users, programs, applications, eligibility
from app.config.settings import settings
from app.models.database import init_db

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    print("GrantsAssist API starting...")
    init_db()
    print("Database ready")
    yield


app = FastAPI(
    title="GrantsAssist API",
    description="Help individuals and small organizations find and apply for grants",
    version=VERSION,
    lifespan=lifespan,
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": VERSION}
