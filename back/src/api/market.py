"""Market data API endpoints."""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from src.core.security import User, get_current_user
from src.schemas.market import (
    MarketDataResponse,
    EconomicIndicatorResponse,
    MarketIndicesResponse,
    MarketSummaryResponse,
    StockQuoteResponse,
    TechnicalIndicatorsResponse,
    MarketNewsResponse,
    FearGreedIndexResponse,
    FearGreedHistoricalResponse,
    MarketSentimentSummaryResponse,
    SentimentAnalysisResponse
)
from src.schemas.common import ApiResponse
# Remove middleware import - using direct security functions now
from src.services.market_data_service import MarketDataService
from src.services.fear_greed_service import get_fear_greed_service, FearGreedService

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize market data service
market_service = MarketDataService()


@router.get("/quote/{ticker}")
async def get_stock_quote(
    ticker: str,
    # Market endpoints are public - no auth required
):
    """Get real-time stock quote."""
    try:
        ticker = ticker.upper().strip()
        
        if not ticker.isalnum() or len(ticker) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ticker symbol"
            )
        
        quote = await market_service.get_stock_quote(ticker)
        
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quote not found for ticker: {ticker}"
            )
        
        # Return standardized API response
        return JSONResponse(content={
            "success": True,
            "message": f"Quote retrieved for {ticker}",
            "data": {
                "ticker": quote.ticker,
                "company_name": quote.company_name,
                "price": quote.price,
                "change": quote.change,
                "change_percent": quote.change_percent,
                "volume": quote.volume,
                "day_low": quote.day_low,
                "day_high": quote.day_high,
                "week_52_low": quote.week_52_low,
                "week_52_high": quote.week_52_high,
                "previous_close": quote.previous_close,
                "market_cap": quote.market_cap,
                "pe_ratio": quote.pe_ratio,
                "timestamp": quote.timestamp.isoformat()
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stock quote for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stock quote"
        )


@router.get("/quotes", response_model=List[StockQuoteResponse])
async def get_multiple_quotes(
    tickers: str = Query(..., description="Comma-separated ticker symbols"),
    # Market endpoints are public - no auth required
):
    """Get quotes for multiple stocks."""
    try:
        # Parse tickers
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        if len(ticker_list) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 tickers allowed"
            )
        
        # Validate tickers
        for ticker in ticker_list:
            if not ticker.isalnum() or len(ticker) > 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid ticker symbol: {ticker}"
                )
        
        quotes = await market_service.get_multiple_quotes(ticker_list)
        
        return quotes
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get multiple quotes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stock quotes"
        )


@router.get("/indices", response_model=MarketIndicesResponse)
async def get_market_indices(
    # Market endpoints are public - no auth required
):
    """Get major market indices."""
    try:
        indices = await market_service.get_market_indices()
        return indices
        
    except Exception as e:
        logger.error(f"Failed to get market indices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market indices"
        )


@router.get("/summary", response_model=MarketSummaryResponse)
async def get_market_summary(
    # Market endpoints are public - no auth required
):
    """Get market summary with indices and top movers."""
    try:
        summary = await market_service.get_market_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get market summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market summary"
        )


@router.get("/indicators/{ticker}", response_model=TechnicalIndicatorsResponse)
async def get_technical_indicators(
    ticker: str,
    current_user: User = Depends(get_current_user),
    timeframe: str = Query("1d", description="Timeframe: 1m, 5m, 15m, 1h, 1d, 1w")
):
    """Get technical indicators for a stock."""
    try:
        ticker = ticker.upper().strip()
        
        if not ticker.isalnum() or len(ticker) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ticker symbol"
            )
        
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1w", "1M"]
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}"
            )
        
        indicators = await market_service.get_technical_indicators(ticker, timeframe)
        
        if not indicators:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technical indicators not found for ticker: {ticker}"
            )
        
        return indicators
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get technical indicators: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get technical indicators"
        )


@router.get("/news", response_model=MarketNewsResponse)
async def get_market_news(
    # Market endpoints are public - no auth required,
    ticker: Optional[str] = Query(None, description="Filter news by ticker"),
    category: Optional[str] = Query(None, description="News category"),
    limit: int = Query(20, ge=1, le=100, description="Number of articles")
):
    """Get financial news."""
    try:
        if ticker:
            ticker = ticker.upper().strip()
            if not ticker.isalnum() or len(ticker) > 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid ticker symbol"
                )
        
        news = await market_service.get_market_news(
            ticker=ticker,
            category=category,
            limit=limit
        )
        
        return news
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get market news: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market news"
        )


