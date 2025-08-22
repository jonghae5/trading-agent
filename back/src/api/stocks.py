"""Advanced stocks API endpoints for comprehensive stock analysis."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.security import User
from src.core.security import get_current_user
from src.services.fred_service import get_fred_service
from back.src.services.stock_service import get_stock_service
from src.schemas.common import ApiResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Service instances
fred_service = get_fred_service()
stocks_service = get_stock_service()


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