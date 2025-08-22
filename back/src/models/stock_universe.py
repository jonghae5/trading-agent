"""Stock universe database models for fast local search."""

from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class StockInfo(Base):
    """Stock information for fast local search."""
    __tablename__ = "stock_info"
    
    symbol = Column(String(10), primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)  # Full company name
    short_name = Column(String(100), nullable=True)  # Short name
    exchange = Column(String(20), nullable=False, index=True)
    sector = Column(String(50), nullable=True, index=True)
    industry = Column(String(100), nullable=True, index=True)
    market_cap = Column(Float, nullable=True, index=True)
    currency = Column(String(10), default='USD')
    country = Column(String(50), nullable=True)
    
    # Stock type categorization
    stock_type = Column(String(20), default='equity', index=True)  # equity, etf, fund, etc
    
    # Search optimization fields
    name_upper = Column(String(200), index=True)  # Uppercase name for fast search
    keywords = Column(Text, nullable=True)  # Additional search keywords
    
    # Market data (updated less frequently)
    avg_volume = Column(Float, nullable=True)
    shares_outstanding = Column(Float, nullable=True)
    
    # Status flags
    is_active = Column(Boolean, default=True, index=True)
    is_popular = Column(Boolean, default=False, index=True)  # Pre-mark popular stocks
    popularity_rank = Column(Integer, nullable=True, index=True)  # Ranking by market cap/volume
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_price_fetch = Column(DateTime, nullable=True)  # When price was last fetched from API
    
    def __repr__(self):
        return f"<StockInfo(symbol='{self.symbol}', name='{self.name}', exchange='{self.exchange}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'short_name': self.short_name,
            'exchange': self.exchange,
            'sector': self.sector,
            'industry': self.industry,
            'market_cap': self.market_cap,
            'currency': self.currency,
            'country': self.country,
            'type': self.stock_type,
            'avg_volume': self.avg_volume,
            'shares_outstanding': self.shares_outstanding,
            'is_active': self.is_active,
            'is_popular': self.is_popular,
            'popularity_rank': self.popularity_rank
        }


# StockPrice 클래스 제거 - 실시간 가격은 API로만 가져옴