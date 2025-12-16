from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from app.db.base import Base

class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, unique=True, index=True, nullable=False)  # sweetcrumbs_001
    business_name = Column(String, nullable=False)
    whatsapp_number = Column(String, unique=True, index=True, nullable=False)  # +1415XXX
    owner_user_id = Column(Integer, nullable=True)  # Links to users table
    description = Column(Text, nullable=True)
    brand_voice = Column(Text, nullable=True)
    default_language = Column(String, default="en")
    supported_languages = Column(JSON, default=["en"])  # ["en", "yo", "ha", "ig"]
    inventory = Column(JSON, nullable=True)  # Product catalog
    payment_instructions = Column(JSON, nullable=True)  # Bank or wallet details shared with customers
    business_hours = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)
    integration_preferences = Column(JSON, nullable=True)
    webhook_url = Column(String, nullable=True)
    sandbox_code = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
