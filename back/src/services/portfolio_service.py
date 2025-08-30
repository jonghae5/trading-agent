import yfinance as yf
import pandas as pd
import numpy as np
from pypfopt import EfficientFrontier, risk_models, expected_returns, objective_functions
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt.exceptions import OptimizationError
import cvxpy as cp
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PortfolioOptimizationService:
    """Portfolio optimization service using PyPortfolioOpt."""
    
    @staticmethod
    async def fetch_price_data(tickers: List[str], period: str = "2y") -> pd.DataFrame:
        """주가 데이터 가져오기"""
        try:
            # yfinance로 데이터 가져오기
            data = yf.download(tickers, period=period, progress=False)
            # 단일 종목인 경우 처리
            if len(tickers) == 1:
                data = pd.DataFrame(data['Close'])
                data.columns = tickers
            else:
                # MultiIndex에서 Close 데이터만 추출
                data = data['Close']
                # 컬럼명이 MultiIndex인 경우 단순 컬럼으로 변환
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(1)
                
            # 결측값 제거
            data = data.dropna()
            
            if data.empty:
                raise ValueError("선택한 종목들의 데이터를 가져올 수 없습니다.")
                
            logger.info(f"Successfully fetched price data for {len(tickers)} tickers")
            return data
            
        except Exception as e:
            logger.error(f"주가 데이터 가져오기 실패: {e}")
            raise ValueError(f"주가 데이터를 가져올 수 없습니다: {str(e)}")
    
    @staticmethod
    def optimize_portfolio(
        price_data: pd.DataFrame, 
        method: str = "max_sharpe",
        risk_aversion: float = 1.0,
        investment_amount: float = 100000
    ) -> Dict:
        """포트폴리오 최적화 - 개선된 버전"""
        try:
            # 데이터 검증
            if len(price_data) < 30:
                raise ValueError("최소 30일 이상의 가격 데이터가 필요합니다")
            
            # 기대 수익률과 공분산 행렬 계산 (더 정확한 방법 사용)
            mu = expected_returns.capm_return(price_data, frequency=252)
            S = risk_models.CovarianceShrinkage(price_data).ledoit_wolf()
            
            # 효율적 프론티어 생성
            ef = EfficientFrontier(mu, S)
            
            # 제약 조건 추가 (더 현실적인 포트폴리오)
            ef.add_constraint(lambda w: cp.sum(w) == 1)  # 가중치 합 = 1
            ef.add_constraint(lambda w: w >= 0.005)          # 공매도 금지
            ef.add_constraint(lambda w: w <= 0.6)        # 최대 60% 이하 (집중도 제한)
            
            # 최적화 방법에 따른 가중치 계산
            if method == "max_sharpe":
                weights = ef.max_sharpe(risk_free_rate=0.02)  # 무위험 수익률 2%
            elif method == "min_volatility":
                weights = ef.min_volatility()
            elif method == "efficient_frontier":
                # L2 정규화를 사용한 균형 잡힌 포트폴리오
                ef.add_objective(objective_functions.L2_reg, gamma=0.1)
                # 보수적인 목표 수익률 설정 (최대 기대수익률의 70% 또는 평균 수익률의 110% 중 작은 값)
                target_return = min(mu.mean() * 1.1, mu.max() * 0.7)
                try:
                    weights = ef.efficient_return(target_return, market_neutral=False)
                except OptimizationError:
                    logger.warning("Target return not achievable, using max_sharpe instead")
                    ef = EfficientFrontier(mu, S)  # 제약조건 재설정
                    ef.add_constraint(lambda w: cp.sum(w) == 1)  # 가중치 합 = 1
                    ef.add_constraint(lambda w: w >= 0)          # 공매도 금지
                    ef.add_constraint(lambda w: w <= 0.6)        # 최대 60% 이하 (집중도 제한)
                    weights = ef.max_sharpe(risk_free_rate=0.02)
            else:
                raise ValueError(f"지원하지 않는 최적화 방법: {method}")
            
            # 가중치 정제 (소수점 3자리, 최소 임계값 적용)
            cleaned_weights = ef.clean_weights(cutoff=0.005, rounding=3)
            
            # 성과 지표 계산
            performance = ef.portfolio_performance(verbose=False, risk_free_rate=0.02)
            
            # 유효한 가중치만 반환 (0.5% 이상)
            significant_weights = {k: v for k, v in cleaned_weights.items() if v >= 0.005}
            
            # 가중치 정규화 (합이 정확히 1이 되도록)
            total_weight = sum(significant_weights.values())
            if total_weight > 0:
                significant_weights = {k: v/total_weight for k, v in significant_weights.items()}
            
            # 추가 위험 지표 계산
            portfolio_returns = price_data.pct_change().dropna()
            weights_series = pd.Series(significant_weights).reindex(portfolio_returns.columns, fill_value=0)
            weighted_returns = portfolio_returns.dot(weights_series)
            
            # VaR (Value at Risk) 계산
            var_95 = np.percentile(weighted_returns, 5) * np.sqrt(252)  # 연간화
            
            # 이산 할당 계산 (실제 주식 수량)
            try:
                latest_prices = get_latest_prices(price_data)
                da = DiscreteAllocation(significant_weights, latest_prices, total_portfolio_value=investment_amount)
                allocation, leftover = da.greedy_portfolio()
            except Exception as e:
                logger.warning(f"Discrete allocation calculation failed: {e}")
                allocation = {}
                leftover = 0.0
            
            # 상관관계 매트릭스 계산
            correlation_matrix = price_data.corr().round(3).to_dict()
            
            # Efficient Frontier 계산
            efficient_frontier_data = PortfolioOptimizationService._calculate_efficient_frontier(mu, S)
            
            return {
                "weights": significant_weights,
                "expected_annual_return": round(float(performance[0]), 4),
                "annual_volatility": round(float(performance[1]), 4),
                "sharpe_ratio": round(float(performance[2]), 2),
                "value_at_risk_95": round(float(var_95), 4),
                "raw_weights": dict(cleaned_weights),
                "discrete_allocation": allocation,
                "leftover_cash": round(float(leftover), 2),
                "correlation_matrix": correlation_matrix,
                "efficient_frontier": efficient_frontier_data
            }
            
        except (OptimizationError, cp.error.SolverError) as e:
            logger.error(f"최적화 솔버 오류: {e}")
            # 간단한 균등 가중치로 폴백
            return PortfolioOptimizationService._fallback_equal_weights(price_data)
        except Exception as e:
            logger.error(f"포트폴리오 최적화 실패: {e}")
            raise ValueError(f"포트폴리오 최적화에 실패했습니다: {str(e)}")
    
    @staticmethod
    def _fallback_equal_weights(price_data: pd.DataFrame) -> Dict:
        """최적화 실패 시 균등 가중치 포트폴리오 반환"""
        logger.warning("Optimization failed, falling back to equal weights")
        
        n_assets = len(price_data.columns)
        equal_weight = 1.0 / n_assets
        weights = {col: equal_weight for col in price_data.columns}
        
        # 균등 가중 포트폴리오 성과 계산
        returns = price_data.pct_change().dropna()
        portfolio_returns = returns.mean(axis=1)
        
        annual_return = portfolio_returns.mean() * 252
        annual_vol = portfolio_returns.std() * np.sqrt(252)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0
        
        return {
            "weights": weights,
            "expected_annual_return": float(annual_return),
            "annual_volatility": float(annual_vol),
            "sharpe_ratio": float(sharpe),
            "value_at_risk_95": float(np.percentile(portfolio_returns, 5) * np.sqrt(252)),
            "raw_weights": weights
        }
    
    @staticmethod
    def simulate_portfolio_performance(
        price_data: pd.DataFrame,
        weights: Dict[str, float],
        initial_value: float = 10000
    ) -> pd.DataFrame:
        """포트폴리오 성과 시뮬레이션"""
        try:
            # 일일 수익률 계산
            returns = price_data.pct_change().dropna()
            
            # 가중치에 해당하는 종목들만 선택
            available_tickers = [ticker for ticker in weights.keys() if ticker in returns.columns]
            if not available_tickers:
                raise ValueError("가중치에 해당하는 종목 데이터가 없습니다.")
            
            # 포트폴리오 가중치를 pandas Series로 변환
            weight_series = pd.Series(weights)
            weight_series = weight_series.reindex(available_tickers, fill_value=0)
            
            # 가중치 정규화
            weight_series = weight_series / weight_series.sum()
            
            # 포트폴리오 수익률 계산
            portfolio_returns = returns[available_tickers].dot(weight_series)
            
            # 포트폴리오 가치 계산
            portfolio_value = initial_value * (1 + portfolio_returns).cumprod()
            
            # 누적 수익률 계산
            cumulative_return = (portfolio_value / initial_value - 1)
            
            # 결과 DataFrame 생성
            simulation_df = pd.DataFrame({
                'date': portfolio_value.index.strftime('%Y-%m-%d'),
                'portfolio_value': portfolio_value.values,
                'daily_return': portfolio_returns.values,
                'cumulative_return': cumulative_return.values
            })
            
            return simulation_df.reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"포트폴리오 시뮬레이션 실패: {e}")
            raise ValueError(f"포트폴리오 시뮬레이션에 실패했습니다: {str(e)}")
    
    @staticmethod
    def validate_tickers(tickers: List[str]) -> List[str]:
        """종목 코드 유효성 검증"""
        try:
            # yfinance로 간단한 데이터 요청해서 유효성 확인
            test_data = yf.download(tickers, period="5d", progress=False)
            
            if test_data.empty:
                raise ValueError("유효하지 않은 종목 코드가 포함되어 있습니다.")
            
            # 실제 데이터가 있는 종목들만 반환
            if len(tickers) == 1:
                return tickers if not test_data.empty else []
            else:
                # MultiIndex 컬럼 구조에서 유효한 티커 확인
                if isinstance(test_data.columns, pd.MultiIndex):
                    valid_tickers = [ticker for ticker in tickers if ticker in test_data.columns.get_level_values(1)]
                else:
                    valid_tickers = [ticker for ticker in tickers if ticker in test_data.columns]
                return valid_tickers
                
        except Exception as e:
            logger.error(f"종목 코드 유효성 검증 실패: {e}")
            raise ValueError(f"종목 코드 유효성 검증에 실패했습니다: {str(e)}")
    
    @staticmethod
    def _calculate_efficient_frontier(mu, S, num_portfolios=100):
        """Efficient Frontier 계산"""
        try:
            # 효율적 프론티어 포인트들 계산
            min_vol = mu.min()
            max_vol = mu.max()
            target_returns = np.linspace(min_vol, max_vol * 0.95, num_portfolios)
            
            efficient_portfolios = []
            
            for target_return in target_returns:
                try:
                    # 새로운 EfficientFrontier 인스턴스 생성
                    ef_temp = EfficientFrontier(mu, S)
                    ef_temp.add_constraint(lambda w: cp.sum(w) == 1)
                    ef_temp.add_constraint(lambda w: w >= 0)
                    
                    # 목표 수익률에 대한 최소 변동성 포트폴리오
                    weights = ef_temp.efficient_return(target_return, market_neutral=False)
                    performance = ef_temp.portfolio_performance(verbose=False, risk_free_rate=0.02)
                    
                    efficient_portfolios.append({
                        "expected_return": round(float(performance[0]), 4),
                        "volatility": round(float(performance[1]), 4),
                        "sharpe_ratio": round(float(performance[2]), 2)
                    })
                    
                except (OptimizationError, cp.error.SolverError):
                    # 최적화 실패 시 건너뛰기
                    continue
            
            # Max Sharpe 포트폴리오 계산
            ef_sharpe = EfficientFrontier(mu, S)
            ef_sharpe.add_constraint(lambda w: cp.sum(w) == 1)
            ef_sharpe.add_constraint(lambda w: w >= 0)
            ef_sharpe.max_sharpe(risk_free_rate=0.02)
            sharpe_performance = ef_sharpe.portfolio_performance(verbose=False, risk_free_rate=0.02)
            
            max_sharpe_point = {
                "expected_return": round(float(sharpe_performance[0]), 4),
                "volatility": round(float(sharpe_performance[1]), 4),
                "sharpe_ratio": round(float(sharpe_performance[2]), 2)
            }
            
            # 개별 자산들 포인트
            individual_assets = []
            for i, ticker in enumerate(mu.index):
                individual_assets.append({
                    "ticker": ticker,
                    "expected_return": round(float(mu.iloc[i]), 4),
                    "volatility": round(float(np.sqrt(S.iloc[i, i])), 4)
                })
            
            return {
                "frontier_points": efficient_portfolios,
                "max_sharpe_point": max_sharpe_point,
                "individual_assets": individual_assets,
                "risk_free_rate": 0.02
            }
            
        except Exception as e:
            logger.warning(f"Efficient Frontier 계산 실패: {e}")
            return {
                "frontier_points": [],
                "max_sharpe_point": None,
                "individual_assets": [],
                "risk_free_rate": 0.02
            }