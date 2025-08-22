"""Economic indicators API endpoints using FRED data."""

import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.core.security import User
from src.schemas.common import ApiResponse
from src.services.fred_service import get_fred_service, FredService, FredAPIError
from back.src.services.economic_service import get_economic_service, EconomicService, EventType, EventSeverity
from src.models.base import get_kst_now

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/historical", response_model=ApiResponse)
async def get_historical_data(
    indicators: str = Query(..., description="Comma-separated list of indicator names or series IDs"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
    include_events: bool = Query(True, description="Include economic events markers"),
    event_types: Optional[str] = Query(None, description="Filter events by type (comma-separated)"),
    min_severity: Optional[str] = Query(None, description="Minimum event severity (low, medium, high, critical)"),
    # Public endpoint - no authentication required
    fred_service: FredService = Depends(get_fred_service),
    events_service: EconomicService = Depends(get_economic_service)
):
    """Get historical economic data with optional event markers for long-term analysis."""
    try:
        # Parse indicators
        indicator_list = [ind.strip() for ind in indicators.split(",")]
        
        # Parse dates
        try:
            parsed_start_date = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
        
        parsed_end_date = get_kst_now()
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        # Validate date range (max 50 years for performance)
        date_diff = parsed_end_date - parsed_start_date
        if date_diff.days > 365 * 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 50 years"
            )
        
        # Get economic data
        indicators_data = await fred_service.get_economic_indicators(
            indicator_list, parsed_start_date, parsed_end_date
        )
        
        # Format the economic data
        formatted_data = {}
        for indicator, observations in indicators_data.items():
            formatted_data[indicator] = [
                {
                    "date": obs.date.isoformat(),
                    "value": obs.value
                }
                for obs in observations if obs.value is not None
            ]
        
        # Get economic events if requested
        events_data = []
        if include_events:
            # Parse event type filters
            event_type_filters = None
            if event_types:
                try:
                    event_type_filters = [
                        EventType(et.strip()) for et in event_types.split(",")
                    ]
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid event type. Valid types: crisis, recession, policy_change, market_event, geopolitical, pandemic"
                    )
            
            # Parse minimum severity
            min_severity_filter = None
            if min_severity:
                try:
                    min_severity_filter = EventSeverity(min_severity.lower())
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid severity level. Valid levels: low, medium, high, critical"
                    )
            
            events_data = events_service.get_events_in_date_range(
                parsed_start_date, 
                parsed_end_date,
                event_type_filters,
                min_severity_filter
            )
        
        response_data = {
            "date_range": {
                "start": parsed_start_date.isoformat(),
                "end": parsed_end_date.isoformat(),
                "duration_days": (parsed_end_date - parsed_start_date).days
            },
            "indicators": formatted_data,
            "events": events_data,
            "metadata": {
                "indicators_count": len(formatted_data),
                "events_count": len(events_data),
                "data_points_total": sum(len(data) for data in formatted_data.values())
            }
        }
        
        return ApiResponse(
            success=True,
            message=f"Retrieved historical data for {len(indicator_list)} indicators from {start_date} to {parsed_end_date.date()}",
            data=response_data
        )
    
    except FredAPIError as e:
        logger.error(f"FRED API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Economic data service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch historical data: {str(e)}"
        )


@router.get("/events", response_model=ApiResponse)
async def get_economic_events(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    event_types: Optional[str] = Query(None, description="Filter by event types (comma-separated)"),
    min_severity: Optional[str] = Query(None, description="Minimum severity level"),
    indicator: Optional[str] = Query(None, description="Filter events relevant to specific indicator"),
    # Public endpoint - no authentication required
    events_service: EconomicService = Depends(get_economic_service)
):
    """Get economic events and crisis markers."""
    try:
        # Parse dates
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        # Get events based on whether specific indicator is requested
        if indicator:
            events_data = events_service.get_events_for_indicator(
                indicator, parsed_start_date, parsed_end_date
            )
        else:
            # Parse event type filters
            event_type_filters = None
            if event_types:
                try:
                    event_type_filters = [
                        EventType(et.strip()) for et in event_types.split(",")
                    ]
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid event type"
                    )
            
            # Parse minimum severity
            min_severity_filter = None
            if min_severity:
                try:
                    min_severity_filter = EventSeverity(min_severity.lower())
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid severity level"
                    )
            
            # Default date range if not specified (last 50 years)
            if not parsed_start_date:
                parsed_start_date = get_kst_now() - timedelta(days=365*50)
            if not parsed_end_date:
                parsed_end_date = get_kst_now()
            
            events_data = events_service.get_events_in_date_range(
                parsed_start_date,
                parsed_end_date,
                event_type_filters,
                min_severity_filter
            )
        
        # Get available filter options
        available_types = events_service.get_all_event_types()
        available_severities = events_service.get_all_severity_levels()
        
        response_data = {
            "events": events_data,
            "metadata": {
                "total_events": len(events_data),
                "date_range": {
                    "start": parsed_start_date.isoformat() if parsed_start_date else None,
                    "end": parsed_end_date.isoformat() if parsed_end_date else None
                },
                "filters": {
                    "indicator": indicator,
                    "event_types": event_types.split(",") if event_types else None,
                    "min_severity": min_severity
                }
            },
            "available_filters": {
                "event_types": available_types,
                "severity_levels": available_severities
            }
        }
        
        return ApiResponse(
            success=True,
            message=f"Retrieved {len(events_data)} economic events",
            data=response_data
        )
    
    except Exception as e:
        logger.error(f"Error fetching economic events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch economic events: {str(e)}"
        )