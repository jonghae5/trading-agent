"""Stock search service for ticker autocomplete functionality."""

import logging
import asyncio
import yfinance as yf
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re
from src.models.base import get_kst_now
from src.services.mock_data_service import mock_data_service


logger = logging.getLogger(__name__)


@dataclass
class StockSearchResult:
    """Stock search result data."""
    symbol: str
    name: str
    exchange: str
    type: str  # 'stock', 'etf', 'index', etc.
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    currency: Optional[str] = None


class StockSearchService:
    """Service for searching and finding stock tickers."""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 86400  # 24 hours for stock search cache
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for search query."""
        return f"stock_search_{query.lower().strip()}"
    
    def _is_cache_valid(self, cache_time: datetime) -> bool:
        """Check if cache is still valid."""
        return get_kst_now() - cache_time < timedelta(seconds=self.cache_duration)
    
    def _fuzzy_match_score(self, query: str, text: str) -> float:
        """Calculate fuzzy match score between query and text."""
        query = query.lower().strip()
        text = text.lower()
        
        # Exact match gets highest score
        if query == text:
            return 1.0
        
        # Check if query is at the beginning of text
        if text.startswith(query):
            return 0.9
        
        # Check if all characters of query appear in text in order
        query_chars = list(query)
        text_chars = list(text)
        
        i = 0  # query index
        j = 0  # text index
        matches = 0
        
        while i < len(query_chars) and j < len(text_chars):
            if query_chars[i] == text_chars[j]:
                matches += 1
                i += 1
            j += 1
        
        if matches == len(query_chars):
            # All characters found, calculate score based on density
            return matches / len(text) * 0.8
        else:
            # Not all characters found
            return matches / len(query_chars) * 0.3
    
    async def search_stocks_local(self, query: str, limit: int = 10) -> List[StockSearchResult]:
        """Search stocks using centralized mock data service."""
        if not query or len(query.strip()) < 1:
            # Return popular stocks if no query
            popular_stocks = mock_data_service.get_popular_stocks(limit)
            results = []
            
            for stock_data in popular_stocks:
                results.append(StockSearchResult(
                    symbol=stock_data['ticker'],
                    name=stock_data['name'],
                    exchange=stock_data['exchange'],
                    type=stock_data['type'],
                    sector=stock_data['sector'],
                    industry=None,
                    market_cap=None,
                    currency='USD'
                ))
            return results
        
        # Use centralized search function
        search_results = mock_data_service.search_stocks(query, limit)
        results = []
        
        for stock_data in search_results:
            results.append(StockSearchResult(
                symbol=stock_data['ticker'],
                name=stock_data['name'],
                exchange=stock_data['exchange'],
                type=stock_data['type'],
                sector=stock_data['sector'],
                industry=None,
                market_cap=None,
                currency='USD'
            ))
        
        return results
    
    async def validate_ticker(self, ticker: str) -> bool:
        """Validate if a ticker exists and is tradeable."""
        try:
            ticker = ticker.upper().strip()
            
            # First check centralized mock data service
            if mock_data_service.get_stock_by_ticker(ticker):
                return True
            
            # If not in local database, try yfinance
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if we got valid data
            if info and 'symbol' in info and info.get('regularMarketPrice'):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return False
    
    async def get_stock_info(self, ticker: str) -> Optional[StockSearchResult]:
        """Get detailed information for a specific ticker."""
        try:
            ticker = ticker.upper().strip()
            
            # Check local database first
            if ticker in self.all_stocks:
                data = self.all_stocks[ticker]
                return StockSearchResult(
                    symbol=ticker,
                    name=data['name'],
                    exchange=data['exchange'],
                    type='etf' if data['sector'] == 'ETF' else 'stock',
                    sector=data['sector'],
                    industry=None,
                    market_cap=None,
                    currency='USD'
                )
            
            # If not in local database, try yfinance
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if info and 'symbol' in info:
                return StockSearchResult(
                    symbol=ticker,
                    name=info.get('longName', info.get('shortName', ticker)),
                    exchange=info.get('exchange', 'Unknown'),
                    type=info.get('quoteType', 'stock').lower(),
                    sector=info.get('sector'),
                    industry=info.get('industry'),
                    market_cap=info.get('marketCap'),
                    currency=info.get('currency', 'USD')
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting stock info for {ticker}: {e}")
            return None
    
    async def search_stocks(self, query: str, limit: int = 10) -> List[StockSearchResult]:
        """Main search function with caching."""
        cache_key = self._get_cache_key(query)
        
        # Check cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry['timestamp']):
                return cache_entry['results']
        
        try:
            # Search using local database
            results = await self.search_stocks_local(query, limit)
            
            # Cache results
            self.cache[cache_key] = {
                'results': results,
                'timestamp': get_kst_now()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching stocks for query '{query}': {e}")
            return []
    
    async def get_popular_stocks(self, limit: int = 20) -> List[StockSearchResult]:
        """Get list of popular stocks for quick selection."""
        popular_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
            'JPM', 'JNJ', 'PG', 'V', 'MA', 'UNH', 'HD', 'KO',
            'SPY', 'QQQ', 'VTI', 'VOO'
        ]
        
        results = []
        for ticker in popular_tickers[:limit]:
            if ticker in self.all_stocks:
                data = self.all_stocks[ticker]
                results.append(StockSearchResult(
                    symbol=ticker,
                    name=data['name'],
                    exchange=data['exchange'],
                    type='etf' if data['sector'] == 'ETF' else 'stock',
                    sector=data['sector'],
                    industry=None,
                    market_cap=None,
                    currency='USD'
                ))
        
        return results


# Global service instance
stock_search_service = StockSearchService()


def get_stock_search_service() -> StockSearchService:
    """Get the global stock search service instance."""
    return stock_search_service