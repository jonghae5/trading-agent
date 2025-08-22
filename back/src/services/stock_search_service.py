"""Stock search service for ticker autocomplete functionality."""

import logging
import asyncio
import yfinance as yf
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func, and_, desc
from sqlalchemy.dialects.sqlite import insert

from src.models.base import get_kst_now
from src.core.config import settings
from src.core.database import get_database_manager
from src.models.stock_universe import Base, StockInfo
from src.services.fred_service import get_fred_service
import time

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
        self.executor = ThreadPoolExecutor(max_workers=15)
        self.fred_service = get_fred_service()
        self.db_manager = get_database_manager()
        
        # Ticker caching (requirement #4)
        self.ticker_cache = {}  # Cache for ticker search results
        self.ticker_cache_duration = 3600  # 1 hour cache for tickers
        self.yfinance_cache = {}  # Cache for yfinance API results
        self.yfinance_cache_duration = 1800  # 30 minutes for API results

    
    def _get_ticker_cache_key(self, ticker: str) -> str:
        """Generate cache key for ticker search."""
        return f"ticker_{ticker.upper().strip()}"
    
    def _get_yfinance_cache_key(self, ticker: str) -> str:
        """Generate cache key for yfinance API results."""
        return f"yf_{ticker.upper().strip()}"
    
    def _is_ticker_cache_valid(self, cache_time: datetime) -> bool:
        """Check if ticker cache is still valid."""
        return get_kst_now() - cache_time < timedelta(seconds=self.ticker_cache_duration)
    
    def _is_yfinance_cache_valid(self, cache_time: datetime) -> bool:
        """Check if yfinance cache is still valid."""
        return get_kst_now() - cache_time < timedelta(seconds=self.yfinance_cache_duration)
    
    def _search_yfinance_sync(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Search yfinance for ticker info (requirement #2)."""
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            # Check if we got valid data
            if not info or 'symbol' not in info:
                return None
            
            # Return yfinance info in a format suitable for DB upsert
            return info
            
        except Exception as e:
            logger.debug(f"Error searching yfinance for {ticker}: {e}")
            return None
    
    def _get_stock_info_sync(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get stock info synchronously from yfinance."""
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            # Check if we got valid data
            if not info or 'symbol' not in info:
                return None
            
            # Return formatted stock data
            return {
                'symbol': ticker.upper(),
                'name': info.get('longName', info.get('shortName', ticker)),
                'exchange': info.get('exchange', 'Unknown'),
                'type': info.get('quoteType', 'EQUITY').lower(),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'market_cap': info.get('marketCap'),
                'currency': info.get('currency', 'USD'),
                'price': info.get('regularMarketPrice', info.get('previousClose')),
                'volume': info.get('regularMarketVolume', info.get('averageVolume'))
            }
            
        except Exception as e:
            logger.debug(f"Error getting stock info for {ticker}: {e}")
            return None
    
    def _get_multiple_stocks_info_sync(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get info for multiple stocks at once (batch processing)."""
        try:
            # Use yfinance batch download for better performance  
            if len(tickers) > 1:
                # Create a space-separated string of tickers
                ticker_string = ' '.join(tickers)
                stocks = yf.Tickers(ticker_string)
                
                results = {}
                for ticker in tickers:
                    try:
                        stock = getattr(stocks.tickers, ticker, None)
                        if stock:
                            info = stock.info
                            if info and 'symbol' in info:
                                results[ticker] = {
                                    'symbol': ticker.upper(),
                                    'name': info.get('longName', info.get('shortName', ticker)),
                                    'exchange': info.get('exchange', 'Unknown'),
                                    'type': info.get('quoteType', 'EQUITY').lower(),
                                    'sector': info.get('sector'),
                                    'industry': info.get('industry'),
                                    'market_cap': info.get('marketCap'),
                                    'currency': info.get('currency', 'USD'),
                                    'price': info.get('regularMarketPrice', info.get('previousClose')),
                                    'volume': info.get('regularMarketVolume', info.get('averageVolume'))
                                }
                    except Exception as e:
                        logger.debug(f"Error processing {ticker} in batch: {e}")
                        continue
                
                return results
            else:
                # Single ticker
                ticker = tickers[0]
                result = self._get_stock_info_sync(ticker)
                return {ticker: result} if result else {}
                
        except Exception as e:
            logger.debug(f"Batch processing failed: {e}, falling back to individual calls")
            # Fallback to individual calls
            results = {}
            for ticker in tickers:
                result = self._get_stock_info_sync(ticker)
                if result:
                    results[ticker] = result
            return results
    
    async def _build_popular_stocks(self) -> List[Dict[str, Any]]:
        """Build popular stocks based on market cap and volume (optimized with batch processing)."""
        start_time = time.perf_counter()
        try:
            # Popular tickers by market cap and trading volume
            popular_tickers = [
                # Mega Cap Tech
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
                # Financial Services 
                'JPM', 'V', 'MA', 'BRK.B', 'BAC', 'WFC',
                # Healthcare & Consumer
                'JNJ', 'UNH', 'PG', 'KO', 'PEP', 'WMT', 'HD',
                # Communication & Entertainment
                'DIS', 'NFLX', 'CRM', 'ADBE',
                # ETFs
                'SPY', 'QQQ', 'VTI', 'VOO', 'IWM'
            ]
            
            # Use batch processing for better performance
            loop = asyncio.get_event_loop()
            
            # Split tickers into smaller batches to avoid overwhelming the API
            batch_size = 10
            all_results = {}
            
            for i in range(0, len(popular_tickers), batch_size):
                batch = popular_tickers[i:i + batch_size]
                
                # Process batch
                batch_results = await loop.run_in_executor(
                    self.executor,
                    self._get_multiple_stocks_info_sync,
                    batch
                )
                
                all_results.update(batch_results)
            
            # Convert to list format
            results = []
            for ticker in popular_tickers:
                if ticker in all_results and all_results[ticker]:
                    results.append(all_results[ticker])
            
            # Sort by market cap (descending)
            results.sort(key=lambda x: x.get('market_cap', 0) or 0, reverse=True)
            
            elapsed = time.perf_counter() - start_time
            logger.info(f"Built {len(results)} popular stocks in {elapsed:.4f} seconds")
            
            return results
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"Error building popular stocks: {e} (elapsed {elapsed:.4f}s)")
            return self._get_fallback_popular_stocks()
    
    def _get_fallback_popular_stocks(self) -> List[Dict[str, Any]]:
        """Fallback popular stocks if API fails."""
        return [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ', 'type': 'equity', 'sector': 'Technology', 'currency': 'USD'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'NASDAQ', 'type': 'equity', 'sector': 'Technology', 'currency': 'USD'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'type': 'equity', 'sector': 'Technology', 'currency': 'USD'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'NASDAQ', 'type': 'equity', 'sector': 'Consumer Cyclical', 'currency': 'USD'},
            {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'exchange': 'ARCA', 'type': 'etf', 'sector': 'Diversified', 'currency': 'USD'}
        ]
    

    async def search_stocks_by_ticker(self, ticker: str, limit: int = 10) -> List[StockSearchResult]:
        """
        새로운 요구사항에 맞는 주식 검색:
        1. ticker가 들어오면 DB에서 startswith으로 검색한다
        2. 없으면 yfinance 검색한다  
        3. yfinance로 검색한 결과가 있으면 DB upsert한다
        4. 전체적으로 ticker caching
        """
        start_time = time.perf_counter()
        ticker = ticker.strip()
        
        # Check ticker cache first (requirement #4)
        cache_key = self._get_ticker_cache_key(ticker)
        if cache_key in self.ticker_cache:
            cache_entry = self.ticker_cache[cache_key] 
            if self._is_ticker_cache_valid(cache_entry['timestamp']):
                logger.debug(f"⚡ Ticker cache HIT for '{ticker}'")
                return cache_entry['results']
        
        try:
            # Step 1: DB에서 startswith 검색 (requirement #1)
            db_results = await self._search_stocks_in_db(ticker, limit)
            
            results = []
            for stock_data in db_results:
                results.append(StockSearchResult(
                    symbol=stock_data['symbol'],
                    name=stock_data['name'],
                    exchange=stock_data['exchange'],
                    type=stock_data['type'],
                    sector=stock_data.get('sector'),
                    industry=stock_data.get('industry'),
                    market_cap=stock_data.get('market_cap'),
                    currency=stock_data.get('currency', 'USD')
                ))
            
            # If we found results in DB, cache and return
            if results:
                elapsed = time.perf_counter() - start_time
                logger.info(f"🚀 DB search for '{ticker}' took {elapsed:.4f}s, found {len(results)} results")
                
                # Cache results (requirement #4)
                self.ticker_cache[cache_key] = {
                    'results': results,
                    'timestamp': get_kst_now()
                }
                return results
            
            # Step 2: 없으면 yfinance 검색 (requirement #2)
            if ticker and len(ticker) <= 10:  # 유효한 ticker 길이
                yf_cache_key = self._get_yfinance_cache_key(ticker)
                
                # Check yfinance cache first
                yfinance_data = None
                if yf_cache_key in self.yfinance_cache:
                    yf_cache_entry = self.yfinance_cache[yf_cache_key]
                    if self._is_yfinance_cache_valid(yf_cache_entry['timestamp']):
                        yfinance_data = yf_cache_entry['data']
                        logger.debug(f"⚡ YFinance cache HIT for '{ticker}'")
                
                # If not in cache, search yfinance
                if yfinance_data is None:
                    loop = asyncio.get_event_loop()
                    yfinance_data = await loop.run_in_executor(
                        self.executor,
                        self._search_yfinance_sync,
                        ticker
                    )
                    
                    # Cache yfinance result
                    if yfinance_data:
                        self.yfinance_cache[yf_cache_key] = {
                            'data': yfinance_data,
                            'timestamp': get_kst_now()
                        }
                
                # Step 3: yfinance 결과가 있으면 DB upsert (requirement #3)
                if yfinance_data:
                    # Upsert to database
                    upsert_success = await self._upsert_stock_to_db(ticker, yfinance_data)
                    
                    if upsert_success:
                        # Create result from yfinance data
                        result = StockSearchResult(
                            symbol=ticker.upper(),
                            name=yfinance_data.get('longName', yfinance_data.get('shortName', ticker)),
                            exchange=yfinance_data.get('exchange', 'Unknown'),
                            type='etf' if yfinance_data.get('quoteType') == 'ETF' else 'equity',
                            sector=yfinance_data.get('sector'),
                            industry=yfinance_data.get('industry'),
                            market_cap=yfinance_data.get('marketCap'),
                            currency=yfinance_data.get('currency', 'USD')
                        )
                        
                        results = [result]
                        elapsed = time.perf_counter() - start_time
                        logger.info(f"🔍 YFinance search for '{ticker}' took {elapsed:.4f}s, found and upserted")
                        
                        # Cache results (requirement #4)
                        self.ticker_cache[cache_key] = {
                            'results': results,
                            'timestamp': get_kst_now()
                        }
                        return results
            
            # Step 4: 마지막으로 name LIKE 검색 시도
            name_results = await self._search_stocks_by_name_in_db(ticker, limit)
            
            results = []
            for stock_data in name_results:
                results.append(StockSearchResult(
                    symbol=stock_data['symbol'],
                    name=stock_data['name'],
                    exchange=stock_data['exchange'],
                    type=stock_data['type'],
                    sector=stock_data.get('sector'),
                    industry=stock_data.get('industry'),
                    market_cap=stock_data.get('market_cap'),
                    currency=stock_data.get('currency', 'USD')
                ))
            
            if results:
                elapsed = time.perf_counter() - start_time
                logger.info(f"🔍 Name search for '{ticker}' took {elapsed:.4f}s, found {len(results)} results")
                
                # Cache results
                self.ticker_cache[cache_key] = {
                    'results': results,
                    'timestamp': get_kst_now()
                }
                return results
            
            # No results found anywhere
            elapsed = time.perf_counter() - start_time  
            logger.info(f"❌ No results found for '{ticker}' in {elapsed:.4f}s")
            
            # Cache empty result to avoid repeated API calls
            self.ticker_cache[cache_key] = {
                'results': [],
                'timestamp': get_kst_now()
            }
            return []
            
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"Error searching for ticker '{ticker}': {e} (elapsed {elapsed:.4f}s)")
            return []
    
    async def validate_ticker(self, ticker: str) -> bool:
        """Validate if a ticker exists and is tradeable using yfinance."""
        try:
            ticker = ticker.upper().strip()
            
            # Use async executor to run yfinance validation
            loop = asyncio.get_event_loop()
            stock_info = await loop.run_in_executor(
                self.executor,
                self._get_stock_info_sync,
                ticker
            )
            
            return stock_info is not None and 'symbol' in stock_info
            
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return False
    
    async def get_stock_info_real(self, ticker: str) -> Optional[StockSearchResult]:
        """Get detailed information for a specific ticker using real APIs."""
        try:
            ticker = ticker.upper().strip()
            
            # Use async executor to run yfinance call
            loop = asyncio.get_event_loop()
            stock_data = await loop.run_in_executor(
                self.executor,
                self._get_stock_info_sync,
                ticker
            )
            
            if stock_data:
                return StockSearchResult(
                    symbol=stock_data['symbol'],
                    name=stock_data['name'],
                    exchange=stock_data['exchange'],
                    type=stock_data['type'],
                    sector=stock_data.get('sector'),
                    industry=stock_data.get('industry'),
                    market_cap=stock_data.get('market_cap'),
                    currency=stock_data.get('currency', 'USD')
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting stock info for {ticker}: {e}")
            return None
    
    async def get_stock_info(self, ticker: str) -> Optional[StockSearchResult]:
        """Legacy method for backward compatibility."""
        return await self.get_stock_info_real(ticker)
    
    async def search_stocks(self, query: str, limit: int = 10) -> List[StockSearchResult]:
        """Main search function - delegates to ticker-based search."""
        return await self.search_stocks_by_ticker(query, limit)
    
    async def _get_fallback_search_results(self, query: str, limit: int) -> List[StockSearchResult]:
        """Ultimate fallback when all search methods fail."""
        try:
            # First try to search by query in DB
            if query and query.strip():
                db_results = await self._search_stocks_in_db(query, limit)
                if db_results:
                    results = []
                    for stock_data in db_results:
                        results.append(StockSearchResult(
                            symbol=stock_data['symbol'],
                            name=stock_data['name'],
                            exchange=stock_data['exchange'],
                            type=stock_data['type'],
                            sector=stock_data.get('sector'),
                            industry=stock_data.get('industry'),
                            market_cap=stock_data.get('market_cap'),
                            currency=stock_data.get('currency', 'USD')
                        ))
                    return results
            
            # If no query results, try to get popular stocks from DB
            popular_stocks = await self._get_popular_stocks_from_db(limit)
            
            results = []
            for stock_data in popular_stocks:
                results.append(StockSearchResult(
                    symbol=stock_data['symbol'],
                    name=stock_data['name'],
                    exchange=stock_data['exchange'],
                    type=stock_data['type'],
                    sector=stock_data.get('sector'),
                    industry=stock_data.get('industry'),
                    market_cap=stock_data.get('market_cap'),
                    currency=stock_data.get('currency', 'USD')
                ))
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Even fallback failed: {e}")
            # Hard-coded ultimate fallback
            return [
                StockSearchResult(
                    symbol='AAPL', name='Apple Inc.', exchange='NASDAQ', 
                    type='equity', sector='Technology', currency='USD'
                ),
                StockSearchResult(
                    symbol='SPY', name='SPDR S&P 500 ETF Trust', exchange='ARCA', 
                    type='etf', sector='Diversified', currency='USD'
                )
            ]
    
    async def get_dynamic_popular_stocks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get dynamically updated popular stocks based on real market data."""
        # Check if we have recent cache
        now = get_kst_now()
        if (self.popular_stocks_last_updated and 
            self.popular_stocks_cache and
            now - self.popular_stocks_last_updated < timedelta(hours=6)):  # Cache for 6 hours
            return self.popular_stocks_cache[:limit]
        
        try:
            # Build fresh popular stocks list
            popular_stocks = await self._build_popular_stocks()
            
            # Update cache
            self.popular_stocks_cache = popular_stocks
            self.popular_stocks_last_updated = now
            
            return popular_stocks[:limit]
            
        except Exception as e:
            logger.error(f"Error getting dynamic popular stocks: {e}")
            # Return fallback
            return self._get_fallback_popular_stocks()[:limit]
    
    def _is_fast_cache_valid(self, cache_time: datetime) -> bool:
        """Check if fast cache is still valid."""
        return get_kst_now() - cache_time < timedelta(seconds=self.fast_cache_duration)
    
    async def _search_with_fred_data(self, query: str, limit: int = 5) -> List[StockSearchResult]:
        """Use FRED API to get economic context and enhance search results."""
        try:
            if not settings.FRED_API_KEY:
                return []
            
            # Search for relevant economic series that might relate to the query
            series_results = await self.fred_service.search_series(query, limit=5)
            
            enhanced_results = []
            for series in series_results:
                # If the series title contains stock-related keywords, try to extract ticker symbols
                title = series.get('title', '').upper()
                
                # Look for ticker-like patterns in FRED series titles
                import re
                ticker_pattern = r'\b[A-Z]{1,5}\b'
                potential_tickers = re.findall(ticker_pattern, title)
                
                for ticker in potential_tickers:
                    if len(ticker) >= 2 and ticker not in [r.symbol for r in enhanced_results]:
                        # Validate this ticker with yfinance
                        stock_info = await self.get_stock_info_real(ticker)
                        if stock_info:
                            enhanced_results.append(stock_info)
                            if len(enhanced_results) >= limit:
                                break
                
                if len(enhanced_results) >= limit:
                    break
            
            return enhanced_results
            
        except Exception as e:
            logger.debug(f"FRED search enhancement failed: {e}")
            return []
    
    async def get_popular_stocks(self, limit: int = 20) -> List[StockSearchResult]:
        """Get popular stocks from database."""
        try:
            popular_stocks_data = await self._get_popular_stocks_from_db(limit)
            
            results = []
            for stock_data in popular_stocks_data:
                results.append(StockSearchResult(
                    symbol=stock_data['symbol'],
                    name=stock_data['name'],
                    exchange=stock_data['exchange'],
                    type=stock_data['type'],
                    sector=stock_data.get('sector'),
                    industry=stock_data.get('industry'),
                    market_cap=stock_data.get('market_cap'),
                    currency=stock_data.get('currency', 'USD')
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting popular stocks: {e}")
            return []
    
    
    async def _search_stocks_in_db(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fast ticker-based search using startswith in database (requirement #1)."""
        try:
            async with self.db_manager.get_async_session() as session:
                if not ticker.strip():
                    # Return popular stocks when no query
                    stmt = select(StockInfo).where(
                        and_(StockInfo.is_active == True, StockInfo.is_popular == True)
                    ).order_by(StockInfo.popularity_rank).limit(limit)
                else:
                    ticker_upper = ticker.upper().strip()
                    
                    # Search by ticker startswith (requirement #1)
                    stmt = select(StockInfo).where(
                        and_(
                            StockInfo.is_active == True,
                            StockInfo.symbol.like(f'{ticker_upper}%')  # startswith only
                        )
                    ).order_by(
                        # Exact match first, then alphabetical
                        StockInfo.symbol == ticker_upper,
                        StockInfo.symbol
                    ).limit(limit)
                
                result = await session.execute(stmt)
                stocks = result.scalars().all()
                
                return [stock.to_dict() for stock in stocks]
                
        except Exception as e:
            logger.error(f"Error in DB ticker search: {e}")
            return []
    
    async def _search_stocks_by_name_in_db(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search stocks by name LIKE in database."""
        try:
            async with self.db_manager.get_async_session() as session:
                query_upper = query.upper().strip()
                
                # Search by name contains query (case insensitive)
                stmt = select(StockInfo).where(
                    and_(
                        StockInfo.is_active == True,
                        func.upper(StockInfo.name).like(f'%{query_upper}%')  # case insensitive name search
                    )
                ).order_by(StockInfo.name).limit(limit)
                
                result = await session.execute(stmt)
                stocks = result.scalars().all()
                
                return [stock.to_dict() for stock in stocks]
                
        except Exception as e:
            logger.error(f"Error in DB name search: {e}")
            return []
    
    async def _upsert_stock_to_db(self, ticker: str, stock_data: Dict[str, Any]) -> bool:
        """Insert or update stock from yfinance result (requirement #3)."""
        try:
            async with self.db_manager.get_async_session() as session:
                # Prepare database data
                db_data = {
                    'symbol': ticker.upper(),
                    'name': stock_data.get('longName', stock_data.get('shortName', ticker)),
                    'short_name': stock_data.get('shortName', ticker),
                    'name_upper': stock_data.get('longName', stock_data.get('shortName', ticker)).upper(),
                    'exchange': stock_data.get('exchange', 'Unknown'),
                    'sector': stock_data.get('sector'),
                    'industry': stock_data.get('industry'),
                    'market_cap': stock_data.get('marketCap'),
                    'currency': stock_data.get('currency', 'USD'),
                    'country': stock_data.get('country', 'US'),
                    'stock_type': 'etf' if stock_data.get('quoteType') == 'ETF' else 'equity',
                    'avg_volume': stock_data.get('averageVolume'),
                    'shares_outstanding': stock_data.get('sharesOutstanding'),
                    'is_active': True,
                    'is_popular': False,  # New stocks are not popular by default
                    'updated_at': datetime.now()
                }
                
                # UPSERT operation
                stmt = insert(StockInfo).values(**db_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol'],
                    set_=db_data
                )
                
                await session.execute(stmt)
                
                logger.info(f"✅ Upserted stock {ticker} to database")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error upserting stock {ticker}: {e}")
            return False
    
    async def _get_popular_stocks_from_db(self, limit: int = 20) -> List[Dict[str, Any]]:
        """DB에서 인기 주식 가져오기."""
        try:
            async with self.db_manager.get_async_session() as session:
                stmt = select(StockInfo).where(
                    and_(StockInfo.is_active == True, StockInfo.is_popular == True)
                ).order_by(StockInfo.popularity_rank).limit(limit)
                
                result = await session.execute(stmt)
                stocks = result.scalars().all()
                
                return [stock.to_dict() for stock in stocks]
                
        except Exception as e:
            logger.error(f"Error getting popular stocks from DB: {e}")
            return []
    
    async def get_stock_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """심볼로 주식 정보 가져오기."""
        try:
            async with self.db_manager.get_async_session() as session:
                stmt = select(StockInfo).where(
                    and_(StockInfo.symbol == symbol.upper(), StockInfo.is_active == True)
                )
                result = await session.execute(stmt)
                stock = result.scalar_one_or_none()
                
                return stock.to_dict() if stock else None
                
        except Exception as e:
            logger.error(f"Error getting stock by symbol {symbol}: {e}")
            return None
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            async with self.db_manager.get_async_session() as session:
                # Count total stocks
                total_result = await session.execute(select(func.count(StockInfo.symbol)))
                total_stocks = total_result.scalar()
                
                # Count popular stocks
                popular_result = await session.execute(
                    select(func.count(StockInfo.symbol)).where(StockInfo.is_popular == True)
                )
                popular_stocks = popular_result.scalar()
                
                # Count by exchange
                exchange_result = await session.execute(
                    select(StockInfo.exchange, func.count(StockInfo.symbol))
                    .group_by(StockInfo.exchange)
                )
                exchanges = dict(exchange_result.all())
                
                # Count by sector
                sector_result = await session.execute(
                    select(StockInfo.sector, func.count(StockInfo.symbol))
                    .where(StockInfo.sector.isnot(None))
                    .group_by(StockInfo.sector)
                )
                sectors = dict(sector_result.all())
                
                return {
                    'total_stocks': total_stocks,
                    'popular_stocks': popular_stocks,
                    'exchanges': exchanges,
                    'sectors': sectors,
                    'last_updated': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


# Global service instance
stock_search_service = StockSearchService()


def get_stock_search_service() -> StockSearchService:
    """Get the global stock search service instance."""
    return stock_search_service