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
    weights = Column(JSON, nullable=False)
    optimization_method = Column(String(50), nullable=False)
    expected_return = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    
    # 개인투자자 특화 리스크 지표
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    calmar_ratio = Column(Float, nullable=True)
    value_at_risk_95 = Column(Float, nullable=True)
    
    # 최적화 설정 파라미터
    transaction_cost = Column(Float, nullable=True, default=0.001)
    max_position_size = Column(Float, nullable=True, default=0.30)
    
    # 추가 메타데이터
    correlation_matrix = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
