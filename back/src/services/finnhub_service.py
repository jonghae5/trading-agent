"""Finnhub API service for financial news and sentiment analysis."""

import asyncio
import hashlib
import logging
import sys
import threading
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta, timezone
from pathlib import Path
import aiohttp
from dataclasses import dataclass
from cachetools import TTLCache

# Add project root to path for trading system imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class NewsArticle:
    """News article information."""
    id: Optional[str]
    title: str
    description: str
    published_at: datetime
    source: str
    url: str
    image: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[float] = None


@dataclass
class SentimentData:
    """Sentiment analysis data."""
    symbol: str
    mention: int
    positive_mention: int
    negative_mention: int
    positive_score: float
    negative_score: float
    compound_score: float


class FinnhubAPIError(Exception):
    """Finnhub API specific error."""
    pass


class FinnhubService:
    """Service for fetching financial news and sentiment from Finnhub API."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self):
        self.api_key = settings.FINNHUB_API_KEY if hasattr(settings, 'FINNHUB_API_KEY') else None
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not set. News and sentiment data will not be available.")
        
        # TTL 캐시 설정 (10분 TTL, 최대 200개 항목)
        self._cache_lock = threading.RLock()
        self._cache = TTLCache(maxsize=200, ttl=600)  # 10분 = 600초
        logger.info("Finnhub service initialized with 10-minute TTL cache (max 200 items)")
    
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters."""
        cache_params = {k: v for k, v in params.items() if k != "token"}
        param_str = "&".join(f"{k}={v}" for k, v in sorted(cache_params.items()))
        key_str = f"{endpoint}:{param_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make cached async HTTP request to Finnhub API."""
        if not self.api_key:
            raise FinnhubAPIError("Finnhub API key not configured")
        
        # 캐시 키 생성
        cache_key = self._generate_cache_key(endpoint, params)
        
        # 캐시에서 확인
        with self._cache_lock:
            cached_result = self._cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {endpoint}")
                return cached_result
        
        # 캐시 미스 - API 호출
        logger.debug(f"Cache MISS for {endpoint} - calling Finnhub API")
        
        params.update({"token": self.api_key})
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 성공 시 캐시에 저장
                        with self._cache_lock:
                            self._cache[cache_key] = data
                        
                        return data
                    elif response.status == 429:
                        raise FinnhubAPIError("API rate limit exceeded")
                    else:
                        text = await response.text()
                        raise FinnhubAPIError(f"HTTP {response.status}: {text}")
        except aiohttp.ClientError as e:
            raise FinnhubAPIError(f"Network error: {str(e)}")
    
    async def get_market_news(self, category: str = "general", limit: int = 20) -> List[NewsArticle]:
        """Get market news from Finnhub."""
        try:
            params = {"category": category}
            data = await self._make_request("news", params)
            
            articles = []
            for item in data[:limit]:
                article = NewsArticle(
                    id=str(item.get("id", "")),
                    title=item.get("headline", ""),
                    description=item.get("summary", ""),
                    published_at=datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc),
                    source=item.get("source", "Finnhub"),
                    url=item.get("url", ""),
                    image=item.get("image", ""),
                    category=category
                )
                articles.append(article)
            
            return articles
        except Exception as e:
            logger.error(f"Error fetching market news: {e}")
            return self._get_sample_news(limit)
    
    async def get_company_news(self, symbol: str, from_date: Optional[datetime] = None, 
                             to_date: Optional[datetime] = None, limit: int = 20) -> List[NewsArticle]:
        """Get company-specific news from Finnhub."""
        try:
            # Default to last 30 days if no dates provided
            if not from_date:
                from_date = datetime.now() - timedelta(days=30)
            if not to_date:
                to_date = datetime.now()
            
            params = {
                "symbol": symbol.upper(),
                "from": from_date.strftime("%Y-%m-%d"),
                "to": to_date.strftime("%Y-%m-%d")
            }
            
            data = await self._make_request("company-news", params)
            
            articles = []
            for item in data:
                article = NewsArticle(
                    id=str(item.get("id", "")),
                    title=item.get("headline", ""),
                    description=item.get("summary", ""),
                    published_at=datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc),
                    source=item.get("source", "Finnhub"),
                    url=item.get("url", ""),
                    image=item.get("image", ""),
                    category=f"company_{symbol.lower()}"
                )
                articles.append(article)
            
            # published_at 기준으로 내림차순 정렬 후 limit 적용
            articles_sorted = sorted(articles, key=lambda x: x.published_at, reverse=True)[:limit]
            return articles_sorted
        except Exception as e:
            logger.error(f"Error fetching company news for {symbol}: {e}")
            return self._get_sample_company_news(symbol, limit)
    
    async def get_news_sentiment(self, symbol: str) -> Optional[SentimentData]:
        """Get news sentiment data for a symbol from Finnhub."""
        try:
            params = {"symbol": symbol.upper()}
            data = await self._make_request("news-sentiment", params)
            
            if data and "buzz" in data and "sentiment" in data:
                buzz = data["buzz"]
                sentiment = data["sentiment"]
                
                return SentimentData(
                    symbol=symbol.upper(),
                    mention=buzz.get("articlesInLastWeek", 0),
                    positive_mention=buzz.get("buzz", 0),
                    negative_mention=buzz.get("weeklyAverage", 0),
                    positive_score=sentiment.get("bullishPercent", 0.0),
                    negative_score=sentiment.get("bearishPercent", 0.0),
                    compound_score=sentiment.get("bullishPercent", 0.0) - sentiment.get("bearishPercent", 0.0)
                )
            
            return None
        except Exception as e:
            logger.error(f"Error fetching sentiment for {symbol}: {e}")
            return self._get_sample_sentiment(symbol)
    
    
    async def get_economic_news(self, limit: int = 20) -> List[NewsArticle]:
        """Get economic news (general market news)."""
        return await self.get_market_news("general", limit)
    
    async def get_crypto_news(self, limit: int = 20) -> List[NewsArticle]:
        """Get cryptocurrency news."""
        return await self.get_market_news("crypto", limit)
    
    async def get_forex_news(self, limit: int = 20) -> List[NewsArticle]:
        """Get forex news."""
        return await self.get_market_news("forex", limit)
    
    async def get_merger_news(self, limit: int = 20) -> List[NewsArticle]:
        """Get merger and acquisition news."""
        return await self.get_market_news("merger", limit)
    
 
    def _get_sample_news(self, limit: int = 20) -> List[NewsArticle]:
        """Get sample news when API is unavailable."""
        sample_news = [
            NewsArticle(
                id="1",
                title="Markets Rally on Fed Policy Outlook",
                description="Stock markets surge as Federal Reserve signals potential rate cuts ahead.",
                published_at=datetime.now() - timedelta(hours=1),
                source="Market News",
                url="https://example.com/news1",
                category="general"
            ),
            NewsArticle(
                id="2", 
                title="Tech Stocks Lead Market Gains",
                description="Technology sector outperforms as investors bet on AI growth prospects.",
                published_at=datetime.now() - timedelta(hours=3),
                source="Tech Daily",
                url="https://example.com/news2",
                category="general"
            ),
            NewsArticle(
                id="3",
                title="Oil Prices Stabilize After Recent Volatility",
                description="Crude oil markets find support amid supply concerns and demand outlook.",
                published_at=datetime.now() - timedelta(hours=5),
                source="Energy Report",
                url="https://example.com/news3",
                category="general"
            )
        ]
        return sample_news[:limit]
    
    def _get_sample_company_news(self, symbol: str, limit: int = 20) -> List[NewsArticle]:
        """Get sample company news when API is unavailable."""
        sample_news = [
            NewsArticle(
                id=f"{symbol}_1",
                title=f"{symbol} Reports Strong Quarterly Earnings",
                description=f"{symbol} exceeds analyst expectations with robust revenue growth.",
                published_at=datetime.now() - timedelta(hours=2),
                source="Financial Times",
                url="https://example.com/news1",
                category=f"company_{symbol.lower()}"
            ),
            NewsArticle(
                id=f"{symbol}_2",
                title=f"{symbol} Announces Strategic Partnership",
                description=f"{symbol} enters into major alliance to expand market presence.",
                published_at=datetime.now() - timedelta(hours=6),
                source="Business Wire",
                url="https://example.com/news2",
                category=f"company_{symbol.lower()}"
            )
        ]
        return sample_news[:limit]
    
    def _get_sample_sentiment(self, symbol: str) -> SentimentData:
        """Get sample sentiment when API is unavailable."""
        return SentimentData(
            symbol=symbol.upper(),
            mention=45,
            positive_mention=28,
            negative_mention=17,
            positive_score=0.62,
            negative_score=0.38,
            compound_score=0.24
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        with self._cache_lock:
            cache_info = {
                "current_size": len(self._cache),
                "max_size": self._cache.maxsize,
                "ttl_seconds": self._cache.ttl
            }
        return cache_info
    
    def clear_cache(self):
        """Clear all cached data."""
        with self._cache_lock:
            self._cache.clear()
            logger.info("Finnhub cache cleared")


# Global Finnhub service instance
finnhub_service = FinnhubService()


def get_finnhub_service() -> FinnhubService:
    """Get the global Finnhub service instance."""
    return finnhub_service