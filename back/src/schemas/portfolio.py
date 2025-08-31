from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date, datetime


class PortfolioBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    tickers: List[str] = Field(..., min_items=2, max_items=20)
    optimization_method: str = Field(..., pattern="^(max_sharpe|min_volatility|efficient_frontier)$")
    rebalance_frequency: str = Field(..., pattern="^(monthly|quarterly)$")


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioOptimizeRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=2, max_items=20)
    optimization_method: str = Field(default="max_sharpe", pattern="^(max_sharpe|min_volatility|efficient_frontier|risk_parity)$")
    investment_amount: Optional[float] = Field(default=10000, ge=1000, le=10000000)
    transaction_cost: Optional[float] = Field(default=0.001, ge=0.0, le=0.05)
    max_position_size: Optional[float] = Field(default=0.30, ge=0.05, le=0.60)


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
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    calmar_ratio: Optional[float] = None
    value_at_risk_95: Optional[float] = None
    raw_weights: Optional[Dict[str, float]] = None
    discrete_allocation: Optional[Dict[str, int]] = None
    leftover_cash: Optional[float] = None
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    efficient_frontier: Optional[EfficientFrontierData] = None
    transaction_cost_impact: Optional[float] = None
    concentration_limit: Optional[float] = None
    

class SimulationDataPoint(BaseModel):
    date: str
    portfolio_value: float
    daily_return: float
    cumulative_return: float


class EconomicEvent(BaseModel):
    date: str
    detail_date: str
    title: str
    description: str
    type: str
    severity: str
    color: str
    icon: str
    impact_duration_months: Optional[int] = None
    related_indicators: List[str] = []
    priority: int = 5


class PortfolioOptimizeResponse(BaseModel):
    optimization: OptimizationResult
    simulation: List[SimulationDataPoint]
    tickers: List[str]
    economic_events: Optional[List[EconomicEvent]] = []


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    tickers: List[str]
    optimization_method: str
    rebalance_frequency: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BacktestRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=2, max_items=20)
    optimization_method: str = Field(default="max_sharpe", pattern="^(max_sharpe|min_volatility|efficient_frontier|risk_parity)$")
    
    # Walk-Forward Analysis 파라미터
    rebalance_frequency: Optional[str] = Field(default="monthly", pattern="^(monthly|quarterly)$")
    
    # 공통 파라미터
    investment_amount: Optional[float] = Field(default=100000, ge=1000, le=10000000)
    transaction_cost: Optional[float] = Field(default=0.001, ge=0.0, le=0.05)
    max_position_size: Optional[float] = Field(default=0.30, ge=0.05, le=0.60)


class BacktestResponse(BaseModel):
    backtest_type: str  # "walk_forward", "out_of_sample", "monthly_rebalancing"
    results: Dict  # 백테스트 결과 (각 방법마다 구조가 다름)
    tickers: List[str]
