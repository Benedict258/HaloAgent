from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Profile info
    first_name = Column(String(100))
    last_name = Column(String(100))
    business_name = Column(String(200))
    preferred_language = Column(String(10), default="en")  # en, yo, ha, ig
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Preferences
    notification_preferences = Column(Text)  # JSON string
    business_hours = Column(Text)  # JSON string
    
    # WhatsApp Business Integration (per business)
    whatsapp_phone_number_id = Column(String(50))
    whatsapp_business_account_id = Column(String(50))
    whatsapp_access_token = Column(Text)
    whatsapp_webhook_verify_token = Column(String(100))