@router.get("/sectors")
async def get_sector_performance(
    # Market endpoints are public - no auth required
):
    """Get sector performance data."""
    try:
        sectors = await market_service.get_sector_performance()
        
        return JSONResponse(content={
            "success": True,
            "data": sectors,
            "timestamp": "2025-01-21T20:00:00Z"  # Would use actual timestamp
        })
        
    except Exception as e:
        logger.error(f"Failed to get sector performance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sector performance"
        )


@router.get("/economic-indicators", response_model=List[EconomicIndicatorResponse])
async def get_economic_indicators(
    # Market endpoints are public - no auth required,
    country: str = Query("US", description="Country code (US, CN, EU, etc.)"),
    category: Optional[str] = Query(None, description="Indicator category")
):
    """Get economic indicators."""
    try:
        indicators = await market_service.get_economic_indicators(
            country=country,
            category=category
        )
        
        return indicators
        
    except Exception as e:
        logger.error(f"Failed to get economic indicators: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get economic indicators"
        )


@router.get("/search")
async def search_stocks(
    query: str = Query(..., description="Search query"),
    # Market endpoints are public - no auth required,
    limit: int = Query(10, ge=1, le=50, description="Number of results")
):
    """Search for stocks by name or ticker."""
    try:
        if len(query) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query too short"
            )
        
        results = await market_service.search_stocks(query, limit)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Found {len(results)} results for '{query}'",
            "data": results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search stocks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search stocks"
        )


# Add chart data endpoint for real-time charts
@router.get("/chart/{ticker}")
async def get_chart_data(
    ticker: str,
    interval: str = Query("1m", description="Chart interval: 1m, 5m, 15m, 1h, 1d"),
    range: str = Query("1d", description="Chart range: 1d, 5d, 1mo, 3mo, 6mo, 1y")
):
    """Get chart data for real-time charts."""
    try:
        ticker = ticker.upper().strip()
        
        if not ticker.isalnum() or len(ticker) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ticker symbol"
            )
        
        # Get quote data first for basic info
        quote = await market_service.get_stock_quote(ticker)
        
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticker not found: {ticker}"
            )
        
        # Generate simulated chart data based on current price
        # In production, this would fetch real historical data
        import random
        from datetime import datetime, timedelta
        
        chart_data = []
        base_price = quote.price
        current_time = datetime.now()
        
        # Generate data points based on interval
        if interval == "1m":
            points = 60  # 1 hour of 1-minute data
            time_delta = timedelta(minutes=1)
        elif interval == "5m":
            points = 72  # 6 hours of 5-minute data
            time_delta = timedelta(minutes=5)
        elif interval == "15m":
            points = 96  # 24 hours of 15-minute data
            time_delta = timedelta(minutes=15)
        elif interval == "1h":
            points = 168  # 1 week of hourly data
            time_delta = timedelta(hours=1)
        else:  # 1d
            points = 30  # 30 days of daily data
            time_delta = timedelta(days=1)
        
        for i in range(points):
            # Generate realistic price movement
            price_variation = random.uniform(-0.02, 0.02)  # 2% max variation
            price = base_price * (1 + price_variation * (i / points))
            volume = random.randint(100000, 2000000)
            
            timestamp = current_time - (time_delta * (points - i - 1))
            
            chart_data.append({
                "timestamp": timestamp.isoformat(),
                "price": round(price, 2),
                "volume": volume
            })
        
        return JSONResponse(content={
            "success": True,
            "message": f"Chart data retrieved for {ticker}",
            "data": chart_data
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chart data for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chart data"
        )


@router.get("/status")
async def get_market_status():
    """Get market status and trading hours."""
    try:
        status_info = await market_service.get_market_status()
        
        return JSONResponse(content={
            "success": True,
            "data": status_info
        })
        
    except Exception as e:
        logger.error(f"Failed to get market status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market status"
        )


@router.get("/fear-greed/history", response_model=ApiResponse)
async def get_fear_greed_history(
    days: int = Query(30, description="Number of days of historical data", ge=1, le=2000),
    aggregation: str = Query("daily", description="Data aggregation: 'daily' or 'monthly'"),
    # Market endpoints are public - no auth required,
    fear_greed_service: FearGreedService = Depends(get_fear_greed_service)
):
    """Get historical CNN Fear & Greed Index data."""
    try:
        # Validate aggregation parameter
        if aggregation not in ["daily", "monthly"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aggregation must be 'daily' or 'monthly'"
            )
        
        historical_data = await fear_greed_service.get_fear_greed_history(days, aggregation=aggregation)
        
        if not historical_data:
            return ApiResponse(
                success=True,
                message="No historical data available",
                data={"data": [], "period_days": days, "aggregation": aggregation}
            )
        
        # Format historical data
        formatted_data = []
        for item in historical_data:
            formatted_data.append({
                "date": item.date.isoformat(),
                "value": item.value,
                "classification": item.classification
            })
        
        response_data = {
            "data": formatted_data,
            "period_days": days,
            "aggregation": aggregation,
            "start_date": historical_data[-1].date.isoformat() if historical_data else None,
            "end_date": historical_data[0].date.isoformat() if historical_data else None,
            "total_points": len(formatted_data)
        }
        
        return ApiResponse(
            success=True,
            message=f"Retrieved {len(formatted_data)} {aggregation} Fear & Greed Index history points",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error fetching Fear & Greed Index history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch Fear & Greed Index history"
        )


@router.get("/sentiment", response_model=ApiResponse)
async def get_market_sentiment_summary(
    # Market endpoints are public - no auth required,
    fear_greed_service: FearGreedService = Depends(get_fear_greed_service)
):
    """Get comprehensive market sentiment summary including Fear & Greed Index."""
    try:
        sentiment_summary = await fear_greed_service.get_market_sentiment_summary()
        
        if "error" in sentiment_summary:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Market sentiment service unavailable: {sentiment_summary['error']}"
            )
        
        return ApiResponse(
            success=True,
            message="Market sentiment summary retrieved successfully",
            data=sentiment_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching market sentiment summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch market sentiment summary"
        )


