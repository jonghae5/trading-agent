"""CNN Fear & Greed Index service for market sentiment analysis."""

import asyncio
import logging
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
from dataclasses import dataclass
import json
from bs4 import BeautifulSoup
import re
from src.models.base import get_kst_now
# Add project root to path for trading system imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class FearGreedData:
    """Fear & Greed Index data point."""
    timestamp: datetime
    value: int  # 0-100
    classification: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    previous_close: Optional[int] = None
    one_week_ago: Optional[int] = None
    one_month_ago: Optional[int] = None
    one_year_ago: Optional[int] = None


@dataclass
class FearGreedHistorical:
    """Historical Fear & Greed Index data."""
    date: datetime
    value: int
    classification: str


class FearGreedServiceError(Exception):
    """Fear & Greed service specific error."""
    pass


class FearGreedService:
    """Service for fetching CNN Fear & Greed Index data."""
    
    # CNN Fear & Greed Index endpoints
    CNN_FEAR_GREED_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    CNN_FEAR_GREED_CURRENT = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    
    # Alternative APIs for Fear & Greed Index
    ALTERNATIVE_API_URL = "https://api.alternative.me/fng/"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        # Simple in-memory cache
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=10)  # Cache for 10 minutes
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session
    
    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache_expiry:
            return False
        return get_kst_now() < self._cache_expiry[key]
    
    def _set_cache(self, key: str, value: Any) -> None:
        """Set cache entry with expiry time."""
        self._cache[key] = value
        self._cache_expiry[key] = get_kst_now() + self._cache_duration
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get cache entry if valid."""
        if self._is_cache_valid(key):
            return self._cache[key]
        return None
    
    def _classify_fear_greed_value(self, value: int) -> str:
        """Classify Fear & Greed Index value into categories."""
        if value <= 25:
            return "Extreme Fear"
        elif value <= 45:
            return "Fear"
        elif value <= 55:
            return "Neutral"
        elif value <= 75:
            return "Greed"
        else:
            return "Extreme Greed"
    
    async def get_current_fear_greed_index(self) -> Optional[FearGreedData]:
        """Get current CNN Fear & Greed Index with caching."""

        try:
            session = await self._get_session()
            
            # Try CNN API first
            try:
                async with session.get(self.CNN_FEAR_GREED_URL) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._parse_cnn_fear_greed_data(data)
                        logger.info("Fetched fresh Fear & Greed Index data from CNN")
                        return result
            except Exception as e:
                logger.warning(f"CNN API failed, trying alternative: {e}")
            
            # Try alternative API
            try:
                async with session.get(self.ALTERNATIVE_API_URL + "?limit=1") as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._parse_alternative_fear_greed_data(data)
                        logger.info("Fetched fresh Fear & Greed Index data from alternative API")
                        return result
            except Exception as e:
                logger.warning(f"Alternative API also failed: {e}")
            
            # If both APIs fail, raise error
            raise FearGreedServiceError("Failed to fetch Fear & Greed Index from all sources")
            
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            raise FearGreedServiceError(f"Failed to fetch Fear & Greed Index: {str(e)}")
    
    def _parse_cnn_fear_greed_data(self, data: Dict[str, Any]) -> FearGreedData:
        """Parse CNN Fear & Greed Index API response."""
        try:
            # CNN API structure may vary, adapt as needed
            fear_greed_data = data.get('fear_and_greed', {})
            current_value = int(fear_greed_data.get('score', 50))
            
            # Get historical values if available
            previous_close = fear_greed_data.get('previous_close')
            one_week_ago = fear_greed_data.get('one_week_ago')
            one_month_ago = fear_greed_data.get('one_month_ago')
            one_year_ago = fear_greed_data.get('one_year_ago')
            
            return FearGreedData(
                timestamp=get_kst_now(),
                value=current_value,
                classification=self._classify_fear_greed_value(current_value),
                previous_close=int(previous_close) if previous_close else None,
                one_week_ago=int(one_week_ago) if one_week_ago else None,
                one_month_ago=int(one_month_ago) if one_month_ago else None,
                one_year_ago=int(one_year_ago) if one_year_ago else None
            )
            
        except Exception as e:
            logger.error(f"Error parsing CNN Fear & Greed data: {e}")
            raise FearGreedServiceError(f"Failed to parse CNN data: {str(e)}")
    
    def _parse_alternative_fear_greed_data(self, data: Dict[str, Any]) -> FearGreedData:
        """Parse alternative Fear & Greed Index API response."""
        try:
            # Alternative.me API structure
            if 'data' in data and len(data['data']) > 0:
                latest = data['data'][0]
                current_value = int(latest.get('value', 50))
                
                return FearGreedData(
                    timestamp=datetime.fromtimestamp(int(latest.get('timestamp', 0))),
                    value=current_value,
                    classification=latest.get('value_classification', self._classify_fear_greed_value(current_value))
                )
            
            raise ValueError("No data found in alternative API response")
            
        except Exception as e:
            logger.error(f"Error parsing alternative Fear & Greed data: {e}")
            raise FearGreedServiceError(f"Failed to parse alternative data: {str(e)}")
    
    
    async def get_fear_greed_history(self, days: int = 30, aggregation: str = "daily") -> List[FearGreedHistorical]:
        """Get historical Fear & Greed Index data."""
        try:
            session = await self._get_session()
            
            # Try to get historical data from alternative API
            try:
                # Alternative.me API: limit=0 means get all available data (usually 2-3 years)
                # For more than available data, we still get the maximum available
                url = f"{self.ALTERNATIVE_API_URL}?limit=0" if days > 1000 else f"{self.ALTERNATIVE_API_URL}?limit={days}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        historical_data = self._parse_historical_data(data)
                        
                        all_data = historical_data
                        
                        # Apply aggregation if requested
                        if aggregation == "monthly":
                            return self._aggregate_monthly(all_data)
                        else:
                            return all_data
                            
            except Exception as e:
                logger.warning(f"Failed to get historical data: {e}")
            
            # If API fails, raise error
            raise FearGreedServiceError("Failed to fetch historical Fear & Greed Index data")
            
        except Exception as e:
            logger.error(f"Error fetching historical Fear & Greed data: {e}")
            raise FearGreedServiceError(f"Failed to fetch historical Fear & Greed data: {str(e)}")
    
    def _parse_historical_data(self, data: Dict[str, Any]) -> List[FearGreedHistorical]:
        """Parse historical Fear & Greed Index API response."""
        try:
            historical_data = []
            
            if 'data' in data:
                for item in data['data']:
                    timestamp = datetime.fromtimestamp(int(item.get('timestamp', 0)))
                    value = int(item.get('value', 50))
                    classification = item.get('value_classification', self._classify_fear_greed_value(value))
                    
                    historical_data.append(FearGreedHistorical(
                        date=timestamp,
                        value=value,
                        classification=classification
                    ))
            
            # Sort by date (newest first)
            historical_data.sort(key=lambda x: x.date, reverse=True)
            return historical_data
            
        except Exception as e:
            logger.error(f"Error parsing historical data: {e}")
            return []
    
    
    def _aggregate_monthly(self, daily_data: List[FearGreedHistorical]) -> List[FearGreedHistorical]:
        """Aggregate daily Fear & Greed data into monthly averages."""
        if not daily_data:
            return []
        
        from collections import defaultdict
        
        # Group data by year-month
        monthly_groups = defaultdict(list)
        
        for item in daily_data:
            # Use first day of the month as the key
            month_key = item.date.replace(day=1)
            monthly_groups[month_key].append(item)
        
        # Calculate monthly averages
        monthly_data = []
        for month_date, items in monthly_groups.items():
            # Calculate average value for the month
            avg_value = int(sum(item.value for item in items) / len(items))
            
            # Determine classification based on average
            classification = self._classify_fear_greed_value(avg_value)
            
            monthly_data.append(FearGreedHistorical(
                date=month_date,
                value=avg_value,
                classification=classification
            ))
        
        # Sort by date (newest first)
        monthly_data.sort(key=lambda x: x.date, reverse=True)
        return monthly_data
    
    async def get_fear_greed_summary(self) -> Dict[str, Any]:
        """Get comprehensive market sentiment summary."""
        try:
            # Get current Fear & Greed Index
            current_fg = await self.get_current_fear_greed_index()
            
            # Get recent history for trend analysis
            history = await self.get_fear_greed_history(7)
            
            if not current_fg:
                return {"error": "Unable to fetch Fear & Greed Index data"}
            
            # Calculate trend
            trend = "neutral"
            if len(history) >= 2:
                recent_avg = sum(h.value for h in history[:3]) / min(3, len(history))
                if current_fg.value > recent_avg + 5:
                    trend = "improving"
                elif current_fg.value < recent_avg - 5:
                    trend = "declining"
            
            # Calculate volatility (standard deviation of recent values)
            volatility = "low"
            if len(history) >= 5:
                values = [h.value for h in history[:5]]
                avg = sum(values) / len(values)
                variance = sum((x - avg) ** 2 for x in values) / len(values)
                std_dev = variance ** 0.5
                
                if std_dev > 15:
                    volatility = "high"
                elif std_dev > 8:
                    volatility = "medium"
            
            return {
                "current": {
                    "value": history[0].value, 
                    "classification": history[0].classification,
                    "timestamp": history[0].date.isoformat()
                },
                "trend": trend,
                "volatility": volatility,
                "historical_comparison": {
                    "previous_close": history[1],
                    "one_week_ago": history[6],
                    "one_month_ago": current_fg.one_month_ago,
                    "one_year_ago": current_fg.one_year_ago
                },
                "recent_history": [
                    {
                        "date": h.date.isoformat(),
                        "value": h.value,
                        "classification": h.classification
                    }
                    for h in history[:7]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting market sentiment summary: {e}")
            return {"error": str(e)}


# Global Fear & Greed service instance
fear_greed_service = FearGreedService()


def get_fear_greed_service() -> FearGreedService:
    """Get the global Fear & Greed service instance."""
    return fear_greed_service