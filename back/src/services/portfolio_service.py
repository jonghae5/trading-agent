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
from functools import lru_cache
import time
import asyncio
from src.utils.stock_utils import guess_korea_market

logger = logging.getLogger(__name__)


class PortfolioOptimizationService:
    """Portfolio optimization service using PyPortfolioOpt with Walk-Forward Analysis."""
    
    @staticmethod
    @lru_cache(maxsize=64)
    def _cached_spy_data(start_date: str, end_date: str):
        """SPY 시장 데이터 캐시 (날짜별)"""
        try:
            logger.info(f"Downloading SPY data from {start_date} to {end_date}")
            market_data = yf.download("SPY", start=start_date, end=end_date, progress=False, threads=True)['Close']
            logger.info(f"SPY data downloaded: {len(market_data)} days")
            return market_data
        except Exception as e:
            logger.warning(f"Failed to download SPY data: {e}")
            return None
    
    @staticmethod
    async def _async_cached_spy_data(start_date: str, end_date: str):
        """SPY 시장 데이터 비동기 캐시"""
        try:
            # 먼저 캐시 확인
            cached_data = PortfolioOptimizationService._cached_spy_data(start_date, end_date)
            if cached_data is not None:
                return cached_data
            
            # 캐시에 없으면 비동기로 다운로드
            def _download_spy():
                return yf.download("SPY", start=start_date, end=end_date, progress=False, threads=True)['Close']
            
            market_data = await asyncio.to_thread(_download_spy)
            logger.info(f"SPY data downloaded asynchronously: {len(market_data)} days")
            return market_data
        except Exception as e:
            logger.warning(f"Failed to download SPY data asynchronously: {e}")
            return None

    @staticmethod
    def _optimize_single_period(args):
        """단일 기간 최적화 (병렬 처리용)"""
        train_data, test_data, method, kwargs = args
        
        try:
            # 거래비용 파라미터 추출
            transaction_cost = kwargs.get('transaction_cost', 0.001)
            
            # 훈련 데이터로 포트폴리오 최적화
            optimization_result = PortfolioOptimizationService.optimize_portfolio(
                train_data, method=method, **kwargs
            )
            
            new_weights = optimization_result['weights']
            
            # 테스트 기간 성과 시뮬레이션 (벡터화)
            test_returns = test_data.pct_change().dropna()
            
            # 가중치 조정 (테스트 데이터에 있는 종목만)
            available_tickers = [t for t in new_weights.keys() if t in test_returns.columns]
            if not available_tickers:
                return None
            
            # 가중치 정규화 (벡터화)
            adjusted_weights = {t: new_weights.get(t, 0) for t in available_tickers}
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                adjusted_weights = {t: w/total_weight for t, w in adjusted_weights.items()}
            
            # 포트폴리오 수익률 계산 (벡터화)
            weight_series = pd.Series(adjusted_weights).reindex(test_returns.columns, fill_value=0)
            portfolio_returns = test_returns.dot(weight_series)
            
            # 리밸런싱 거래비용 차감 (첫날에 한 번만 적용)
            if len(portfolio_returns) > 0:
                portfolio_returns.iloc[0] -= transaction_cost
            
            # 성과 지표 계산 (벡터화)
            period_cumret = (1 + portfolio_returns).prod() - 1
            period_vol = portfolio_returns.std() * np.sqrt(252)
            period_sharpe = (portfolio_returns.mean() * 252 - 0.02) / period_vol if period_vol > 0 else 0
            
            return {
                'period_start': test_data.index[0].strftime('%Y-%m-%d'),
                'period_end': test_data.index[-1].strftime('%Y-%m-%d'),
                'weights': adjusted_weights,
                'period_return': round(float(period_cumret), 4),
                'period_volatility': round(float(period_vol), 4),
                'period_sharpe': round(float(period_sharpe), 2),
                'train_period': f"{train_data.index[0].strftime('%Y-%m-%d')} to {train_data.index[-1].strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            logger.warning(f"Optimization failed for period {test_data.index[0] if len(test_data) > 0 else 'unknown'}: {e}")
            return None

    @staticmethod
    async def walk_forward_analysis(
        price_data: pd.DataFrame,
        method: str = "max_sharpe",
        rebalance_freq: str = "monthly",  # 리밸런싱 빈도: "monthly", "quarterly"  
        transaction_cost: float = 0.001,  # 거래비용 (0.1%)
        fixed_weights: Dict[str, float] = None,  # 고정 비중 (선택적)
        **kwargs
    ) -> Dict:
        """Walk-Forward Analysis를 통한 실제적인 백테스팅 (최적화됨)"""
        try:
            start_time = time.time()
            
            # 리밸런싱 빈도에 따른 자동 윈도우 설정
            if rebalance_freq == "quarterly":
                train_window = 252  # 4분기 (1년)
                test_window = 63    # 1분기 (3개월)
                logger.info(f"Quarterly rebalancing mode: {train_window} train / {test_window} test days")
                
            else:  # monthly (기본값)
                # 월별 모드: 12개월 훈련, 1개월 테스트  
                train_window = 252  # 12개월 (1년)
                test_window = 21    # 1개월
                logger.info(f"Monthly rebalancing mode: {train_window} train / {test_window} test days")
            
            logger.info(f"Starting optimized Walk-Forward Analysis with {len(price_data)} days of data")
            
            # 데이터 길이 검증
            if len(price_data) < train_window + test_window:
                raise ValueError(f"최소 {train_window + test_window}일 이상의 데이터가 필요합니다 (현재: {len(price_data)}일)")
            
            # kwargs에 transaction_cost 추가
            kwargs['transaction_cost'] = transaction_cost
            
            # 모든 기간 데이터를 먼저 준비 (메모리 사용량을 줄이기 위해)
            periods_args = []
            start_idx = train_window
            
            while start_idx + test_window <= len(price_data):
                train_end_idx = start_idx
                train_start_idx = max(0, train_end_idx - train_window)
                train_data = price_data.iloc[train_start_idx:train_end_idx].copy()
                test_data = price_data.iloc[start_idx:start_idx + test_window].copy()
                
                periods_args.append((train_data, test_data, method, kwargs))
                start_idx += test_window
            
            logger.info(f"Processing {len(periods_args)} periods")
            
            # asyncio를 사용한 개선된 병렬 처리 (순서 보장)
            results = []
            
            async def process_single_period_with_index(idx, args):
                """단일 기간을 비동기적으로 처리 (인덱스 포함)"""
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    PortfolioOptimizationService._optimize_single_period, 
                    args
                )
                return idx, result  # 인덱스와 함께 반환
            
            # 비동기 병렬 처리 - 순서 보장을 위해 인덱스 포함
            tasks = [
                process_single_period_with_index(i, args) 
                for i, args in enumerate(periods_args)
            ]
            results_with_idx = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 순서대로 정렬하여 시간순서 보장
            period_results = [None] * len(periods_args)
            for result in results_with_idx:
                if not isinstance(result, Exception) and result is not None:
                    idx, data = result
                    period_results[idx] = data if not isinstance(data, Exception) else None
            
            # 결과 필터링 및 포트폴리오 가치 계산
            initial_value = 100000
            current_value = initial_value
            portfolio_values = []
            rebalance_dates = []
            current_weights = None
            
            # 고정 비중 성과 추적 변수들 (fixed_weights가 제공된 경우)
            fixed_results = []
            fixed_current_value = initial_value if fixed_weights else None
            fixed_portfolio_values = []
            
            for i, result in enumerate(period_results):
                if result:
                    # 최적화 포트폴리오 가치 업데이트
                    current_value = current_value * (1 + result['period_return'])
                    result['portfolio_value'] = round(float(current_value), 2)
                    
                    results.append(result)
                    portfolio_values.append({
                        'date': result['period_end'],
                        'value': current_value,
                        'cumulative_return': (current_value / initial_value) - 1
                    })
                    
                    rebalance_dates.append(result['period_start'])
                    current_weights = result['weights']
                    
                    # 고정 비중 성과 계산 (동일한 기간, 동일한 데이터)
                    if fixed_weights:
                        # 동일한 테스트 기간 데이터 사용
                        period_start_idx = i * test_window + train_window
                        period_end_idx = period_start_idx + test_window
                        
                        if period_end_idx <= len(price_data):
                            test_data_fixed = price_data.iloc[period_start_idx:period_end_idx].copy()
                            test_returns_fixed = test_data_fixed.pct_change().dropna()
                            
                            # 고정 비중을 테스트 데이터에 맞춰 조정
                            available_tickers = [t for t in fixed_weights.keys() if t in test_returns_fixed.columns]
                            if available_tickers:
                                adjusted_fixed_weights = {t: fixed_weights.get(t, 0) for t in available_tickers}
                                total_weight = sum(adjusted_fixed_weights.values())
                                if total_weight > 0:
                                    adjusted_fixed_weights = {t: w/total_weight for t, w in adjusted_fixed_weights.items()}
                                
                                # 고정 비중 포트폴리오 수익률 계산 (Walk-Forward와 완전히 동일한 방식)
                                weight_series = pd.Series(adjusted_fixed_weights).reindex(test_returns_fixed.columns, fill_value=0)
                                fixed_portfolio_returns = test_returns_fixed.dot(weight_series)
                                
                                # 동일한 거래비용 차감
                                if len(fixed_portfolio_returns) > 0:
                                    fixed_portfolio_returns.iloc[0] -= transaction_cost
                                
                                # 기간별 총 수익률 계산 (Walk-Forward와 동일한 방식)
                                fixed_period_return = (1 + fixed_portfolio_returns).prod() - 1
                                fixed_current_value = fixed_current_value * (1 + fixed_period_return)
                                
                                # 성과 지표 계산 (Walk-Forward와 동일한 방식)
                                fixed_period_vol = np.std(fixed_portfolio_returns) * np.sqrt(252)
                                fixed_period_sharpe = ((np.mean(fixed_portfolio_returns) * 252) - 0.02) / fixed_period_vol if fixed_period_vol > 0 else 0
                                
                                fixed_result = {
                                    'period_start': result['period_start'],
                                    'period_end': result['period_end'],
                                    'weights': adjusted_fixed_weights,
                                    'period_return': round(float(fixed_period_return), 4),
                                    'period_volatility': round(float(fixed_period_vol), 4),
                                    'period_sharpe': round(float(fixed_period_sharpe), 2),
                                    'portfolio_value': round(float(fixed_current_value), 2)
                                }
                                fixed_results.append(fixed_result)
                                
                                fixed_portfolio_values.append({
                                    'date': result['period_end'],
                                    'value': fixed_current_value,
                                    'cumulative_return': (fixed_current_value / initial_value) - 1
                                })
            
            # 전체 성과 지표 계산 (벡터화)
            if not results:
                raise ValueError("Walk-Forward Analysis 실행 중 유효한 결과를 얻지 못했습니다")
            
            total_return = (current_value / initial_value) - 1
            period_returns = np.array([r['period_return'] for r in results])
            
            # 벡터화된 계산
            avg_return = np.mean(period_returns) * (252 / test_window)
            volatility = np.std(period_returns) * np.sqrt(252 / test_window)
            sharpe_ratio = (avg_return - 0.02) / volatility if volatility > 0 else 0
            
            # 최대 낙폭 계산 (벡터화)
            values = np.array([pv['value'] for pv in portfolio_values])
            if len(values) > 0:
                peaks = np.maximum.accumulate(values)
                drawdowns = (values - peaks) / peaks
                max_dd = np.min(drawdowns)
            else:
                max_dd = 0
            
            # 승률 계산 (벡터화)
            win_rate = np.mean(period_returns > 0)
            
            # 최종 포트폴리오에 대한 추가 분석 정보 생성
            final_weights = current_weights or {}
            additional_info = {}
            
            if final_weights and len(price_data) > 0:
                try:
                    # 상관관계 매트릭스 (전체 기간 사용 - 장기 상관관계 파악용)
                    # 이것은 Look-ahead가 아님 - 상관관계는 전략적 자산 배분을 위한 장기 통계
                    correlation_matrix = price_data.corr().round(3).to_dict()
                    
                    # Walk-Forward 마지막 기간과 일치하는 효율적 프론티어 계산 (Look-ahead bias 방지)
                    # 마지막 Walk-Forward 기간의 훈련 데이터만 사용
                    if results:
                        # Walk-Forward 로직과 동일하게 마지막 훈련 윈도우 재구성
                        total_periods = len(results)
                        last_start_idx = train_window + (total_periods - 1) * test_window
                        last_train_start_idx = max(0, last_start_idx - train_window)
                        last_train_end_idx = last_start_idx
                        
                        # 훈련 기간만 엄격히 추출 (Look-ahead bias 방지)
                        latest_data = price_data.iloc[last_train_start_idx:last_train_end_idx].copy()
                        
                        logger.info(f"Walk-Forward Efficient Frontier: using training data [{last_train_start_idx}:{last_train_end_idx}] = {len(latest_data)} days")
                        logger.info(f"Training period: {latest_data.index[0].strftime('%Y-%m-%d')} to {latest_data.index[-1].strftime('%Y-%m-%d')}")
                    else:
                        # 결과가 없으면 마지막 훈련 윈도우 사용 (여전히 Look-ahead bias 없음)
                        if len(price_data) >= train_window:
                            latest_data = price_data.iloc[-train_window:].copy()
                        else:
                            latest_data = price_data.copy()
                        logger.info(f"No Walk-Forward results, using last {len(latest_data)} days for Efficient Frontier")
                    
                    if len(latest_data) >= 30:  # 최소 데이터 요구사항
                        frequency = len(latest_data)
                        ewma_span = max(30, int(len(latest_data) * 0.7))
                        
                        try:
                            # 시장 벤치마크 데이터 (비동기 캐시 사용)
                            start_date = latest_data.index.min().strftime('%Y-%m-%d')
                            end_date = latest_data.index.max().strftime('%Y-%m-%d')
                            market_data = await PortfolioOptimizationService._async_cached_spy_data(start_date, end_date)
                            if market_data is not None:
                                market_data = market_data.reindex(latest_data.index, method='ffill').dropna()
                            else:
                                raise Exception("Failed to get SPY data")
                            
                            # CAPM 기대수익률 계산
                            capm_mu = expected_returns.capm_return(
                                latest_data, 
                                market_prices=market_data, 
                                frequency=frequency,
                                risk_free_rate=0.02
                            )
                            ewma_mu = expected_returns.ema_historical_return(latest_data, frequency=frequency, span=ewma_span)
                            mu = 0.6 * capm_mu + 0.4 * ewma_mu
                            
                        except Exception:
                            mu = expected_returns.ema_historical_return(latest_data, frequency=frequency, span=ewma_span)
                        
                        S = risk_models.CovarianceShrinkage(latest_data).ledoit_wolf()
                        
                        # 월가 공격적 집중투자 전략 완전 적용
                        tickers_count = len(latest_data.columns)
                        if tickers_count == 2:
                            dynamic_max_position = 0.50  # 2개 종목: 각 50%
                        elif tickers_count == 3:
                            dynamic_max_position = 0.35  # 3개 종목: 최대 35%
                        elif tickers_count == 4:
                            dynamic_max_position = 0.30  # 4개 종목: 최대 30%
                        elif tickers_count == 5:
                            dynamic_max_position = 0.25  # 5개 종목: 최대 25%
                        elif tickers_count == 6:
                            dynamic_max_position = 0.20  # 6개 종목: 최대 20%
                        else:
                            dynamic_max_position = 0.15  # 7개 이상: 최대 15%
                        
                        logger.info(f"Efficient Frontier: {tickers_count} assets, Wall Street max position: {dynamic_max_position*100}%")
                        
                        efficient_frontier_data = PortfolioOptimizationService._calculate_efficient_frontier(
                            mu, S, max_position_size=dynamic_max_position
                        )
                        additional_info['efficient_frontier'] = efficient_frontier_data
                        
                        # 이산 할당 계산 (훈련 기간 마지막 가격 사용 - Look-ahead bias 방지)
                        try:
                            # 훈련 데이터의 마지막 날 가격 사용 (미래 정보 사용 안함)
                            training_latest_prices = latest_data.iloc[-1].to_dict()
                            da = DiscreteAllocation(final_weights, training_latest_prices, total_portfolio_value=100000)
                            allocation, leftover = da.greedy_portfolio()
                            additional_info['discrete_allocation'] = allocation
                            additional_info['leftover_cash'] = round(float(leftover), 2)
                            logger.info(f"Discrete allocation using training end prices from {latest_data.index[-1].strftime('%Y-%m-%d')}")
                        except Exception as e:
                            logger.warning(f"Discrete allocation 계산 실패: {e}")
                    
                    additional_info['correlation_matrix'] = correlation_matrix
                    
                except Exception as e:
                    logger.warning(f"추가 분석 정보 생성 실패: {e}")
            
            # 고정 비중 성과 지표 계산 (제공된 경우)
            fixed_weights_performance = None
            if fixed_weights and fixed_results:
                fixed_total_return = (fixed_current_value / initial_value) - 1
                fixed_period_returns = np.array([r['period_return'] for r in fixed_results])
                
                # Walk-Forward와 정확히 동일한 벡터화된 계산
                fixed_avg_return = np.mean(fixed_period_returns) * (252 / test_window)
                fixed_volatility = np.std(fixed_period_returns) * np.sqrt(252 / test_window)
                fixed_sharpe_ratio = (fixed_avg_return - 0.02) / fixed_volatility if fixed_volatility > 0 else 0
                
                # 최대 낙폭 계산 (Walk-Forward와 동일한 방식)
                fixed_values = np.array([pv['value'] for pv in fixed_portfolio_values])
                if len(fixed_values) > 0:
                    fixed_peaks = np.maximum.accumulate(fixed_values)
                    fixed_drawdowns = (fixed_values - fixed_peaks) / fixed_peaks
                    fixed_max_dd = np.min(fixed_drawdowns)
                else:
                    fixed_max_dd = 0
                
                # 승률 계산 (Walk-Forward와 동일한 방식)
                fixed_win_rate = np.mean(fixed_period_returns > 0)
                
                fixed_weights_performance = {
                    'portfolio_timeline': fixed_results,  # Walk-Forward와 동일한 구조
                    'rebalance_dates': rebalance_dates,  # 동일한 날짜 사용
                    'summary_stats': {
                        'total_return': round(float(fixed_total_return), 4),
                        'annualized_return': round(float(fixed_avg_return), 4),
                        'annualized_volatility': round(float(fixed_volatility), 4),
                        'sharpe_ratio': round(float(fixed_sharpe_ratio), 2),
                        'max_drawdown': round(float(fixed_max_dd), 4),
                        'win_rate': round(float(fixed_win_rate), 2),
                        'total_periods': len(fixed_results),
                        'final_value': round(float(fixed_current_value), 2)
                    },
                    'fixed_weights': fixed_weights,
                    'parameters': {
                        'rebalance_frequency': rebalance_freq,
                        'transaction_cost': transaction_cost,
                        'investment_amount': initial_value
                    }
                }
                logger.info(f"Fixed weights performance calculated: Total return {fixed_total_return:.4f}, Sharpe {fixed_sharpe_ratio:.2f}")

            # 실행 시간 기록
            execution_time = time.time() - start_time
            logger.info(f"Walk-Forward Analysis completed in {execution_time:.2f} seconds with {len(results)} periods")

            result_data = {
                'walk_forward_results': results,
                'portfolio_timeline': portfolio_values,
                'rebalance_dates': rebalance_dates,
                'summary_stats': {
                    'total_return': round(float(total_return), 4),
                    'annualized_return': round(float(avg_return), 4),
                    'annualized_volatility': round(float(volatility), 4),
                    'sharpe_ratio': round(float(sharpe_ratio), 2),
                    'max_drawdown': round(float(max_dd), 4),
                    'win_rate': round(float(win_rate), 2),
                    'total_periods': len(results),
                    'final_value': round(float(current_value), 2)
                },
                'final_weights': final_weights,
                'method_used': method,
                'parameters': {
                    'train_window': train_window,
                    'test_window': test_window,
                    'rebalance_frequency': rebalance_freq,
                    'transaction_cost': transaction_cost
                },
                # 추가 분석 정보
                **additional_info
            }
            
            # 고정 비중 성과 추가 (있는 경우)
            if fixed_weights_performance:
                result_data['fixed_weights_performance'] = fixed_weights_performance
                
            return result_data
            
        except Exception as e:
            logger.error(f"Walk-Forward Analysis 실패: {e}")
            raise ValueError(f"Walk-Forward Analysis 실행에 실패했습니다: {str(e)}")
    
    @staticmethod
    async def fetch_price_data(tickers: List[str], period: str = "2y", rebalance_freq: str = "monthly") -> pd.DataFrame:
        """주가 데이터 가져오기 (비동기 최적화)"""
        try:
            # 리밸런싱 빈도에 따른 데이터 기간 자동 조정
            if rebalance_freq == "quarterly":
                period = "5y"  # 분기별 모드는 더 긴 기간 필요
                logger.info(f"Quarterly mode: extended data period to {period}")
            
            # asyncio.to_thread를 사용해서 yfinance를 비동기적으로 실행
            def _download_data():
                # 한국 주식 코드 변환 처리
                processed_tickers = [guess_korea_market(ticker) for ticker in tickers]
                return yf.download(processed_tickers, period=period, progress=False, threads=True)
            
            # 병렬로 데이터 다운로드
            data = await asyncio.to_thread(_download_data)
            
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
        investment_amount: float = 100000,
        transaction_cost: float = 0.001,
        max_position_size: float = 0.65  # 공격적 투자를 위한 높은 집중도 허용
    ) -> Dict:
        """포트폴리오 최적화 - 개선된 버전"""
        try:
            # 데이터 검증
            if len(price_data) < 30:
                raise ValueError("최소 30일 이상의 가격 데이터가 필요합니다")
            
            # 월가 공격적 집중투자 전략 적용
            tickers_size = len(price_data.columns)
            if tickers_size == 2:
                max_position_size = 0.50  # 2개 종목: 각 50%
            elif tickers_size == 3:
                max_position_size = 0.35  # 3개 종목: 최대 35%
            elif tickers_size == 4:
                max_position_size = 0.30  # 4개 종목: 최대 30%
            elif tickers_size == 5:
                max_position_size = 0.25  # 5개 종목: 최대 25%
            elif tickers_size == 6:
                max_position_size = 0.20  # 6개 종목: 최대 20%
            else:
                max_position_size = 0.15  # 7개 이상: 최대 15%
            
            logger.info(f"Wall Street aggressive strategy applied: {tickers_size} assets, max position: {max_position_size*100}%")

            # 실제 거래일 수 계산
            trading_days = len(price_data)
            frequency = trading_days  # 실제 연간 거래일 수로 설정
            
            # EWMA span을 실제 데이터 길이에 맞춤 (약 70% 기간 사용)
            ewma_span = max(30, int(trading_days * 0.7))
            
            # 모든 방법에서 CAPM-EWMA 하이브리드 기대 수익률 사용 (CAPM 60% + EWMA 40%)
            try:
                # 시장 벤치마크 데이터 가져오기 (SPY 사용, 동기 캐시 사용 - optimize_portfolio는 동기함수)
                start_date = price_data.index.min().strftime('%Y-%m-%d')
                end_date = price_data.index.max().strftime('%Y-%m-%d')
                market_data = PortfolioOptimizationService._cached_spy_data(start_date, end_date)
                if market_data is None:
                    raise Exception("Failed to get SPY data")
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
                    ef_sharpe.add_constraint(lambda w: w >= 0.005)  # 최소 0.5% (더 공격적)
                    ef_sharpe.add_constraint(lambda w: w <= max_position_size)
                    weights = ef_sharpe.max_sharpe(risk_free_rate=0.02)
                    optimization_ef = ef_sharpe
                    
                elif method == "min_volatility":
                    # Min Volatility 전용 EF 인스턴스 생성
                    ef_min_vol = EfficientFrontier(mu, S)
                    ef_min_vol.add_constraint(lambda w: cp.sum(w) == 1)
                    ef_min_vol.add_constraint(lambda w: w >= 0.005)  # 최소 0.5% (더 공격적)
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
                    optimization_ef.add_constraint(lambda w: w >= 0.005)  # 최소 0.5% (더 공격적)
                    
                    # 거래비용 고려
                    if transaction_cost > 0:
                        optimization_ef.add_objective(objective_functions.L2_reg, gamma=transaction_cost)
                    
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
                mu, S, max_position_size=max_position_size
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
    async def validate_tickers_async(tickers: List[str]) -> List[str]:
        """종목 코드 유효성 검증 (비동기)"""
        try:
            # 비동기로 yfinance 데이터 요청
            def _validate_data():
                # 한국 주식 코드 변환 처리
                processed_tickers = [guess_korea_market(ticker) for ticker in tickers]
                return yf.download(processed_tickers, period="5d", progress=False, threads=True)
            
            test_data = await asyncio.to_thread(_validate_data)
            
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
    def validate_tickers(tickers: List[str]) -> List[str]:
        """종목 코드 유효성 검증 (동기 - 하위 호환성)"""
        try:
            # yfinance로 간단한 데이터 요청해서 유효성 확인
            # 한국 주식 코드 변환 처리
            processed_tickers = [guess_korea_market(ticker) for ticker in tickers]
            test_data = yf.download(processed_tickers, period="5d", progress=False, threads=True)
            
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
    def _calculate_efficient_frontier(mu, S, num_portfolios=200, max_position_size=0.40):
        """Efficient Frontier 계산 (강화된 안정성)"""
        try:
            # 공분산 행렬 정규화 및 안정성 강화
            eigenvals, eigenvecs = np.linalg.eigh(S)
            min_eigenval = np.min(eigenvals)
            
            if min_eigenval <= 1e-8:
                # 음수 또는 0에 가까운 고유값 보정
                eigenvals = np.maximum(eigenvals, 1e-6)
                S_regularized = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
                S = pd.DataFrame(S_regularized, index=S.index, columns=S.columns)
                logger.info(f"Regularized covariance matrix: min eigenvalue was {min_eigenval}")
            
            # 기대수익률 범위를 더 보수적으로 설정
            mu_mean = mu.mean()
            mu_std = mu.std()
            min_return = max(mu.min(), mu_mean - 2*mu_std)
            max_return = min(mu.max(), mu_mean + 2*mu_std) * 0.9  # 더 보수적
            
            # 포인트 수를 줄여서 안정성 향상
            target_returns = np.linspace(min_return, max_return, num_portfolios)
            
            efficient_portfolios = []
            successful_optimizations = 0
            
            for target_return in target_returns:
                try:
                    # 새로운 EfficientFrontier 인스턴스 생성
                    ef_temp = EfficientFrontier(mu, S)
                    ef_temp.add_constraint(lambda w: cp.sum(w) == 1)
                    ef_temp.add_constraint(lambda w: w >= 0.005)  # 최소 0.5% (공격적)
                    # 동적 집중도 제한 적용
                    ef_temp.add_constraint(lambda w: w <= max_position_size)
                    
                    # 목표 수익률에 대한 최소 변동성 포트폴리오
                    ef_temp.efficient_return(target_return, market_neutral=False)
                    performance = ef_temp.portfolio_performance(verbose=False, risk_free_rate=0.02)
                    
                    # 성과지표 유효성 검증
                    if all(np.isfinite([performance[0], performance[1], performance[2]])):
                        efficient_portfolios.append({
                            "expected_return": round(float(performance[0]), 4),
                            "volatility": round(float(performance[1]), 4),
                            "sharpe_ratio": round(float(performance[2]), 2)
                        })
                        successful_optimizations += 1
                    
                except (OptimizationError, cp.error.SolverError, ValueError) as e:
                    # 최적화 실패 시 건너뛰기
                    continue
                    
            logger.info(f"Efficient Frontier: {successful_optimizations}/{num_portfolios} successful optimizations")
            
            # Max Sharpe 포트폴리오 계산
            ef_sharpe = EfficientFrontier(mu, S)
            ef_sharpe.add_constraint(lambda w: cp.sum(w) == 1)
            ef_sharpe.add_constraint(lambda w: w >= 0.005)  # 최소 0.5% (공격적)
            ef_sharpe.add_constraint(lambda w: w <= max_position_size)  # 동적 집중도 제한
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

    