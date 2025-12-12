from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base

class MessageLog(Base):
    __tablename__ = "message_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    direction = Column(String, nullable=False)  # inbound, outbound
    channel = Column(String, nullable=False)  # whatsapp, sms, ussd
    content_hash = Column(String, nullable=True)
    template_id = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
