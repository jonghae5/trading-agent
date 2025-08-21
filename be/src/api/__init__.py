"""API router configuration."""

from fastapi import APIRouter

from .auth import router as auth_router
from .analysis import router as analysis_router
from .reports import router as reports_router
from .market import router as market_router
from .economic import router as economic_router
from .insights import router as insights_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(market_router, prefix="/market", tags=["market"])
api_router.include_router(economic_router, prefix="/economic", tags=["economic"])
api_router.include_router(insights_router, prefix="/insights", tags=["insights"])

__all__ = ["api_router"]