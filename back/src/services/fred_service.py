"""FRED (Federal Reserve Economic Data) API service for economic indicators."""

import asyncio
import hashlib
import logging
import sys
import threading
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
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
class FredSeries:
    """FRED data series information."""
    id: str
    title: str
    frequency: str
    units: str
    seasonal_adjustment: str
    last_updated: datetime
    notes: Optional[str] = None


@dataclass
class FredObservation:
    """FRED data observation."""
    date: datetime
    value: Optional[float]


class FredAPIError(Exception):
    """FRED API specific error."""
    pass


class FredService:
    """Service for fetching economic data from FRED API."""
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    # Key economic indicators
    ECONOMIC_INDICATORS = {
        # GDP & Growth
        "GDP": "GDP",  # Gross Domestic Product
        "GDPC1": "GDPC1",  # Real GDP
        "GDPDEF": "GDPDEF",  # GDP Deflator
        "NYGDPMKTPCDWLD": "NYGDPMKTPCDWLD",  # World GDP per capita

        # NYU Manhattan Condo/Co-op Price Index (추가됨)
        "NYUCSFRCONDOSMSAMID": "NYUCSFRCONDOSMSAMID",  # NYU 콘도/코압 가격지수 (맨해튼)
        
        # Employment & Labor
        "UNRATE": "UNRATE",  # Unemployment Rate
        "CIVPART": "CIVPART",  # Labor Force Participation Rate
        "PAYEMS": "PAYEMS",  # Nonfarm Payrolls
        "EMRATIO": "EMRATIO",  # Employment-Population Ratio
        "AHETPI": "AHETPI",  # Average Hourly Earnings
        "ICSA": "ICSA",  # Initial Claims
        
        # Labor Market Tightness
        "JTSJOL": "JTSJOL",  # Job Openings: Total Nonfarm
        "JTSQUR": "JTSQUR",  # Quits: Total Nonfarm
        "JTSHIR": "JTSHIR",  # Hires: Total Nonfarm
        "JTSTSL": "JTSTSL",  # Total Separations: Total Nonfarm
        
        # Inflation & Prices
        "CPIAUCSL": "CPIAUCSL",  # Consumer Price Index
        "CPILFESL": "CPILFESL",  # Core CPI
        "PCEPI": "PCEPI",  # PCE Price Index
        "PCEPILFE": "PCEPILFE",  # Core PCE Price Index
        "DFEDTARU": "DFEDTARU",  # Federal Funds Target Rate Upper Limit
        "DFEDTARL": "DFEDTARL",  # Federal Funds Target Rate Lower Limit
        
        # Real-Time Inflation Expectations
        "T5YIE": "T5YIE",  # 5-Year Breakeven Inflation Rate
        "T10YIE": "T10YIE",  # 10-Year Breakeven Inflation Rate
        "DFII10": "DFII10",  # 10-Year TIPS-Treasury Spread
        
        # Interest Rates & Monetary Policy
        "FEDFUNDS": "FEDFUNDS",  # Federal Funds Rate
        "DGS10": "DGS10",  # 10-Year Treasury Rate
        "DGS2": "DGS2",  # 2-Year Treasury Rate
        "DGS3MO": "DGS3MO",  # 3-Month Treasury Rate
        "DGS30": "DGS30",  # 30-Year Treasury Rate
        "T10Y2Y": "T10Y2Y",  # 10Y-2Y Treasury Spread
        "T10Y3M": "T10Y3M",  # 10Y-3M Treasury Spread
        
        # Money Supply
        "M1SL": "M1SL",  # M1 Money Stock
        "M2SL": "M2SL",  # M2 Money Stock
        "BOGMBASE": "BOGMBASE",  # Monetary Base
        
        # Housing
        "HOUST": "HOUST",  # Housing Starts
        "HOUSTNSA": "HOUSTNSA",  # Housing Starts (Not Seasonally Adjusted)
        "MORTGAGE30US": "MORTGAGE30US",  # 30-Year Fixed Mortgage Rate
        "CSUSHPISA": "CSUSHPISA",  # Case-Shiller Home Price Index
        
        # Consumer Confidence & Sentiment
        "UMCSENT": "UMCSENT",  # University of Michigan Consumer Sentiment
        "USSLIND": "USSLIND",  # Leading Index for the United States
        
        # Industrial Production & Manufacturing
        "INDPRO": "INDPRO",  # Industrial Production Index
        "TCU": "TCU",  # Capacity Utilization
        
        # Retail & Consumer Spending
        "RSAFS": "RSAFS",  # Retail Sales
        "PCE": "PCE",  # Personal Consumption Expenditures
        "PSAVERT": "PSAVERT",  # Personal Saving Rate
        "DSPIC96": "DSPIC96",  # Real Disposable Personal Income
        
        # Trade & Current Account
        "BOPGSTB": "BOPGSTB",  # Trade Balance
        "IMPGS": "IMPGS",  # Imports of Goods and Services
        "EXPGS": "EXPGS",  # Exports of Goods and Services
        
        # Financial Markets
        "VIXCLS": "VIXCLS",  # VIX Volatility Index
        "DEXUSEU": "DEXUSEU",  # USD/EUR Exchange Rate
        "DEXJPUS": "DEXJPUS",  # JPY/USD Exchange Rate
        "DEXCHUS": "DEXCHUS",  # CNY/USD Exchange Rate
        
        # Financial Conditions Index
        "NFCI": "NFCI",  # Chicago Fed National Financial Conditions Index
        "ANFCI": "ANFCI",  # Adjusted National Financial Conditions Index
        "STLFSI": "STLFSI",  # St. Louis Fed Financial Stress Index
        
        # Global Economic Linkages
        "DTWEXBGS": "DTWEXBGS",  # Trade Weighted U.S. Dollar Index: Broad, Goods
        
        # Regional Economic Activity
        "DPHILBSRMQ": "DPHILBSRMQ",  # Philadelphia Fed Business Conditions Index
        "NYFEDBSRMQ": "NYFEDBSRMQ",  # NY Fed Empire State Manufacturing Index
        "USREC": "USREC",  # NBER Recession Indicators
        
        # Commodities
        "DCOILWTICO": "DCOILWTICO",  # WTI Crude Oil Price
        "DHHNGSP": "DHHNGSP",  # Natural Gas Price
        
        # Government Finance
        "FYFSGDA188S": "FYFSGDA188S",  # Federal Surplus or Deficit
        "GFDEBTN": "GFDEBTN",  # Federal Debt Total Public Debt
        "GFDEGDQ188S": "GFDEGDQ188S",  # Federal Debt as % of GDP
        
        # Credit & Banking Stress
        "DRSFRMACBS": "DRSFRMACBS",  # Delinquency Rate on Credit Card Loans
        "DRBLACBS": "DRBLACBS",  # Delinquency Rate on Business Loans
        "TOTCI": "TOTCI",  # Total Credit to Private Non-Financial Sector
        
        # Financial Stability Metrics
        "MORTGAGE15US": "MORTGAGE15US",  # 15-Year Fixed Mortgage Rate
        "AAA": "AAA",  # Moody's Seasoned Aaa Corporate Bond Yield
        "BAA": "BAA",  # Moody's Seasoned Baa Corporate Bond Yield
        "BAMLH0A0HYM2": "BAMLH0A0HYM2",  # ICE BofA High Yield Index Option-Adjusted Spread
    }
    
    def __init__(self):
        self.api_key = settings.FRED_API_KEY
        if not self.api_key:
            logger.warning("FRED_API_KEY not set. Economic data will not be available.")
        
        # TTL 캐시 설정 (5분 TTL, 최대 500개 항목)
        self._cache_lock = threading.RLock()
        self._cache = TTLCache(maxsize=500, ttl=300)  # 5분 = 300초
        logger.info("FRED service initialized with 5-minute TTL cache (max 500 items)")
    
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters."""
        cache_params = {k: v for k, v in params.items() if k != "api_key"}
        param_str = "&".join(f"{k}={v}" for k, v in sorted(cache_params.items()))
        key_str = f"{endpoint}:{param_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make cached async HTTP request to FRED API."""
        if not self.api_key:
            raise FredAPIError("FRED API key not configured")
        
        # 캐시 키 생성
        cache_key = self._generate_cache_key(endpoint, params)
        
        # 캐시에서 확인
        with self._cache_lock:
            cached_result = self._cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {endpoint}")
                return cached_result
        
        # 캐시 미스 - API 호출
        logger.debug(f"Cache MISS for {endpoint} - calling FRED API")
        
        params.update({
            "api_key": self.api_key,
            "file_type": "json"
        })
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "error_code" in data:
                            raise FredAPIError(f"FRED API error: {data.get('error_message', 'Unknown error')}")
                        
                        # 성공 시 캐시에 저장
                        with self._cache_lock:
                            self._cache[cache_key] = data
                        
                        return data
                    else:
                        text = await response.text()
                        raise FredAPIError(f"HTTP {response.status}: {text}")
        except aiohttp.ClientError as e:
            raise FredAPIError(f"Network error: {str(e)}")
    
    async def get_series_info(self, series_id: str) -> FredSeries:
        """Get information about a FRED data series."""
        try:
            data = await self._make_request("series", {"series_id": series_id})
            series_data = data["seriess"][0]
            
            return FredSeries(
                id=series_data["id"],
                title=series_data["title"],
                frequency=series_data["frequency"],
                units=series_data["units"],
                seasonal_adjustment=series_data["seasonal_adjustment"],
                last_updated=datetime.fromisoformat(series_data["last_updated"].replace("Z", "+00:00")),
                notes=series_data.get("notes")
            )
        except Exception as e:
            logger.error(f"Error fetching series info for {series_id}: {e}")
            raise FredAPIError(f"Failed to get series info: {str(e)}")
    
    async def get_series_observations(
        self,
        series_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[FredObservation]:
        """Get observations for a FRED data series."""
        params = {"series_id": series_id}
        
        if start_date:
            params["observation_start"] = start_date.strftime("%Y-%m-%d")
        
        if end_date:
            params["observation_end"] = end_date.strftime("%Y-%m-%d")
        
        if limit:
            params["limit"] = str(limit)
        
        try:
            data = await self._make_request("series/observations", params)
            observations = []
            
            for obs in data["observations"]:
                try:
                    date = datetime.strptime(obs["date"], "%Y-%m-%d")
                    value = float(obs["value"]) if obs["value"] != "." else None
                    observations.append(FredObservation(date=date, value=value))
                except (ValueError, TypeError):
                    # Skip invalid observations
                    continue
            
            return observations
        except Exception as e:
            logger.error(f"Error fetching observations for {series_id}: {e}")
            raise FredAPIError(f"Failed to get observations: {str(e)}")
    
    async def get_latest_value(self, series_id: str) -> Optional[FredObservation]:
        """Get the latest observation for a series."""
        try:
            observations = await self.get_series_observations(series_id, limit=1)
            return observations[0] if observations else None
        except Exception as e:
            logger.error(f"Error fetching latest value for {series_id}: {e}")
            return None
    
    async def get_economic_indicators(
        self,
        indicators: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, List[FredObservation]]:
        """Get multiple economic indicators at once."""
        if indicators is None:
            # Get key indicators by default - representative from each category
            indicators = [
                # Growth & Productivity
                "GDP", "INDPRO", 
                # Employment & Labor
                "UNRATE", "PAYEMS",
                # Inflation & Prices  
                "CPIAUCSL", "PCEPI",
                # Monetary Policy & Interest Rates
                "FEDFUNDS", "DGS10",
                # Fiscal Policy & Debt
                "GFDEGDQ188S",
                # Financial Markets & Risk
                "VIXCLS", "UMCSENT"
            ]
        
        # Set a high limit to avoid 429 errors from FRED API
        limit = 10000
        
        results = {}
        tasks = []
        
        for indicator in indicators:
            series_id = self.ECONOMIC_INDICATORS.get(indicator, indicator)
            task = self.get_series_observations(series_id, start_date, end_date, limit)
            tasks.append((indicator, task))
        
        for indicator, task in tasks:
            try:
                observations = await task
                results[indicator] = observations
            except Exception as e:
                logger.error(f"Error fetching {indicator}: {e}")
                results[indicator] = []
        
        return results
    
    async def search_series(self, search_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for FRED data series by text."""
        try:
            params = {
                "search_text": search_text,
                "limit": str(limit),
                "order_by": "popularity",
                "sort_order": "desc"
            }
            
            data = await self._make_request("series/search", params)
            return data.get("seriess", [])
        except Exception as e:
            logger.error(f"Error searching series: {e}")
            return []
    
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
            logger.info("FRED cache cleared")


# Global FRED service instance
fred_service = FredService()


def get_fred_service() -> FredService:
    """Get the global FRED service instance."""
    return fred_service