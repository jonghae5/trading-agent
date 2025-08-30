"""API router configuration."""

from fastapi import APIRouter

from .auth import router as auth_router
from .analysis import router as analysis_router
from .reports import router as reports_router
from .fear_greed import router as fear_greed_router
from .economic import router as economic_router
from .stocks import router as stocks_router
from .news import router as news_router
from .portfolio import router as portfolio_router

# Main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(fear_greed_router, prefix="/fear-greed", tags=["fear-greed"])
api_router.include_router(economic_router, prefix="/economic", tags=["economic"])
api_router.include_router(stocks_router, prefix="/stocks", tags=["stocks"])
api_router.include_router(news_router, prefix="/news", tags=["news"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])

__all__ = ["api_router"]