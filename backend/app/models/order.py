from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    items = Column(JSON, nullable=False)  # [{"name": "Jollof Rice", "qty": 2, "price": 1500}]
    status = Column(String, default="received")  # received, preparing, ready, delivered
    total = Column(Float, nullable=False)
    delivery_info = Column(JSON, nullable=True)  # {"type": "pickup/delivery", "address": "..."}
    channel = Column(String, default="whatsapp")  # whatsapp, sms, ussd
    placed_ts = Column(DateTime(timezone=True), server_default=func.now())
    updated_ts = Column(DateTime(timezone=True), onupdate=func.now())
