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
        
        # Popular stocks for quick suggestions
        self.popular_stocks = {
            # Tech Giants
            'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'MSFT': {'name': 'Microsoft Corporation', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'GOOGL': {'name': 'Alphabet Inc. (Class A)', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'GOOG': {'name': 'Alphabet Inc. (Class C)', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'AMZN': {'name': 'Amazon.com Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NASDAQ'},
            'META': {'name': 'Meta Platforms Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'TSLA': {'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NASDAQ'},
            'NVDA': {'name': 'NVIDIA Corporation', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'NFLX': {'name': 'Netflix Inc.', 'sector': 'Communication Services', 'exchange': 'NASDAQ'},
            'CRM': {'name': 'Salesforce Inc.', 'sector': 'Technology', 'exchange': 'NYSE'},
            
            # Financial Services
            'JPM': {'name': 'JPMorgan Chase & Co.', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'BAC': {'name': 'Bank of America Corporation', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'WFC': {'name': 'Wells Fargo & Company', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'GS': {'name': 'Goldman Sachs Group Inc.', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'MS': {'name': 'Morgan Stanley', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'BRK.A': {'name': 'Berkshire Hathaway Inc. (Class A)', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'BRK.B': {'name': 'Berkshire Hathaway Inc. (Class B)', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            
            # Healthcare
            'JNJ': {'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'exchange': 'NYSE'},
            'PFE': {'name': 'Pfizer Inc.', 'sector': 'Healthcare', 'exchange': 'NYSE'},
            'UNH': {'name': 'UnitedHealth Group Incorporated', 'sector': 'Healthcare', 'exchange': 'NYSE'},
            'ABBV': {'name': 'AbbVie Inc.', 'sector': 'Healthcare', 'exchange': 'NYSE'},
            'TMO': {'name': 'Thermo Fisher Scientific Inc.', 'sector': 'Healthcare', 'exchange': 'NYSE'},
            
            # Consumer Goods
            'KO': {'name': 'The Coca-Cola Company', 'sector': 'Consumer Defensive', 'exchange': 'NYSE'},
            'PEP': {'name': 'PepsiCo Inc.', 'sector': 'Consumer Defensive', 'exchange': 'NASDAQ'},
            'PG': {'name': 'The Procter & Gamble Company', 'sector': 'Consumer Defensive', 'exchange': 'NYSE'},
            'NKE': {'name': 'NIKE Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'MCD': {'name': 'McDonald\'s Corporation', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'SBUX': {'name': 'Starbucks Corporation', 'sector': 'Consumer Cyclical', 'exchange': 'NASDAQ'},
            
            # Industrial
            'BA': {'name': 'The Boeing Company', 'sector': 'Industrials', 'exchange': 'NYSE'},
            'CAT': {'name': 'Caterpillar Inc.', 'sector': 'Industrials', 'exchange': 'NYSE'},
            'GE': {'name': 'General Electric Company', 'sector': 'Industrials', 'exchange': 'NYSE'},
            'MMM': {'name': '3M Company', 'sector': 'Industrials', 'exchange': 'NYSE'},
            
            # Energy
            'XOM': {'name': 'Exxon Mobil Corporation', 'sector': 'Energy', 'exchange': 'NYSE'},
            'CVX': {'name': 'Chevron Corporation', 'sector': 'Energy', 'exchange': 'NYSE'},
            
            # ETFs
            'SPY': {'name': 'SPDR S&P 500 ETF Trust', 'sector': 'ETF', 'exchange': 'NYSE'},
            'QQQ': {'name': 'Invesco QQQ Trust', 'sector': 'ETF', 'exchange': 'NASDAQ'},
            'VTI': {'name': 'Vanguard Total Stock Market ETF', 'sector': 'ETF', 'exchange': 'NYSE'},
            'VOO': {'name': 'Vanguard S&P 500 ETF', 'sector': 'ETF', 'exchange': 'NYSE'},
            'IWM': {'name': 'iShares Russell 2000 ETF', 'sector': 'ETF', 'exchange': 'NYSE'},
            
            # Korean Stocks (ADRs)
            'TSM': {'name': 'Taiwan Semiconductor Manufacturing Company', 'sector': 'Technology', 'exchange': 'NYSE'},
            'BABA': {'name': 'Alibaba Group Holding Limited', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'ASML': {'name': 'ASML Holding N.V.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
        }
        
        # Extended stock database with more entries
        self.extended_stocks = {
            # Additional Tech Stocks
            'ADBE': {'name': 'Adobe Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'INTC': {'name': 'Intel Corporation', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'AMD': {'name': 'Advanced Micro Devices, Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'ORCL': {'name': 'Oracle Corporation', 'sector': 'Technology', 'exchange': 'NYSE'},
            'IBM': {'name': 'International Business Machines Corporation', 'sector': 'Technology', 'exchange': 'NYSE'},
            'CSCO': {'name': 'Cisco Systems, Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'QCOM': {'name': 'QUALCOMM Incorporated', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'TXN': {'name': 'Texas Instruments Incorporated', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'AVGO': {'name': 'Broadcom Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'NOW': {'name': 'ServiceNow, Inc.', 'sector': 'Technology', 'exchange': 'NYSE'},
            'SNOW': {'name': 'Snowflake Inc.', 'sector': 'Technology', 'exchange': 'NYSE'},
            'PLTR': {'name': 'Palantir Technologies Inc.', 'sector': 'Technology', 'exchange': 'NYSE'},
            'SHOP': {'name': 'Shopify Inc.', 'sector': 'Technology', 'exchange': 'NYSE'},
            'UBER': {'name': 'Uber Technologies, Inc.', 'sector': 'Technology', 'exchange': 'NYSE'},
            'LYFT': {'name': 'Lyft, Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'SPOT': {'name': 'Spotify Technology S.A.', 'sector': 'Communication Services', 'exchange': 'NYSE'},
            'ROKU': {'name': 'Roku, Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'ZM': {'name': 'Zoom Video Communications, Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'DOCU': {'name': 'DocuSign, Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            'OKTA': {'name': 'Okta, Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ'},
            
            # More Financials
            'V': {'name': 'Visa Inc.', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'MA': {'name': 'Mastercard Incorporated', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'PYPL': {'name': 'PayPal Holdings, Inc.', 'sector': 'Financial Services', 'exchange': 'NASDAQ'},
            'SQ': {'name': 'Block, Inc.', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'AXP': {'name': 'American Express Company', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'C': {'name': 'Citigroup Inc.', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            'SCHW': {'name': 'The Charles Schwab Corporation', 'sector': 'Financial Services', 'exchange': 'NYSE'},
            
            # More Consumer
            'WMT': {'name': 'Walmart Inc.', 'sector': 'Consumer Defensive', 'exchange': 'NYSE'},
            'COST': {'name': 'Costco Wholesale Corporation', 'sector': 'Consumer Defensive', 'exchange': 'NASDAQ'},
            'TGT': {'name': 'Target Corporation', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'HD': {'name': 'The Home Depot, Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'LOW': {'name': 'Lowe\'s Companies, Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'F': {'name': 'Ford Motor Company', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'GM': {'name': 'General Motors Company', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE'},
            'DIS': {'name': 'The Walt Disney Company', 'sector': 'Communication Services', 'exchange': 'NYSE'},
            
            # More Healthcare & Biotech
            'MRNA': {'name': 'Moderna, Inc.', 'sector': 'Healthcare', 'exchange': 'NASDAQ'},
            'BNTX': {'name': 'BioNTech SE', 'sector': 'Healthcare', 'exchange': 'NASDAQ'},
            'GILD': {'name': 'Gilead Sciences, Inc.', 'sector': 'Healthcare', 'exchange': 'NASDAQ'},
            'AMGN': {'name': 'Amgen Inc.', 'sector': 'Healthcare', 'exchange': 'NASDAQ'},
            'BIIB': {'name': 'Biogen Inc.', 'sector': 'Healthcare', 'exchange': 'NASDAQ'},
            'REGN': {'name': 'Regeneron Pharmaceuticals, Inc.', 'sector': 'Healthcare', 'exchange': 'NASDAQ'},
            
            # More Energy & Utilities
            'NEE': {'name': 'NextEra Energy, Inc.', 'sector': 'Utilities', 'exchange': 'NYSE'},
            'DUK': {'name': 'Duke Energy Corporation', 'sector': 'Utilities', 'exchange': 'NYSE'},
            'SO': {'name': 'The Southern Company', 'sector': 'Utilities', 'exchange': 'NYSE'},
            'SLB': {'name': 'Schlumberger Limited', 'sector': 'Energy', 'exchange': 'NYSE'},
            'COP': {'name': 'ConocoPhillips', 'sector': 'Energy', 'exchange': 'NYSE'},
            
            # Communication Services
            'T': {'name': 'AT&T Inc.', 'sector': 'Communication Services', 'exchange': 'NYSE'},
            'VZ': {'name': 'Verizon Communications Inc.', 'sector': 'Communication Services', 'exchange': 'NYSE'},
            'CMCSA': {'name': 'Comcast Corporation', 'sector': 'Communication Services', 'exchange': 'NASDAQ'},
            
            # More ETFs
            'VTI': {'name': 'Vanguard Total Stock Market ETF', 'sector': 'ETF', 'exchange': 'NYSE'},
            'VXUS': {'name': 'Vanguard Total International Stock ETF', 'sector': 'ETF', 'exchange': 'NASDAQ'},
            'BND': {'name': 'Vanguard Total Bond Market ETF', 'sector': 'ETF', 'exchange': 'NASDAQ'},
            'GLD': {'name': 'SPDR Gold Shares', 'sector': 'ETF', 'exchange': 'NYSE'},
            'SLV': {'name': 'iShares Silver Trust', 'sector': 'ETF', 'exchange': 'NYSE'},
            'TLT': {'name': 'iShares 20+ Year Treasury Bond ETF', 'sector': 'ETF', 'exchange': 'NASDAQ'},
            'XLF': {'name': 'Financial Select Sector SPDR Fund', 'sector': 'ETF', 'exchange': 'NYSE'},
            'XLK': {'name': 'Technology Select Sector SPDR Fund', 'sector': 'ETF', 'exchange': 'NYSE'},
            'XLE': {'name': 'Energy Select Sector SPDR Fund', 'sector': 'ETF', 'exchange': 'NYSE'},
            'XLV': {'name': 'Health Care Select Sector SPDR Fund', 'sector': 'ETF', 'exchange': 'NYSE'},
        }
        
        # Combine all stocks
        self.all_stocks = {**self.popular_stocks, **self.extended_stocks}
    
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
        """Search stocks using local database."""
        if not query or len(query.strip()) < 1:
            # Return popular stocks if no query
            results = []
            popular_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'SPY', 'QQQ']
            
            for ticker in popular_tickers[:limit]:
                if ticker in self.all_stocks:
                    stock_data = self.all_stocks[ticker]
                    results.append(StockSearchResult(
                        symbol=ticker,
                        name=stock_data['name'],
                        exchange=stock_data['exchange'],
                        type='etf' if stock_data['sector'] == 'ETF' else 'stock',
                        sector=stock_data['sector'],
                        industry=None,
                        market_cap=None,
                        currency='USD'
                    ))
            return results
        
        query = query.upper().strip()
        results = []
        
        # Score all stocks
        scored_stocks = []
        
        for ticker, data in self.all_stocks.items():
            # Calculate scores for different matching criteria
            symbol_score = self._fuzzy_match_score(query, ticker) * 2.0  # Symbol match is most important
            name_score = self._fuzzy_match_score(query, data['name']) * 1.0
            
            # Check if query matches word boundaries in company name
            name_words = data['name'].lower().split()
            word_boundary_score = 0
            for word in name_words:
                if word.startswith(query.lower()):
                    word_boundary_score = 1.5
                    break
            
            total_score = max(symbol_score, name_score, word_boundary_score)
            
            if total_score > 0.1:  # Only include reasonable matches
                scored_stocks.append((ticker, data, total_score))
        
        # Sort by score (descending)
        scored_stocks.sort(key=lambda x: x[2], reverse=True)
        
        # Convert to results
        for ticker, data, score in scored_stocks[:limit]:
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
    
    async def validate_ticker(self, ticker: str) -> bool:
        """Validate if a ticker exists and is tradeable."""
        try:
            ticker = ticker.upper().strip()
            
            # First check local database
            if ticker in self.all_stocks:
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