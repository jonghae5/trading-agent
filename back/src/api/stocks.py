"""Advanced stocks API endpoints for comprehensive stock analysis."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.security import User
from src.core.security import get_current_user
from back.src.services.stock_service import get_stock_service
from src.services.finnhub_service import get_finnhub_service
from src.schemas.common import ApiResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Service instances
stocks_service = get_stock_service()
finnhub_service = get_finnhub_service()


@router.get("/search/stocks")
async def search_stocks(
    q: str = Query(..., description="Search query for stock tickers or company names"),
    limit: int = Query(10, description="Maximum number of results", ge=1, le=50),
    current_user: User = Depends(get_current_user),
):  # Public endpoint - no authentication
    """Search for stocks by ticker or company name."""
    try:
        if not q or len(q.strip()) < 1:
            # Return popular stocks if no query - Note: Service needs to be converted to sync
            results = stocks_service.get_popular_stocks(limit)
        else:
            # Search for stocks - Note: Service needs to be converted to sync
            results = await stocks_service.search_stocks(q.strip(), limit)
        
        # Convert results to dict
        search_results = [
            {
                "symbol": result.symbol,
                "name": result.name,
                "exchange": result.exchange,
                "type": result.type,
                "sector": result.sector,
                "industry": result.industry,
                "market_cap": result.market_cap,
                "currency": result.currency
            } for result in results
        ]
        
        logger.info(f"Stock search completed for query '{q}' - {len(search_results)} results")
        
        return ApiResponse(
            success=True,
            message="Stock search completed successfully",
            data={
                "query": q,
                "results": search_results,
                "count": len(search_results)
            }
        )
        
    except Exception as e:
        logger.error(f"Stock search failed for query '{q}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stock search failed"
        )


@router.get("/recommendation-trends/{symbol}")
async def get_recommendation_trends(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    """Get analyst recommendation trends for a company."""
    try:
        trends = await finnhub_service.get_recommendation_trends(symbol)
        
        logger.info(f"Recommendation trends fetched for {symbol}")
        
        return ApiResponse(
            success=True,
            message="Recommendation trends fetched successfully",
            data={
                "symbol": symbol.upper(),
                "trends": trends
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch recommendation trends for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recommendation trends"
        )


@router.get("/earnings-surprises/{symbol}")
async def get_earnings_surprises(
    symbol: str,
    limit: int = Query(None, description="Limit number of periods returned", ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    """Get company historical quarterly earnings surprise."""
    try:
        surprises = await finnhub_service.get_earnings_surprises(symbol, limit)
        
        logger.info(f"Earnings surprises fetched for {symbol}")
        
        return ApiResponse(
            success=True,
            message="Earnings surprises fetched successfully",
            data={
                "symbol": symbol.upper(),
                "surprises": surprises
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch earnings surprises for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch earnings surprises"
        )