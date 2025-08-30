from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.portfolio import Portfolio
from ..schemas.portfolio import (
    PortfolioCreate, PortfolioOptimizeRequest, PortfolioOptimizeResponse,
    PortfolioResponse,  OptimizationResult,
    SimulationDataPoint
)
from ..schemas.common import ApiResponse
from ..services.portfolio_service import PortfolioOptimizationService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portfolio"])


@router.post("/optimize", response_model=ApiResponse[PortfolioOptimizeResponse])
async def optimize_portfolio(
    request: PortfolioOptimizeRequest,
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 최적화"""
    try:
        logger.info(f"User {current_user.username} optimizing portfolio with tickers: {request.tickers}")
        
        # 종목 코드 유효성 검증
        valid_tickers = PortfolioOptimizationService.validate_tickers(request.tickers)
        if len(valid_tickers) < 2:
            raise HTTPException(
                status_code=400, 
                detail="최소 2개 이상의 유효한 종목이 필요합니다."
            )
        
        # 주가 데이터 가져오기
        price_data = await PortfolioOptimizationService.fetch_price_data(valid_tickers)
        
        # 포트폴리오 최적화
        optimization_result = PortfolioOptimizationService.optimize_portfolio(
            price_data, 
            method=request.optimization_method,
            risk_aversion=request.risk_aversion,
            investment_amount=request.investment_amount or 10000
        )
        
        # 포트폴리오 시뮬레이션
        simulation_data = PortfolioOptimizationService.simulate_portfolio_performance(
            price_data, 
            optimization_result["weights"]
        )
        
        # 응답 데이터 구성
        optimization = OptimizationResult(
            weights=optimization_result["weights"],
            expected_annual_return=optimization_result["expected_annual_return"],
            annual_volatility=optimization_result["annual_volatility"],
            sharpe_ratio=optimization_result["sharpe_ratio"],
            value_at_risk_95=optimization_result.get("value_at_risk_95"),
            raw_weights=optimization_result.get("raw_weights"),
            discrete_allocation=optimization_result.get("discrete_allocation"),
            leftover_cash=optimization_result.get("leftover_cash"),
            correlation_matrix=optimization_result.get("correlation_matrix"),
            efficient_frontier=optimization_result.get("efficient_frontier")
        )
        
        simulation = [
            SimulationDataPoint(
                date=row["date"],
                portfolio_value=row["portfolio_value"],
                daily_return=row["daily_return"],
                cumulative_return=row["cumulative_return"]
            )
            for _, row in simulation_data.tail(252).iterrows()  # 최근 1년
        ]
        
        response = PortfolioOptimizeResponse(
            optimization=optimization,
            simulation=simulation,
            tickers=valid_tickers
        )
        
        logger.info(f"Portfolio optimization completed for user {current_user.username}")
        return ApiResponse(
            success=True,
            message="포트폴리오 최적화가 완료되었습니다.",
            data=response
        )
        
    except ValueError as e:
        logger.warning(f"Portfolio optimization validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"포트폴리오 최적화 API 에러: {e}")
        raise HTTPException(
            status_code=500, 
            detail="포트폴리오 최적화 중 서버 오류가 발생했습니다."
        )


@router.post("", response_model=ApiResponse[PortfolioResponse])
async def create_portfolio(
    portfolio: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 저장"""
    try:
        logger.info(f"User {current_user.username} creating portfolio: {portfolio.name}")
        
        # 종목 코드 유효성 검증
        valid_tickers = PortfolioOptimizationService.validate_tickers(portfolio.tickers)
        if len(valid_tickers) < 2:
            raise HTTPException(
                status_code=400, 
                detail="최소 2개 이상의 유효한 종목이 필요합니다."
            )
        
        # 주가 데이터 가져오기 및 최적화
        price_data = await PortfolioOptimizationService.fetch_price_data(valid_tickers)
        optimization_result = PortfolioOptimizationService.optimize_portfolio(
            price_data, 
            portfolio.optimization_method
        )
        
        # 가중치를 리스트로 변환 (종목 순서대로)
        weights_list = [
            optimization_result["weights"].get(ticker, 0.0) 
            for ticker in valid_tickers
        ]
        
        # DB에 저장
        db_portfolio = Portfolio(
            user_id=current_user.id,
            name=portfolio.name,
            description=portfolio.description,
            tickers=valid_tickers,
            weights=weights_list,
            optimization_method=portfolio.optimization_method,
            expected_return=optimization_result["expected_annual_return"],
            volatility=optimization_result["annual_volatility"],
            sharpe_ratio=optimization_result["sharpe_ratio"]
        )
        
        db.add(db_portfolio)
        db.commit()
        db.refresh(db_portfolio)
        
        logger.info(f"Portfolio {portfolio.name} created successfully for user {current_user.username}")
        return ApiResponse(
            success=True,
            message="포트폴리오가 성공적으로 저장되었습니다.",
            data=db_portfolio
        )
        
    except ValueError as e:
        db.rollback()
        logger.warning(f"Portfolio creation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"포트폴리오 저장 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail="포트폴리오 저장에 실패했습니다."
        )


@router.get("", response_model=ApiResponse[List[PortfolioResponse]])
async def get_user_portfolios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """사용자 포트폴리오 목록"""
    try:
        portfolios = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.is_active == True
        ).order_by(Portfolio.created_at.desc()).all()
        
        logger.info(f"Retrieved {len(portfolios)} portfolios for user {current_user.username}")
        return ApiResponse(
            success=True,
            message=f"{len(portfolios)}개의 포트폴리오를 조회했습니다.",
            data=portfolios
        )
        
    except Exception as e:
        logger.error(f"포트폴리오 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail="포트폴리오 목록을 불러오는데 실패했습니다."
        )


@router.get("/{portfolio_id}", response_model=ApiResponse[PortfolioResponse])
async def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 포트폴리오 조회"""
    try:
        portfolio = db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active == True
        ).first()
        
        if not portfolio:
            raise HTTPException(
                status_code=404, 
                detail="포트폴리오를 찾을 수 없습니다."
            )
        
        return ApiResponse(
            success=True,
            message="포트폴리오를 조회했습니다.",
            data=portfolio
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"포트폴리오 조회 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail="포트폴리오 조회에 실패했습니다."
        )


@router.delete("/{portfolio_id}", response_model=ApiResponse[Dict])
async def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """포트폴리오 삭제 (소프트 삭제)"""
    try:
        portfolio = db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active == True
        ).first()
        
        if not portfolio:
            raise HTTPException(
                status_code=404, 
                detail="포트폴리오를 찾을 수 없습니다."
            )
        
        # 소프트 삭제
        portfolio.is_active = False
        portfolio.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Portfolio {portfolio_id} deleted by user {current_user.username}")
        return ApiResponse(
            success=True,
            message="포트폴리오가 삭제되었습니다.",
            data={"message": "포트폴리오가 삭제되었습니다."}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"포트폴리오 삭제 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail="포트폴리오 삭제에 실패했습니다."
        )
