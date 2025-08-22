

"""Market data API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from src.core.security import User, get_current_user

from src.schemas.common import ApiResponse
from src.services.fear_greed_service import get_fear_greed_service, FearGreedService

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize market data service
    
@router.get("/history", response_model=ApiResponse)
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


@router.get("/summary", response_model=ApiResponse)
async def get_fear_greed_summary(
    # Market endpoints are public - no auth required,
    fear_greed_service: FearGreedService = Depends(get_fear_greed_service)
):
    """Get comprehensive market sentiment summary including Fear & Greed Index."""
    try:
        fear_greed_summary = await fear_greed_service.get_fear_greed_summary()
        
        if "error" in fear_greed_summary:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Fear & Greed Index unavailable: {fear_greed_summary['error']}"
            )
        
        return ApiResponse(
            success=True,
            message="Fear & Greed Index retrieved successfully",
            data=fear_greed_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Fear & Greed Index summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch Fear & Greed Index summary"
        )