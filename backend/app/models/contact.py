from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float
from sqlalchemy.sql import func
from app.db.base import Base

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    language = Column(String, default="en")  # en, yo, ha, ig
    opt_in_ts = Column(DateTime(timezone=True), server_default=func.now())
    opt_in_text = Column(String, nullable=True)
    loyalty_count = Column(Integer, default=0)
    last_order_ts = Column(DateTime(timezone=True), nullable=True)
    churn_score = Column(Float, default=0.0)
    deleted_flag = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
