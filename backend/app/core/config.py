from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    APP_NAME: str = "Marketing Agency AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./marketing_agency.db"

    # OpenAI / LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Redis (for Celery task queue)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@marketingagency.ai"

    # Agent Configuration
    SCRAPER_INTERVAL_MINUTES: int = 30
    MAX_LEADS_PER_BATCH: int = 50
    LEAD_SCORE_THRESHOLD: float = 0.6

    # API Keys for integrations
    LINKEDIN_API_KEY: Optional[str] = None
    TWITTER_BEARER_TOKEN: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CSE_ID: Optional[str] = None

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Port (Railway sets PORT env var)
    PORT: int = 8001

    class Config:
        env_file = ".env"


settings = Settings()
