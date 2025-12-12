from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class Reward(Base):
    __tablename__ = "rewards"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    discount_details = Column(JSON, nullable=True)  # {"type": "percent", "value": 10}
    issued_ts = Column(DateTime(timezone=True), server_default=func.now())
    used_ts = Column(DateTime(timezone=True), nullable=True)
    expiry_ts = Column(DateTime(timezone=True), nullable=True)
