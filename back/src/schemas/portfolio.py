from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date, datetime


class PortfolioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    tickers: List[str] = Field(..., min_items=2, max_items=20)
    optimization_method: str = Field(..., pattern="^(max_sharpe|min_volatility|efficient_frontier)$")


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioOptimizeRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=2, max_items=20)
    optimization_method: str = Field(default="max_sharpe", pattern="^(max_sharpe|min_volatility|efficient_frontier)$")
    risk_aversion: float = Field(default=1.0, ge=0.1, le=10.0)
    investment_amount: Optional[float] = Field(default=10000, ge=1000, le=10000000)


class EfficientFrontierPoint(BaseModel):
    expected_return: float
    volatility: float
    sharpe_ratio: float

class IndividualAsset(BaseModel):
    ticker: str
    expected_return: float
    volatility: float

class EfficientFrontierData(BaseModel):
    frontier_points: List[EfficientFrontierPoint]
    max_sharpe_point: Optional[EfficientFrontierPoint] = None
    individual_assets: List[IndividualAsset]
    risk_free_rate: float

class OptimizationResult(BaseModel):
    weights: Dict[str, float]
    expected_annual_return: float
    annual_volatility: float
    sharpe_ratio: float
    value_at_risk_95: Optional[float] = None
    raw_weights: Optional[Dict[str, float]] = None
    discrete_allocation: Optional[Dict[str, int]] = None
    leftover_cash: Optional[float] = None
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    efficient_frontier: Optional[EfficientFrontierData] = None
    

class SimulationDataPoint(BaseModel):
    date: str
    portfolio_value: float
    daily_return: float
    cumulative_return: float


class PortfolioOptimizeResponse(BaseModel):
    optimization: OptimizationResult
    simulation: List[SimulationDataPoint]
    tickers: List[str]


class PortfolioResponse(PortfolioBase):
    id: int
    user_id: int
    weights: List[float]
    expected_return: Optional[float]
    volatility: Optional[float]
    sharpe_ratio: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True