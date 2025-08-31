from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from .base import Base
from sqlalchemy.sql import func

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    tickers = Column(JSON, nullable=False)
    optimization_method = Column(String(50), nullable=False)
    rebalance_frequency = Column(String(20), nullable=True, default="monthly")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
