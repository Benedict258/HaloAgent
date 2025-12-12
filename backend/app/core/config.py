from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

# Ensure the backend .env file is loaded no matter where the app is started
BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = "your_supabase_project_url"
    SUPABASE_KEY: str = "your_supabase_anon_key"
    SUPABASE_SERVICE_KEY: str = "your_supabase_service_role_key"
    
    # Meta AI
    META_AI_API_KEY: str = "placeholder_key"
    META_AI_ENDPOINT: str = "https://api.meta.ai/v1"
    
    # WhatsApp
    WHATSAPP_API_TOKEN: str = "placeholder_token"
    WHATSAPP_PHONE_NUMBER_ID: str = "placeholder_id"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = "placeholder_account"
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "haloagent_verify_2024"
    
    # SMS
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    
    # USSD
    USSD_API_KEY: Optional[str] = None
    USSD_ENDPOINT: Optional[str] = None
    
    # Airtable
    AIRTABLE_API_KEY: Optional[str] = None
    AIRTABLE_BASE_ID: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "haloagent-dev-secret-key-min-32-chars-2024"
    ENCRYPTION_KEY: str = "haloagent-encryption-key-32bytes"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # App
    ENVIRONMENT: str = "development"
    DEBUG: str = "True"
    RETENTION_DAYS: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
