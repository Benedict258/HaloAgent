from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, unique=True, index=True, nullable=False)  # sweetcrumbs_001
    business_name = Column(String, nullable=False)
    whatsapp_number = Column(String, unique=True, index=True, nullable=False)  # +1415XXX
    owner_user_id = Column(Integer, nullable=True)  # Links to users table
    default_language = Column(String, default="en")
    supported_languages = Column(JSON, default=["en"])  # ["en", "yo", "ha", "ig"]
    inventory = Column(JSON, nullable=True)  # Product catalog
    payment_instructions = Column(JSON, nullable=True)  # Bank or wallet details shared with customers
    business_hours = Column(JSON, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
