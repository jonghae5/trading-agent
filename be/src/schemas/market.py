"""Market data related Pydantic src.schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


class MarketDataResponse(BaseModel):
    """Market data response schema."""
    ticker: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    timestamp: datetime
    source: str = "yahoo_finance"
    
    model_config = ConfigDict(from_attributes=True)


class EconomicIndicatorResponse(BaseModel):
    """Economic indicator response schema."""
    name: str
    value: float
    change: Optional[float] = None
    change_percent: Optional[float] = None
    date: datetime
    source: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class MarketIndicesResponse(BaseModel):
    """Market indices response schema."""
    indices: List[MarketDataResponse]
    timestamp: datetime
    source: str = "multiple"


class MarketSummaryResponse(BaseModel):
    """Market summary response schema."""
    market_status: str  # "open", "closed", "pre_market", "after_hours"
    market_date: datetime
    major_indices: List[MarketDataResponse]
    top_gainers: List[MarketDataResponse]
    top_losers: List[MarketDataResponse]
    most_active: List[MarketDataResponse]
    timestamp: datetime


class StockQuoteResponse(BaseModel):
    """Stock quote response schema."""
    ticker: str
    company_name: Optional[str] = None
    price: float
    change: float
    change_percent: float
    
    # Volume data
    volume: int
    avg_volume: Optional[int] = None
    
    # Price ranges
    day_low: Optional[float] = None
    day_high: Optional[float] = None
    week_52_low: Optional[float] = None
    week_52_high: Optional[float] = None
    
    # Market metrics
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    
    # Trading session
    previous_close: Optional[float] = None
    open_price: Optional[float] = None
    
    timestamp: datetime
    source: str = "yahoo_finance"


class TechnicalIndicatorsResponse(BaseModel):
    """Technical indicators response schema."""
    ticker: str
    indicators: Dict[str, Any]  # RSI, MACD, Moving Averages, etc.
    timeframe: str  # "1d", "1h", etc.
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MarketSectorResponse(BaseModel):
    """Market sector performance response schema."""
    sector_name: str
    performance: float  # percentage change
    top_stocks: List[MarketDataResponse]
    timestamp: datetime


class CryptocurrencyResponse(BaseModel):
    """Cryptocurrency data response schema."""
    symbol: str
    name: str
    price_usd: float
    change_24h: float
    change_percent_24h: float
    market_cap_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    timestamp: datetime
    source: str = "coinbase"


class ForexResponse(BaseModel):
    """Forex currency pair response schema."""
    base_currency: str
    quote_currency: str
    exchange_rate: float
    change: float
    change_percent: float
    timestamp: datetime
    source: str = "forex_api"


class NewsArticleResponse(BaseModel):
    """Financial news article response schema."""
    title: str
    summary: Optional[str] = None
    url: str
    source: str
    published_at: datetime
    sentiment: Optional[str] = None  # "positive", "negative", "neutral"
    relevance_score: Optional[float] = None
    related_tickers: List[str] = []


class MarketNewsResponse(BaseModel):
    """Market news response schema."""
    articles: List[NewsArticleResponse]
    total: int
    page: int = 1
    per_page: int = 20
    timestamp: datetime


class WatchlistResponse(BaseModel):
    """User watchlist response schema."""
    id: int
    name: str
    tickers: List[str]
    quotes: Optional[List[StockQuoteResponse]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class MarketAlertResponse(BaseModel):
    """Market alert response schema."""
    id: int
    ticker: str
    alert_type: str  # "price_above", "price_below", "volume_spike", etc.
    trigger_value: float
    current_value: float
    triggered_at: datetime
    message: str
    
    model_config = ConfigDict(from_attributes=True)


# Fear & Greed Index src.schemas

class FearGreedClassification(str, Enum):
    """Fear & Greed Index classification levels."""
    EXTREME_FEAR = "Extreme Fear"
    FEAR = "Fear"
    NEUTRAL = "Neutral"
    GREED = "Greed"
    EXTREME_GREED = "Extreme Greed"


class FearGreedIndexResponse(BaseModel):
    """Current Fear & Greed Index response schema."""
    value: int = Field(..., ge=0, le=100, description="Fear & Greed Index value (0-100)")
    classification: FearGreedClassification = Field(..., description="Classification level")
    timestamp: datetime = Field(..., description="Data timestamp")
    
    # Historical comparison values
    previous_close: Optional[int] = Field(None, ge=0, le=100, description="Previous close value")
    one_week_ago: Optional[int] = Field(None, ge=0, le=100, description="Value one week ago")
    one_month_ago: Optional[int] = Field(None, ge=0, le=100, description="Value one month ago")
    one_year_ago: Optional[int] = Field(None, ge=0, le=100, description="Value one year ago")
    
    class Config:
        use_enum_values = True


class FearGreedHistoricalPoint(BaseModel):
    """Single historical Fear & Greed Index data point."""
    date: datetime = Field(..., description="Date of the data point")
    value: int = Field(..., ge=0, le=100, description="Fear & Greed Index value")
    classification: FearGreedClassification = Field(..., description="Classification level")
    
    class Config:
        use_enum_values = True


class FearGreedHistoricalResponse(BaseModel):
    """Historical Fear & Greed Index response schema."""
    data: List[FearGreedHistoricalPoint] = Field(..., description="Historical data points")
    period_days: int = Field(..., ge=1, description="Number of days of historical data")
    start_date: datetime = Field(..., description="Start date of the data")
    end_date: datetime = Field(..., description="End date of the data")
    
    class Config:
        use_enum_values = True


class MarketSentimentTrend(str, Enum):
    """Market sentiment trend direction."""
    IMPROVING = "improving"
    DECLINING = "declining"
    NEUTRAL = "neutral"


class MarketSentimentVolatility(str, Enum):
    """Market sentiment volatility level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarketSentimentSummaryResponse(BaseModel):
    """Comprehensive market sentiment summary response schema."""
    current: FearGreedIndexResponse = Field(..., description="Current Fear & Greed Index data")
    trend: MarketSentimentTrend = Field(..., description="Recent trend direction")
    volatility: MarketSentimentVolatility = Field(..., description="Sentiment volatility level")
    
    historical_comparison: Dict[str, Optional[int]] = Field(
        ..., 
        description="Historical comparison values"
    )
    
    recent_history: List[FearGreedHistoricalPoint] = Field(
        ..., 
        description="Recent 7-day history"
    )
    
    # Sentiment indicators breakdown
    sentiment_components: Optional[Dict[str, Any]] = Field(
        None,
        description="Breakdown of sentiment components (if available)"
    )
    
    # Market context
    market_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional market context and indicators"
    )
    
    class Config:
        use_enum_values = True


class SentimentAnalysisResponse(BaseModel):
    """Advanced sentiment analysis response schema."""
    fear_greed_index: FearGreedIndexResponse = Field(..., description="Current Fear & Greed Index")
    
    # Additional sentiment metrics
    social_sentiment: Optional[Dict[str, Any]] = Field(None, description="Social media sentiment")
    news_sentiment: Optional[Dict[str, Any]] = Field(None, description="News sentiment analysis")
    options_sentiment: Optional[Dict[str, Any]] = Field(None, description="Options market sentiment")
    
    # Combined sentiment score
    combined_sentiment_score: Optional[float] = Field(
        None, 
        ge=-1.0, 
        le=1.0, 
        description="Combined sentiment score (-1 to 1)"
    )
    
    confidence_level: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence in the sentiment analysis"
    )
    
    timestamp: datetime = Field(..., description="Analysis timestamp")
    
    class Config:
        use_enum_values = True