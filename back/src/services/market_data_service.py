"""Market data service for fetching financial data."""

import asyncio
import logging
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
from dataclasses import dataclass
from src.models.base import get_kst_now
# Add project root to path for trading system imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings
from src.services.mock_data_service import mock_data_service
from src.schemas.market import (
    StockQuoteResponse,
    MarketIndicesResponse,
    MarketSummaryResponse,
    TechnicalIndicatorsResponse,
    MarketNewsResponse,
    NewsArticleResponse,
    EconomicIndicatorResponse,
    MarketDataResponse
)


# Import FRED service
from .fred_service import get_fred_service, FredService

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class MarketDataCache:
    """Simple in-memory cache for market data."""
    data: Any
    timestamp: datetime
    ttl_seconds: int = 300  # 5 minutes default
    
    def is_expired(self) -> bool:
        return get_kst_now() > self.timestamp + timedelta(seconds=self.ttl_seconds)


class MarketDataService:
    """Service for fetching market data from various sources."""
    
    def __init__(self):
        self.cache: Dict[str, MarketDataCache] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.fred_service = get_fred_service()
        
        # API configuration
        self.yahoo_finance_base = "https://query1.finance.yahoo.com/v8/finance/chart"
        self.finnhub_base = "https://finnhub.io/api/v1"
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if not expired."""
        if key in self.cache:
            cache_entry = self.cache[key]
            if not cache_entry.is_expired():
                return cache_entry.data
            else:
                del self.cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any, ttl_seconds: int = 300):
        """Set cache data with TTL."""
        self.cache[key] = MarketDataCache(
            data=data,
            timestamp=get_kst_now(),
            ttl_seconds=ttl_seconds
        )
    
    async def get_stock_quote(self, ticker: str) -> Optional[StockQuoteResponse]:
        """Get stock quote from Yahoo Finance with real-time data."""
        cache_key = f"quote_{ticker}"
        
        # Check cache first (shorter TTL for real-time feel)
        cached_data = self._get_cached(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Always try to get real data first, fallback to mock if needed
            # if settings.MOCK_EXTERNAL_APIS:
            #     # Return realistic mock data for development
            #     quote = self._get_mock_quote(ticker)
            #     self._set_cache(cache_key, quote, 30)  # Cache for 30 seconds in dev for real-time feel
            #     return quote
            
            session = await self._get_session()
            # Use Yahoo Finance real-time quote endpoint
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            params = {
                "interval": "1m",
                "range": "1d",
                "includePrePost": "true",
                "events": "div|split"
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    quote = self._parse_yahoo_quote(ticker, data)
                    
                    if quote:
                        # Cache real-time data for 15 seconds
                        self._set_cache(cache_key, quote, 15)
                    
                    return quote
                else:
                    logger.warning(f"Failed to get quote for {ticker}: {response.status}")
                    # Fallback to mock data if API fails
                    quote = self._get_mock_quote(ticker)
                    self._set_cache(cache_key, quote, 60)
                    return quote
                    
        except Exception as e:
            logger.error(f"Error getting stock quote for {ticker}: {e}")
            # Fallback to mock data on error
            quote = self._get_mock_quote(ticker)
            if quote:
                self._set_cache(cache_key, quote, 60)
            return quote
    
    async def get_multiple_quotes(self, tickers: List[str]) -> List[StockQuoteResponse]:
        """Get quotes for multiple tickers."""
        tasks = [self.get_stock_quote(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        quotes = []
        for i, result in enumerate(results):
            if isinstance(result, StockQuoteResponse):
                quotes.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error getting quote for {tickers[i]}: {result}")
        
        return quotes
    
    async def get_market_indices(self) -> MarketIndicesResponse:
        """Get major market indices."""
        cache_key = "market_indices"
        
        cached_data = self._get_cached(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Major indices tickers
            index_tickers = ["^GSPC", "^DJI", "^IXIC", "^RUT"]  # S&P 500, Dow, Nasdaq, Russell 2000
            
            quotes = await self.get_multiple_quotes(index_tickers)
            
            # Convert to MarketDataResponse
            indices_data = []
            for quote in quotes:
                market_data = MarketDataResponse(
                    ticker=quote.ticker,
                    price=quote.price,
                    change=quote.change,
                    change_percent=quote.change_percent,
                    volume=quote.volume,
                    market_cap=quote.market_cap,
                    pe_ratio=quote.pe_ratio,
                    timestamp=quote.timestamp,
                    source=quote.source
                )
                indices_data.append(market_data)
            
            indices = MarketIndicesResponse(
                indices=indices_data,
                timestamp=get_kst_now(),
                source="yahoo_finance"
            )
            
            self._set_cache(cache_key, indices, 300)  # Cache for 5 minutes
            return indices
            
        except Exception as e:
            logger.error(f"Error getting market indices: {e}")
            # Return empty response on error
            return MarketIndicesResponse(
                indices=[],
                timestamp=get_kst_now(),
                source="error"
            )
    
    async def get_market_summary(self) -> MarketSummaryResponse:
        """Get market summary with indices and top movers."""
        try:
            # Get major indices
            indices = await self.get_market_indices()
            
            # For now, return basic summary with indices
            # In production, you'd fetch actual top gainers/losers
            summary = MarketSummaryResponse(
                market_status="closed",  # Would check actual market hours
                market_date=get_kst_now(),
                major_indices=indices.indices,
                top_gainers=[],  # Would fetch actual data
                top_losers=[],
                most_active=[],
                timestamp=get_kst_now()
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return MarketSummaryResponse(
                market_status="unknown",
                market_date=get_kst_now(),
                major_indices=[],
                top_gainers=[],
                top_losers=[],
                most_active=[],
                timestamp=get_kst_now()
            )
    
    async def get_technical_indicators(
        self,
        ticker: str,
        timeframe: str = "1d"
    ) -> Optional[TechnicalIndicatorsResponse]:
        """Get technical indicators for a ticker."""
        cache_key = f"indicators_{ticker}_{timeframe}"
        
        cached_data = self._get_cached(cache_key)
        if cached_data:
            return cached_data
        
        try:
            if settings.MOCK_EXTERNAL_APIS:
                # Return mock technical indicators
                indicators = TechnicalIndicatorsResponse(
                    ticker=ticker,
                    indicators={
                        "RSI": 65.4,
                        "MACD": {
                            "macd": 2.1,
                            "signal": 1.8,
                            "histogram": 0.3
                        },
                        "SMA_20": 150.2,
                        "SMA_50": 148.7,
                        "EMA_12": 151.1,
                        "Bollinger_Bands": {
                            "upper": 155.0,
                            "middle": 150.0,
                            "lower": 145.0
                        },
                        "Volume_SMA": 1500000
                    },
                    timeframe=timeframe,
                    timestamp=get_kst_now()
                )
                
                self._set_cache(cache_key, indicators, 300)
                return indicators
            
            # In production, you'd calculate indicators from historical data
            # or use a service like Alpha Vantage, Finnhub, etc.
            logger.info(f"Technical indicators not implemented for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting technical indicators: {e}")
            return None
    
    async def get_market_news(
        self,
        ticker: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20
    ) -> MarketNewsResponse:
        """Get financial news."""
        try:
            if settings.MOCK_EXTERNAL_APIS:
                # Return mock news data
                articles = []
                for i in range(min(limit, 5)):
                    article = NewsArticleResponse(
                        title=f"Market Update {i+1}: {ticker or 'General'} News",
                        summary=f"Summary of market news article {i+1}",
                        url=f"https://example.com/news/{i+1}",
                        source="Mock News",
                        published_at=get_kst_now() - timedelta(hours=i),
                        sentiment="neutral",
                        relevance_score=0.8,
                        related_tickers=[ticker] if ticker else []
                    )
                    articles.append(article)
                
                return MarketNewsResponse(
                    articles=articles,
                    total=len(articles),
                    page=1,
                    per_page=limit,
                    timestamp=get_kst_now()
                )
            
            # In production, integrate with news APIs like NewsAPI, Finnhub, etc.
            return MarketNewsResponse(
                articles=[],
                total=0,
                page=1,
                per_page=limit,
                timestamp=get_kst_now()
            )
            
        except Exception as e:
            logger.error(f"Error getting market news: {e}")
            return MarketNewsResponse(
                articles=[],
                total=0,
                page=1,
                per_page=limit,
                timestamp=get_kst_now()
            )
    
    async def get_economic_indicators(
        self,
        country: str = "US",
        category: Optional[str] = None
    ) -> List[EconomicIndicatorResponse]:
        """Get economic indicators."""
        try:
            if settings.MOCK_EXTERNAL_APIS:
                # Return mock economic data
                indicators = [
                    EconomicIndicatorResponse(
                        name="GDP Growth Rate",
                        value=2.1,
                        change=0.1,
                        change_percent=4.8,
                        date=get_kst_now() - timedelta(days=30),
                        source="Mock Data",
                        description="Quarterly GDP growth rate"
                    ),
                    EconomicIndicatorResponse(
                        name="Unemployment Rate",
                        value=3.7,
                        change=-0.1,
                        change_percent=-2.6,
                        date=get_kst_now() - timedelta(days=7),
                        source="Mock Data",
                        description="National unemployment rate"
                    ),
                    EconomicIndicatorResponse(
                        name="Inflation Rate (CPI)",
                        value=3.2,
                        change=0.2,
                        change_percent=6.7,
                        date=get_kst_now() - timedelta(days=14),
                        source="Mock Data",
                        description="Consumer Price Index inflation rate"
                    )
                ]
                
                return indicators
            
            # In production, integrate with economic data APIs
            return []
            
        except Exception as e:
            logger.error(f"Error getting economic indicators: {e}")
            return []
    
    async def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks by name or ticker with comprehensive results."""
        try:
            query = query.upper().strip()
            
            # Use centralized mock data service
            results = mock_data_service.search_stocks(query, limit)
            
            # If no exact matches, return most popular stocks
            if not results and len(query) <= 2:
                results = stock_database[:limit]
            
            return results[:limit]
        
        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            return []
    
    async def get_sector_performance(self) -> List[Dict[str, Any]]:
        """Get comprehensive sector performance data."""
        cache_key = "sector_performance"
        
        cached_data = self._get_cached(cache_key)
        if cached_data:
            return cached_data
        
        try:
            if settings.MOCK_EXTERNAL_APIS:
                import random
                import time
                
                # Simulate realistic sector performance with time-based variation
                time_seed = int(time.time() / 300)  # Changes every 5 minutes
                random.seed(time_seed)
                
                sectors = [
                    {"sector": "Technology", "ticker": "XLK", "base_performance": 1.5},
                    {"sector": "Healthcare", "ticker": "XLV", "base_performance": 0.8},
                    {"sector": "Financial Services", "ticker": "XLF", "base_performance": 0.2},
                    {"sector": "Energy", "ticker": "XLE", "base_performance": -0.5},
                    {"sector": "Consumer Discretionary", "ticker": "XLY", "base_performance": 0.9},
                    {"sector": "Consumer Staples", "ticker": "XLP", "base_performance": 0.3},
                    {"sector": "Industrials", "ticker": "XLI", "base_performance": 0.7},
                    {"sector": "Materials", "ticker": "XLB", "base_performance": -0.2},
                    {"sector": "Utilities", "ticker": "XLU", "base_performance": -0.8},
                    {"sector": "Real Estate", "ticker": "XLRE", "base_performance": -1.0},
                    {"sector": "Communication Services", "ticker": "XLC", "base_performance": 1.2}
                ]
                
                result = []
                for sector_data in sectors:
                    # Add realistic variation to base performance
                    variation = random.uniform(-1.5, 1.5)
                    performance = sector_data["base_performance"] + variation
                    
                    result.append({
                        "sector": sector_data["sector"],
                        "ticker": sector_data["ticker"],
                        "performance": round(performance, 2),
                        "volume": random.randint(1000000, 10000000),
                        "market_cap": f"{random.randint(50, 500)}B",
                        "pe_ratio": round(random.uniform(15, 30), 1),
                        "dividend_yield": round(random.uniform(1, 4), 2)
                    })
                
                # Sort by performance (best to worst)
                result.sort(key=lambda x: x["performance"], reverse=True)
                
                self._set_cache(cache_key, result, 300)  # Cache for 5 minutes
                return result
            
            # In production, fetch real sector performance data
            return []
            
        except Exception as e:
            logger.error(f"Error getting sector performance: {e}")
            return []
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get market status and trading hours."""
        try:
            # This would check actual market hours and status
            now = get_kst_now()
            
            return {
                "market_open": False,  # Would check actual market hours
                "next_open": "2025-01-22T09:30:00",
                "next_close": "2025-01-22T16:00:00",
                "timezone": "US/Eastern",
                "current_time": now.isoformat(),
                "trading_day": True
            }
            
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {}
    
    def _parse_yahoo_quote(self, ticker: str, data: Dict[str, Any]) -> Optional[StockQuoteResponse]:
        """Parse Yahoo Finance API response."""
        try:
            if "chart" not in data or not data["chart"]["result"]:
                return None
            
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            
            # Extract price data
            current_price = meta.get("regularMarketPrice", 0.0)
            previous_close = meta.get("previousClose", current_price)
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0
            
            return StockQuoteResponse(
                ticker=ticker,
                company_name=meta.get("shortName", ticker),
                price=current_price,
                change=change,
                change_percent=change_percent,
                volume=meta.get("regularMarketVolume", 0),
                day_low=meta.get("regularMarketDayLow"),
                day_high=meta.get("regularMarketDayHigh"),
                week_52_low=meta.get("fiftyTwoWeekLow"),
                week_52_high=meta.get("fiftyTwoWeekHigh"),
                previous_close=previous_close,
                timestamp=get_kst_now()
            )
            
        except Exception as e:
            logger.error(f"Error parsing Yahoo Finance data: {e}")
            return None
    
    def _get_mock_quote(self, ticker: str) -> StockQuoteResponse:
        """Generate realistic mock quote data with real-time simulation."""
        import random
        import time
        
        # Create realistic base prices for common tickers
        ticker_prices = {
            'AAPL': 180.0, 'GOOGL': 140.0, 'MSFT': 420.0, 'TSLA': 250.0,
            'NVDA': 880.0, 'AMZN': 170.0, 'META': 500.0, 'NFLX': 600.0,
            'SPY': 500.0, 'QQQ': 420.0, 'IWM': 220.0, 'VTI': 260.0
        }
        
        ticker_names = {
            'AAPL': 'Apple Inc.', 'GOOGL': 'Alphabet Inc.', 'MSFT': 'Microsoft Corporation',
            'TSLA': 'Tesla, Inc.', 'NVDA': 'NVIDIA Corporation', 'AMZN': 'Amazon.com Inc.',
            'META': 'Meta Platforms Inc.', 'NFLX': 'Netflix Inc.',
            'SPY': 'SPDR S&P 500 ETF', 'QQQ': 'Invesco QQQ ETF', 'IWM': 'iShares Russell 2000 ETF',
            'VTI': 'Vanguard Total Stock Market ETF'
        }
        
        base_price = ticker_prices.get(ticker, 100.0 + hash(ticker) % 200)
        
        # Simulate real-time price movement with small fluctuations
        time_seed = int(time.time() / 30)  # Changes every 30 seconds
        random.seed(hash(f"{ticker}_{time_seed}"))
        
        # More realistic price movements
        change_percent = random.uniform(-3.0, 3.0)
        change = base_price * (change_percent / 100)
        current_price = base_price + change
        
        # Realistic volume based on ticker
        volume_multiplier = {
            'AAPL': 5, 'GOOGL': 2, 'MSFT': 4, 'TSLA': 8, 'SPY': 10
        }.get(ticker, 1)
        
        volume = random.randint(500000, 2000000) * volume_multiplier
        
        return StockQuoteResponse(
            ticker=ticker,
            company_name=ticker_names.get(ticker, f"{ticker} Corporation"),
            price=round(current_price, 2),
            change=round(change, 2),
            change_percent=round(change_percent, 2),
            volume=volume,
            day_low=round(current_price - random.uniform(0.5, 2.0), 2),
            day_high=round(current_price + random.uniform(0.5, 2.0), 2),
            week_52_low=round(current_price - random.uniform(10, 30), 2),
            week_52_high=round(current_price + random.uniform(10, 30), 2),
            previous_close=round(base_price, 2),
            timestamp=get_kst_now(),
            source="mock_data_realtime",
            market_cap=random.randint(10, 3000) * 1000000000,  # Market cap in billions
            pe_ratio=round(random.uniform(15, 35), 1) if random.random() > 0.2 else None
        )
    
    async def get_economic_indicators(self) -> Dict[str, Any]:
        """Get key economic indicators from FRED."""
        cache_key = "economic_indicators"
        
        # Check cache first
        cached_data = self._get_cached(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Get economic summary from FRED
            economic_data = await self.fred_service.get_economic_summary()
            
            # Cache for 1 hour (economic data doesn't change frequently)
            self._set_cache(cache_key, economic_data, 3600)
            
            return economic_data
        except Exception as e:
            logger.error(f"Error fetching economic indicators: {e}")
            return {}
    
    async def get_market_context(self) -> Dict[str, Any]:
        """Get comprehensive market context including economic indicators."""
        try:
            # Get parallel data
            tasks = {
                'economic_summary': self.fred_service.get_economic_summary(),
                'gdp_data': self.fred_service.get_gdp_data(),
                'employment_data': self.fred_service.get_employment_data(),
                'inflation_data': self.fred_service.get_inflation_data(),
                'rates_data': self.fred_service.get_interest_rates_data()
            }
            
            results = {}
            for key, task in tasks.items():
                try:
                    results[key] = await task
                except Exception as e:
                    logger.error(f"Error fetching {key}: {e}")
                    results[key] = {}
            
            return {
                'timestamp': get_kst_now().isoformat(),
                'economic_indicators': results['economic_summary'],
                'gdp': results['gdp_data'],
                'employment': results['employment_data'],
                'inflation': results['inflation_data'],
                'interest_rates': results['rates_data']
            }
        except Exception as e:
            logger.error(f"Error getting market context: {e}")
            return {'error': str(e)}


# Global market data service instance
market_data_service = MarketDataService()


def get_market_data_service() -> MarketDataService:
    """Get the global market data service instance."""
    return market_data_service