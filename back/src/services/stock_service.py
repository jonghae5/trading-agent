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


class StockService:
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

    
    def _is_korea_stock(self, ticker: str) -> bool:
        # 숫자로만 이루어져 있고 6자리인지 확인
        return ticker.isdigit() and len(ticker) == 6

    def _guess_korea_market_yf(self, ticker: str):
        # 코스피: .KS, 코스닥: .KQ
        if self._is_korea_stock(ticker):
            try:
                info_ks = yf.Ticker(ticker + ".KS").info
                if info_ks and "shortName" in info_ks and info_ks.get("exchange") == "KSC":
                    return f"{ticker}.KS"
            except Exception:
                pass
            try:
                info_kq = yf.Ticker(ticker + ".KQ").info
                if info_kq and "shortName" in info_kq and info_kq.get("exchange") == "KOE":
                    return f"{ticker}.KQ"
            except Exception:
                pass
        return ticker
        
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
            t = self._guess_korea_market_yf(ticker.upper())
            stock = yf.Ticker(t)
            info = stock.info
            
            # Check if we got valid data
            if not info or 'symbol' not in info:
                return None
            
            # Return yfinance info in a format suitable for DB upsert
            return {
                **info,
                "symbol": ticker.upper()
            }
            
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
                    t = self._guess_korea_market_yf(ticker.upper())
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
    
    async def search_stocks(self, query: str, limit: int = 10) -> List[StockSearchResult]:
        """Main search function - delegates to ticker-based search."""
        return await self.search_stocks_by_ticker(query, limit)
   
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

# Global service instance
stock_service = StockService()


def get_stock_service() -> StockService:
    """Get the global stock search service instance."""
    return stock_service