import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,*"
    SANDBOX_BASE_URL: str = "http://localhost:8000"
    ADMIN_TOKEN: str = "demo-admin-secret-token"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_RECRUITER_CHAT_ID: Optional[str] = None
    TELEGRAM_CANDIDATE_CHAT_ID: Optional[str] = None
    TELEGRAM_WEBHOOK_SECRET: str = "default_secret"

    class Config:
        env_file = ".env"
        extra = "allow"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

settings = Settings()