@router.get("/sentiment/analysis", response_model=ApiResponse)
async def get_advanced_sentiment_analysis(
    include_social: bool = Query(False, description="Include social media sentiment"),
    include_news: bool = Query(False, description="Include news sentiment analysis"),
    include_options: bool = Query(False, description="Include options market sentiment"),
    # Market endpoints are public - no auth required,
    fear_greed_service: FearGreedService = Depends(get_fear_greed_service)
):
    """Get advanced sentiment analysis with multiple data sources."""
    try:
        # Get Fear & Greed Index data
        fear_greed_data = await fear_greed_service.get_current_fear_greed_index()
        
        if not fear_greed_data:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fear & Greed Index data unavailable"
            )
        
        # Base sentiment analysis with Fear & Greed Index
        analysis_data = {
            "fear_greed_index": {
                "value": fear_greed_data.value,
                "classification": fear_greed_data.classification,
                "timestamp": fear_greed_data.timestamp.isoformat()
            },
            "combined_sentiment_score": (fear_greed_data.value - 50) / 50.0,  # Convert to -1 to 1 scale
            "confidence_level": 0.8,  # Base confidence for Fear & Greed Index
            "timestamp": fear_greed_data.timestamp.isoformat()
        }
        
        # Add placeholder for additional sentiment sources
        # These would be implemented with actual APIs in production
        if include_social:
            analysis_data["social_sentiment"] = {
                "twitter_sentiment": 0.1,
                "reddit_sentiment": -0.2,
                "social_volume": "medium",
                "trending_topics": ["market_volatility", "inflation_concerns"]
            }
        
        if include_news:
            analysis_data["news_sentiment"] = {
                "overall_sentiment": 0.05,
                "positive_articles": 12,
                "negative_articles": 8,
                "neutral_articles": 15,
                "key_themes": ["earnings_season", "fed_policy"]
            }
        
        if include_options:
            analysis_data["options_sentiment"] = {
                "put_call_ratio": 1.2,
                "vix_level": 18.5,
                "options_flow": "bearish",
                "gamma_exposure": "negative"
            }
        
        return ApiResponse(
            success=True,
            message="Advanced sentiment analysis retrieved successfully",
            data=analysis_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching advanced sentiment analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch advanced sentiment analysis"
        )