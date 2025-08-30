import yfinance as yf
import pandas as pd
import numpy as np
from pypfopt import EfficientFrontier, risk_models, expected_returns, objective_functions
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt.exceptions import OptimizationError
import cvxpy as cp
from scipy.optimize import minimize
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PortfolioOptimizationService:
    """Portfolio optimization service using PyPortfolioOpt."""
    
    @staticmethod
    async def fetch_price_data(tickers: List[str], period: str = "1y") -> pd.DataFrame:
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
                
            # 결측값을 이전날 값으로 채움 (forward fill)
            data = data.ffill().dropna()
            
            if data.empty:
                raise ValueError("선택한 종목들의 데이터를 가져올 수 없습니다.")
                
            logger.info(f"Successfully fetched price data for {len(tickers)} tickers, {len(data)} trading days")
            return data
            
        except Exception as e:
            logger.error(f"주가 데이터 가져오기 실패: {e}")
            raise ValueError(f"주가 데이터를 가져올 수 없습니다: {str(e)}")
    
    @staticmethod
    def optimize_portfolio(
        price_data: pd.DataFrame, 
        method: str = "max_sharpe",
        risk_aversion: float = 1.0,
        investment_amount: float = 100000,
        transaction_cost: float = 0.001,
        max_position_size: float = 0.30
    ) -> Dict:
        """포트폴리오 최적화 - 개선된 버전"""
        try:
            # 데이터 검증
            if len(price_data) < 30:
                raise ValueError("최소 30일 이상의 가격 데이터가 필요합니다")
            
            tickers_size = len(price_data.columns)
            if tickers_size <= 3:
                max_position_size = ((100 // tickers_size) + 1) / 100

            # 실제 거래일 수 계산
            trading_days = len(price_data)
            frequency = trading_days  # 실제 연간 거래일 수로 설정
            
            # EWMA span을 실제 데이터 길이에 맞춤 (약 70% 기간 사용)
            ewma_span = max(30, int(trading_days * 0.7))
            
            # 모든 방법에서 CAPM-EWMA 하이브리드 기대 수익률 사용 (CAPM 60% + EWMA 40%)
            try:
                # 시장 벤치마크 데이터 가져오기 (SPY 사용)
                market_data = yf.download("SPY", period="1y", progress=False)['Close']
                market_data = market_data.reindex(price_data.index, method='ffill').dropna()
                
                # CAPM 기대수익률 계산
                capm_mu = expected_returns.capm_return(
                    price_data, 
                    market_prices=market_data, 
                    frequency=frequency,
                    risk_free_rate=0.02
                )
                ewma_mu = expected_returns.ema_historical_return(price_data, frequency=frequency, span=ewma_span)
                
                # 하이브리드 조합 (CAPM 60%, EWMA 40%) - 모든 방법에 적용
                mu = 0.6 * capm_mu + 0.4 * ewma_mu
                logger.info(f"Using CAPM-EWMA hybrid expected returns (60%-40%) for {method} method")
                
            except Exception as capm_error:
                # CAPM 실패 시 EWMA만 사용
                logger.warning(f"CAPM calculation failed: {capm_error}, falling back to EWMA only")
                mu = expected_returns.ema_historical_return(price_data, frequency=frequency, span=ewma_span)
            
            S = risk_models.CovarianceShrinkage(price_data).ledoit_wolf()
            
            # 데이터 품질 검사 및 정제
            # 무한대나 NaN 값 처리
            mu = mu.fillna(mu.mean()).replace([np.inf, -np.inf], mu.mean())
            S = S.fillna(0).replace([np.inf, -np.inf], 0)
            
            # 공분산 행렬의 positive definite 보장
            try:
                eigenvals, eigenvecs = np.linalg.eigh(S)
                eigenvals = np.maximum(eigenvals, 1e-8)  # 작은 양수로 클리핑
                S = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
                S = pd.DataFrame(S, index=price_data.columns, columns=price_data.columns)
            except Exception as e:
                logger.warning(f"Covariance matrix regularization failed: {e}")
                # 대각선 행렬로 폴백
                S = pd.DataFrame(np.diag(np.var(price_data.pct_change().dropna())), 
                        index=price_data.columns, columns=price_data.columns)
            
            # 각 최적화 방법마다 독립적인 EfficientFrontier 인스턴스 사용
            
            # 최적화 방법에 따른 가중치 계산 (더 안전한 방식)
            weights = None
            optimization_ef = None
            
            try:
                if method == "max_sharpe":
                    # Max Sharpe 전용 EF 인스턴스 생성
                    ef_sharpe = EfficientFrontier(mu, S)
                    ef_sharpe.add_constraint(lambda w: cp.sum(w) == 1)
                    ef_sharpe.add_constraint(lambda w: w >= 0.01)
                    ef_sharpe.add_constraint(lambda w: w <= max_position_size)
                    weights = ef_sharpe.max_sharpe(risk_free_rate=0.02)
                    optimization_ef = ef_sharpe
                    
                elif method == "min_volatility":
                    # Min Volatility 전용 EF 인스턴스 생성
                    ef_min_vol = EfficientFrontier(mu, S)
                    ef_min_vol.add_constraint(lambda w: cp.sum(w) == 1)
                    ef_min_vol.add_constraint(lambda w: w >= 0.01)
                    ef_min_vol.add_constraint(lambda w: w <= max_position_size)
                    
                    # 거래비용 고려
                    if transaction_cost > 0:
                        ef_min_vol.add_objective(objective_functions.L2_reg, gamma=transaction_cost)
                        
                    weights = ef_min_vol.min_volatility()
                    optimization_ef = ef_min_vol
                    
                elif method == "risk_parity":
                    # Risk Parity 모델 구현
                    weights = PortfolioOptimizationService._risk_parity_optimization(mu, S, max_position_size)
                    # Risk Parity의 경우 별도로 성과 계산을 위한 EF 인스턴스 생성
                    optimization_ef = EfficientFrontier(mu, S)
                    optimization_ef.add_constraint(lambda w: cp.sum(w) == 1)
                    optimization_ef.add_constraint(lambda w: w >= 0.01)
                    
                    # 거래비용 고려
                    if transaction_cost > 0:
                        optimization_ef.add_objective(objective_functions.L2_reg, gamma=transaction_cost)
                    
                elif method == "efficient_frontier":
                    # Efficient Frontier 전용 EF 인스턴스 생성
                    ef_frontier = EfficientFrontier(mu, S)
                    ef_frontier.add_constraint(lambda w: cp.sum(w) == 1)
                    ef_frontier.add_constraint(lambda w: w >= 0.01)
                    ef_frontier.add_constraint(lambda w: w <= max_position_size)
                    
                    # 거래비용 고려
                    if transaction_cost > 0:
                        ef_frontier.add_objective(objective_functions.L2_reg, gamma=transaction_cost)
                    
                    # 실제 달성 가능한 최대 수익률 계산 (max_sharpe로 계산해보기)
                    try:
                        # 임시 EF 인스턴스로 최대 달성 가능 수익률 확인
                        ef_temp = EfficientFrontier(mu, S)
                        ef_temp.add_constraint(lambda w: cp.sum(w) == 1)
                        ef_temp.add_constraint(lambda w: w >= 0.01)
                        ef_temp.add_constraint(lambda w: w <= max_position_size)
                        temp_weights = ef_temp.max_sharpe(risk_free_rate=0.02)
                        temp_performance = ef_temp.portfolio_performance(verbose=False, risk_free_rate=0.02)
                        max_achievable_return = temp_performance[0] * 0.95  # 95%로 안전마진 설정
                    except:
                        # 계산 실패시 매우 보수적으로 설정
                        max_achievable_return = float(mu.mean()) * 0.8
                    
                    # 더 보수적인 목표 수익률 설정
                    avg_return = float(mu.mean())
                    median_return = float(mu.median())
                    
                    # 여러 후보 중 가장 안전한 값 선택
                    target_candidates = [
                        avg_return * 0.8,           # 평균의 80%
                        median_return * 1.1,        # 중간값의 110%
                        max_achievable_return,      # 달성 가능한 최대값의 95%
                        float(mu.quantile(0.6))     # 60분위수
                    ]
                    
                    conservative_target = min(target_candidates)
                    
                    logger.info(f"Target return candidates: {target_candidates}")
                    logger.info(f"Selected conservative target: {conservative_target}")
                    
                    try:
                        weights = ef_frontier.efficient_return(conservative_target, market_neutral=False)
                    except (OptimizationError, cp.error.SolverError) as e:
                        logger.warning(f"First efficient_return attempt failed: {e}")
                        # 더욱 보수적으로 다시 시도
                        ultra_conservative_target = min(avg_return * 0.6, median_return * 0.9, float(mu.quantile(0.4)))
                        logger.info(f"Falling back to ultra-conservative target: {ultra_conservative_target}")
                        try:
                            weights = ef_frontier.efficient_return(ultra_conservative_target, market_neutral=False)
                        except (OptimizationError, cp.error.SolverError):
                            # 최후의 수단: min_volatility 사용
                            logger.warning("All efficient_return attempts failed, falling back to min_volatility")
                            weights = ef_frontier.min_volatility()
                    
                    optimization_ef = ef_frontier
                    
                else:
                    raise ValueError(f"지원하지 않는 최적화 방법: {method}")
            except (OptimizationError, cp.error.SolverError) as e:
                logger.warning(f"Primary optimization failed: {e}")
                raise e
            
            # 가중치 정제 (소수점 3자리, 최소 임계값 적용)
            if isinstance(weights, dict):
                cleaned_weights = weights
            else:
                cleaned_weights = optimization_ef.clean_weights(cutoff=0.005, rounding=3)
            
            # 성과 지표 계산
            try:
                if method == "risk_parity" or isinstance(weights, dict):
                    # Risk Parity나 dict 형태의 가중치인 경우 수동으로 성과 계산
                    weights_array = np.array([cleaned_weights.get(asset, 0) for asset in mu.index])
                    portfolio_return = np.dot(weights_array, mu)
                    portfolio_vol = np.sqrt(np.dot(weights_array, np.dot(S, weights_array)))
                    sharpe = (portfolio_return - 0.02) / portfolio_vol if portfolio_vol > 0 else 0
                    performance = (portfolio_return, portfolio_vol, sharpe)
                else:
                    performance = optimization_ef.portfolio_performance(verbose=False, risk_free_rate=0.02)
            except Exception as perf_e:
                logger.warning(f"Performance calculation failed: {perf_e}, using fallback calculation")
                # 수동 성과 계산
                weights_array = np.array([cleaned_weights.get(asset, 0) for asset in mu.index])
                portfolio_return = np.dot(weights_array, mu)
                portfolio_vol = np.sqrt(np.dot(weights_array, np.dot(S, weights_array)))
                sharpe = (portfolio_return - 0.02) / portfolio_vol if portfolio_vol > 0 else 0
                performance = (portfolio_return, portfolio_vol, sharpe)
            
            # 유효한 가중치만 반환 (0.5% 이상)
            significant_weights = {k: v for k, v in cleaned_weights.items() if v >= 0.005}
            
            # 가중치 정규화 (합이 정확히 1이 되도록)
            total_weight = sum(significant_weights.values())
            if total_weight > 0:
                significant_weights = {k: v/total_weight for k, v in significant_weights.items()}
            
            # 고급 위험 지표 계산
            portfolio_returns = price_data.pct_change().dropna()
            weights_series = pd.Series(significant_weights).reindex(portfolio_returns.columns, fill_value=0)
            weighted_returns = portfolio_returns.dot(weights_series)
            
            # VaR (Value at Risk) 계산 (실제 데이터 기간에 맞춤)
            var_95 = np.percentile(weighted_returns, 5) * np.sqrt(frequency)  # 연간화
            
            # Sortino Ratio 계산 (하락 변동성만 고려)
            downside_returns = weighted_returns[weighted_returns < 0]
            if len(downside_returns) > 0:
                downside_std = downside_returns.std() * np.sqrt(frequency)
                sortino_ratio = (weighted_returns.mean() * frequency - 0.02) / downside_std if downside_std > 0 else 0
            else:
                sortino_ratio = float('inf')
            
            # Max Drawdown 계산
            cumulative_returns = (1 + weighted_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Calmar Ratio 계산 (연간 수익률 / |최대 낙폭|)
            annual_return = weighted_returns.mean() * frequency
            calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
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
            efficient_frontier_data = PortfolioOptimizationService._calculate_efficient_frontier(
                mu, S
            )
            
            # Stress Test 시나리오 계산
            stress_scenarios = PortfolioOptimizationService._calculate_stress_scenarios(
                weighted_returns, significant_weights, price_data
            )
            
            return {
                "weights": significant_weights,
                "expected_annual_return": round(float(performance[0]), 4),
                "annual_volatility": round(float(performance[1]), 4),
                "sharpe_ratio": round(float(performance[2]), 2),
                "sortino_ratio": round(float(sortino_ratio), 2),
                "max_drawdown": round(float(max_drawdown), 4),
                "calmar_ratio": round(float(calmar_ratio), 2),
                "value_at_risk_95": round(float(var_95), 4),
                "raw_weights": dict(cleaned_weights),
                "discrete_allocation": allocation,
                "leftover_cash": round(float(leftover), 2),
                "correlation_matrix": correlation_matrix,
                "efficient_frontier": efficient_frontier_data,
                "stress_scenarios": stress_scenarios,
                "transaction_cost_impact": round(float(transaction_cost * 100), 2),
                "concentration_limit": round(float(max_position_size * 100), 1)
            }
            
        except (OptimizationError, cp.error.SolverError) as e:
            logger.error(f"최적화 솔버 오류: {e}")
            # 간단한 균등 가중치로 폴백
        except Exception as e:
            logger.error(f"포트폴리오 최적화 실패: {e}")
            raise ValueError(f"포트폴리오 최적화에 실패했습니다: {str(e)}")
    
 
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
            
            # 누적 수익률 계산 (첫날은 0으로 설정)
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
    def _calculate_efficient_frontier(mu, S, num_portfolios=300):
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
    
    @staticmethod
    def _risk_parity_optimization(mu, S, max_position_size):
        """Risk Parity 포트폴리오 최적화"""
        try:
            n_assets = len(mu)
            
            # 초기 균등 가중치
            x0 = np.ones(n_assets) / n_assets
            
            # 제약조건: 가중치 합 = 1, 모든 가중치 >= 0
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0},
                {'type': 'ineq', 'fun': lambda x: x - 0.005},  # 최소 0.5%
                {'type': 'ineq', 'fun': lambda x: max_position_size - x}   # 최대 30%
            ]
            
            # Risk Parity 목적함수 (위험 기여도의 분산 최소화)
            def risk_parity_objective(weights):
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(S, weights)))
                marginal_contrib = np.dot(S, weights) / portfolio_vol
                contrib = weights * marginal_contrib
                target_contrib = portfolio_vol / n_assets
                return np.sum((contrib - target_contrib) ** 2)
            
            result = minimize(
                risk_parity_objective,
                x0,
                method='SLSQP',
                constraints=constraints,
                options={'ftol': 1e-9, 'disp': False}
            )
            
            if result.success:
                return dict(zip(mu.index, result.x))
            else:
                # 폴백: 역변동성 가중
                inv_vol = 1 / np.sqrt(np.diag(S))
                weights = inv_vol / np.sum(inv_vol)
                return dict(zip(mu.index, weights))
                
        except Exception as e:
            logger.warning(f"Risk Parity 최적화 실패: {e}")
            # 균등 가중치로 폴백
            n_assets = len(mu)
            equal_weights = np.ones(n_assets) / n_assets
            return dict(zip(mu.index, equal_weights))
    
    @staticmethod
    def _calculate_stress_scenarios(weighted_returns, weights, price_data):
        """스트레스 테스트 시나리오 계산"""
        try:
            scenarios = {}
            
            # 실제 거래일 수 사용
            frequency = len(price_data)
            
            # 1. 시장 급락 시나리오 (-20%)
            market_crash_returns = weighted_returns * 0.8  # 20% 하락
            scenarios["market_crash"] = {
                "name": "시장 급락 (-20%)",
                "portfolio_return": round(float(market_crash_returns.mean() * frequency), 4),
                "max_drawdown": round(float(market_crash_returns.min()), 4)
            }
            
            # 2. 높은 변동성 시나리오 (변동성 2배)
            high_vol_returns = weighted_returns * 2 - weighted_returns.mean()
            scenarios["high_volatility"] = {
                "name": "고변동성 (변동성 2배)",
                "portfolio_return": round(float(high_vol_returns.mean() * frequency), 4),
                "volatility": round(float(high_vol_returns.std() * np.sqrt(frequency)), 4)
            }
            
            # 3. 금리 급등 시나리오 (채권형 자산 타격)
            returns = price_data.pct_change().dropna()
            correlations = returns.corr()
            
            # 상관관계가 높은 자산들 식별 (0.7 이상)
            high_corr_impact = {}
            for ticker in weights.keys():
                if ticker in correlations.index:
                    avg_corr = correlations[ticker].drop(ticker).mean()
                    impact_factor = 0.9 if avg_corr > 0.7 else 1.0
                    high_corr_impact[ticker] = impact_factor
            
            # 4. 최악의 과거 시나리오 (worst 5% days)
            worst_days = weighted_returns.quantile(0.05)
            scenarios["worst_historical"] = {
                "name": "과거 최악 시나리오 (하위 5%)",
                "worst_day_return": round(float(worst_days), 4),
                "probability": "5%"
            }
            
            return scenarios
            
        except Exception as e:
            logger.warning(f"Stress test 계산 실패: {e}")
            return {}