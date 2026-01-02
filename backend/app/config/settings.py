"""Application settings and configuration."""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # App
    app_name: str = "GrantsAssist"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./grants_assist.db"

    # Auth
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # External APIs
    google_api_key: str = ""
    census_api_key: str = ""

    # RevenueCat (for subscription validation)
    revenuecat_api_key: str = ""

    # Apple Push Notifications (APNs)
    apns_team_id: str = ""
    apns_key_id: str = ""
    apns_bundle_id: str = "com.grantsassist.app"
    apns_key_path: str = ""  # Path to .p8 key file (local dev)
    apns_key_content: str = ""  # .p8 key content directly (for Railway/cloud)
    apns_use_sandbox: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
