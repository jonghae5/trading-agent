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
    SimulationDataPoint, EconomicEvent, BacktestRequest, BacktestResponse
)
from ..schemas.common import ApiResponse
from ..services.portfolio_service import PortfolioOptimizationService
from src.services.economic_service import get_economic_service, EconomicService
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portfolio"])

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
        
        # DB에 저장 (고급 지표 포함)
        db_portfolio = Portfolio(
            user_id=current_user.id,
            name=portfolio.name,
            description=portfolio.description,
            tickers=valid_tickers,
            ticker_weights=portfolio.ticker_weights,
            optimization_method=portfolio.optimization_method,
            rebalance_frequency=portfolio.rebalance_frequency
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
        portfolio.updated_at = datetime.now(timezone.utc)
        
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


@router.post("/backtest/walk-forward", response_model=ApiResponse[BacktestResponse])
async def walk_forward_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_user)
):
    """Walk-Forward Analysis 백테스팅 - 월스트리트 스타일"""
    try:
        logger.info(f"User {current_user.username} starting Walk-Forward Analysis")
        
        # 종목 코드 유효성 검증 (비동기)
        valid_tickers = await PortfolioOptimizationService.validate_tickers_async(request.tickers)
        if len(valid_tickers) < 2:
            raise HTTPException(
                status_code=400, 
                detail="최소 2개 이상의 유효한 종목이 필요합니다."
            )
        
        # 리밸런싱 빈도에 따른 데이터 가져오기 (분기별=5년, 월별=2년)
        price_data = await PortfolioOptimizationService.fetch_price_data(
            tickers=valid_tickers, 
            rebalance_freq=request.rebalance_frequency or "monthly"
        )
        
        # Walk-Forward Analysis 실행 (비동기) - 고정 비중 통합
        backtest_result = await PortfolioOptimizationService.walk_forward_analysis(
            price_data,
            method=request.optimization_method,
            rebalance_freq=request.rebalance_frequency or "monthly",
            transaction_cost=request.transaction_cost or 0.001,
            fixed_weights=request.ticker_weights,  # 고정 비중 전달 (있는 경우)
            investment_amount=request.investment_amount or 100000,
            max_position_size=request.max_position_size or 0.40
        )
        
        response = BacktestResponse(
            backtest_type="walk_forward",
            results=backtest_result,
            tickers=valid_tickers
        )
        
        logger.info(f"Walk-Forward Analysis completed for user {current_user.username}")
        return ApiResponse(
            success=True,
            message="Walk-Forward Analysis 백테스팅이 완료되었습니다.",
            data=response
        )
        
    except ValueError as e:
        logger.warning(f"Walk-Forward backtest validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Walk-Forward 백테스트 API 에러: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Walk-Forward 백테스트 중 서버 오류가 발생했습니다."
        )




