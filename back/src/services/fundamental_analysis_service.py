"""Fundamental analysis service using yfinance for financial data."""

import logging
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import warnings
from src.models.base import get_kst_now

warnings.filterwarnings('ignore', category=FutureWarning)

logger = logging.getLogger(__name__)


@dataclass
class FinancialRatio:
    """Financial ratio data."""
    name: str
    value: float
    industry_avg: Optional[float]
    rating: str  # 'excellent', 'good', 'average', 'poor', 'very_poor'
    description: str


@dataclass
class ValuationMetric:
    """Valuation metric data."""
    name: str
    value: float
    fair_value_estimate: Optional[float]
    rating: str
    description: str


@dataclass
class GrowthMetric:
    """Growth metric data."""
    name: str
    current_value: float
    historical_avg: float
    trend: str  # 'accelerating', 'stable', 'declining'
    description: str


@dataclass
class FundamentalAnalysisResult:
    """Complete fundamental analysis result."""
    ticker: str
    company_name: str
    timestamp: datetime
    current_price: float
    market_cap: float
    
    # Valuation metrics
    valuation_metrics: List[ValuationMetric]
    
    # Financial ratios
    financial_ratios: List[FinancialRatio]
    
    # Growth metrics
    growth_metrics: List[GrowthMetric]
    
    # Overall assessment
    overall_rating: str  # 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'
    confidence: float
    fair_value: float
    upside_potential: float
    
    # Risk factors
    risk_factors: List[str]
    strengths: List[str]


class FundamentalAnalysisService:
    """Fundamental analysis service."""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 3600  # 1 hour
    
    def _get_cache_key(self, ticker: str) -> str:
        """Generate cache key."""
        return f"fundamental_{ticker}_{get_kst_now().strftime('%Y%m%d%H')}"
    
    def _is_cache_valid(self, cache_time: datetime) -> bool:
        """Check if cache is still valid."""
        return get_kst_now() - cache_time < timedelta(seconds=self.cache_duration)
    
    async def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive stock information."""
        try:
            loop = asyncio.get_event_loop()
            stock = await loop.run_in_executor(None, lambda: yf.Ticker(ticker))
            
            info = await loop.run_in_executor(None, lambda: stock.info)
            financials = await loop.run_in_executor(None, lambda: stock.financials)
            balance_sheet = await loop.run_in_executor(None, lambda: stock.balance_sheet)
            cash_flow = await loop.run_in_executor(None, lambda: stock.cashflow)
            
            return {
                'info': info,
                'financials': financials,
                'balance_sheet': balance_sheet,
                'cash_flow': cash_flow
            }
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {ticker}: {e}")
            raise
    
    def calculate_valuation_metrics(self, info: Dict[str, Any], financials: pd.DataFrame) -> List[ValuationMetric]:
        """Calculate valuation metrics."""
        metrics = []
        
        try:
            current_price = info.get('currentPrice', 0)
            market_cap = info.get('marketCap', 0)
            shares_outstanding = info.get('sharesOutstanding', 0)
            
            # P/E Ratio
            pe_ratio = info.get('trailingPE')
            if pe_ratio:
                if pe_ratio < 10:
                    pe_rating = 'excellent'
                elif pe_ratio < 15:
                    pe_rating = 'good'
                elif pe_ratio < 25:
                    pe_rating = 'average'
                elif pe_ratio < 35:
                    pe_rating = 'poor'
                else:
                    pe_rating = 'very_poor'
                
                metrics.append(ValuationMetric(
                    name='P/E Ratio',
                    value=pe_ratio,
                    fair_value_estimate=None,
                    rating=pe_rating,
                    description=f'Trading at {pe_ratio:.2f}x earnings'
                ))
            
            # P/B Ratio
            pb_ratio = info.get('priceToBook')
            if pb_ratio:
                if pb_ratio < 1:
                    pb_rating = 'excellent'
                elif pb_ratio < 2:
                    pb_rating = 'good'
                elif pb_ratio < 3:
                    pb_rating = 'average'
                elif pb_ratio < 5:
                    pb_rating = 'poor'
                else:
                    pb_rating = 'very_poor'
                
                metrics.append(ValuationMetric(
                    name='P/B Ratio',
                    value=pb_ratio,
                    fair_value_estimate=None,
                    rating=pb_rating,
                    description=f'Trading at {pb_ratio:.2f}x book value'
                ))
            
            # P/S Ratio
            revenue_per_share = info.get('revenuePerShare')
            if revenue_per_share and current_price:
                ps_ratio = current_price / revenue_per_share
                
                if ps_ratio < 1:
                    ps_rating = 'excellent'
                elif ps_ratio < 3:
                    ps_rating = 'good'
                elif ps_ratio < 6:
                    ps_rating = 'average'
                elif ps_ratio < 10:
                    ps_rating = 'poor'
                else:
                    ps_rating = 'very_poor'
                
                metrics.append(ValuationMetric(
                    name='P/S Ratio',
                    value=ps_ratio,
                    fair_value_estimate=None,
                    rating=ps_rating,
                    description=f'Trading at {ps_ratio:.2f}x revenue'
                ))
            
            # EV/EBITDA
            enterprise_value = info.get('enterpriseValue')
            ebitda = info.get('ebitda')
            if enterprise_value and ebitda and ebitda > 0:
                ev_ebitda = enterprise_value / ebitda
                
                if ev_ebitda < 10:
                    ev_rating = 'excellent'
                elif ev_ebitda < 15:
                    ev_rating = 'good'
                elif ev_ebitda < 20:
                    ev_rating = 'average'
                elif ev_ebitda < 30:
                    ev_rating = 'poor'
                else:
                    ev_rating = 'very_poor'
                
                metrics.append(ValuationMetric(
                    name='EV/EBITDA',
                    value=ev_ebitda,
                    fair_value_estimate=None,
                    rating=ev_rating,
                    description=f'Enterprise value is {ev_ebitda:.2f}x EBITDA'
                ))
            
            # PEG Ratio
            peg_ratio = info.get('pegRatio')
            if peg_ratio:
                if peg_ratio < 0.5:
                    peg_rating = 'excellent'
                elif peg_ratio < 1:
                    peg_rating = 'good'
                elif peg_ratio < 1.5:
                    peg_rating = 'average'
                elif peg_ratio < 2:
                    peg_rating = 'poor'
                else:
                    peg_rating = 'very_poor'
                
                metrics.append(ValuationMetric(
                    name='PEG Ratio',
                    value=peg_ratio,
                    fair_value_estimate=None,
                    rating=peg_rating,
                    description=f'P/E relative to growth rate: {peg_ratio:.2f}'
                ))
            
        except Exception as e:
            logger.error(f"Error calculating valuation metrics: {e}")
        
        return metrics
    
    def calculate_financial_ratios(self, info: Dict[str, Any], balance_sheet: pd.DataFrame, 
                                  financials: pd.DataFrame) -> List[FinancialRatio]:
        """Calculate financial strength ratios."""
        ratios = []
        
        try:
            # Current Ratio
            current_ratio = info.get('currentRatio')
            if current_ratio:
                if current_ratio > 2:
                    current_rating = 'excellent'
                elif current_ratio > 1.5:
                    current_rating = 'good'
                elif current_ratio > 1:
                    current_rating = 'average'
                elif current_ratio > 0.8:
                    current_rating = 'poor'
                else:
                    current_rating = 'very_poor'
                
                ratios.append(FinancialRatio(
                    name='Current Ratio',
                    value=current_ratio,
                    industry_avg=None,
                    rating=current_rating,
                    description=f'Can cover short-term debts {current_ratio:.2f}x over'
                ))
            
            # Quick Ratio
            quick_ratio = info.get('quickRatio')
            if quick_ratio:
                if quick_ratio > 1.5:
                    quick_rating = 'excellent'
                elif quick_ratio > 1:
                    quick_rating = 'good'
                elif quick_ratio > 0.8:
                    quick_rating = 'average'
                elif quick_ratio > 0.5:
                    quick_rating = 'poor'
                else:
                    quick_rating = 'very_poor'
                
                ratios.append(FinancialRatio(
                    name='Quick Ratio',
                    value=quick_ratio,
                    industry_avg=None,
                    rating=quick_rating,
                    description=f'Liquid assets can cover debts {quick_ratio:.2f}x over'
                ))
            
            # Debt-to-Equity Ratio
            debt_to_equity = info.get('debtToEquity')
            if debt_to_equity:
                debt_to_equity = debt_to_equity / 100  # Convert percentage to ratio
                
                if debt_to_equity < 0.3:
                    debt_rating = 'excellent'
                elif debt_to_equity < 0.6:
                    debt_rating = 'good'
                elif debt_to_equity < 1:
                    debt_rating = 'average'
                elif debt_to_equity < 2:
                    debt_rating = 'poor'
                else:
                    debt_rating = 'very_poor'
                
                ratios.append(FinancialRatio(
                    name='Debt-to-Equity',
                    value=debt_to_equity,
                    industry_avg=None,
                    rating=debt_rating,
                    description=f'Debt is {debt_to_equity:.2f}x equity'
                ))
            
            # Return on Equity (ROE)
            roe = info.get('returnOnEquity')
            if roe:
                roe_percent = roe * 100
                
                if roe_percent > 20:
                    roe_rating = 'excellent'
                elif roe_percent > 15:
                    roe_rating = 'good'
                elif roe_percent > 10:
                    roe_rating = 'average'
                elif roe_percent > 5:
                    roe_rating = 'poor'
                else:
                    roe_rating = 'very_poor'
                
                ratios.append(FinancialRatio(
                    name='Return on Equity',
                    value=roe_percent,
                    industry_avg=None,
                    rating=roe_rating,
                    description=f'Generates {roe_percent:.1f}% return on shareholder equity'
                ))
            
            # Return on Assets (ROA)
            roa = info.get('returnOnAssets')
            if roa:
                roa_percent = roa * 100
                
                if roa_percent > 10:
                    roa_rating = 'excellent'
                elif roa_percent > 7:
                    roa_rating = 'good'
                elif roa_percent > 4:
                    roa_rating = 'average'
                elif roa_percent > 2:
                    roa_rating = 'poor'
                else:
                    roa_rating = 'very_poor'
                
                ratios.append(FinancialRatio(
                    name='Return on Assets',
                    value=roa_percent,
                    industry_avg=None,
                    rating=roa_rating,
                    description=f'Generates {roa_percent:.1f}% return on total assets'
                ))
            
            # Gross Margin
            gross_margins = info.get('grossMargins')
            if gross_margins:
                gross_margin_percent = gross_margins * 100
                
                if gross_margin_percent > 50:
                    margin_rating = 'excellent'
                elif gross_margin_percent > 30:
                    margin_rating = 'good'
                elif gross_margin_percent > 20:
                    margin_rating = 'average'
                elif gross_margin_percent > 10:
                    margin_rating = 'poor'
                else:
                    margin_rating = 'very_poor'
                
                ratios.append(FinancialRatio(
                    name='Gross Margin',
                    value=gross_margin_percent,
                    industry_avg=None,
                    rating=margin_rating,
                    description=f'Gross profit margin of {gross_margin_percent:.1f}%'
                ))
            
        except Exception as e:
            logger.error(f"Error calculating financial ratios: {e}")
        
        return ratios
    
    def calculate_growth_metrics(self, info: Dict[str, Any]) -> List[GrowthMetric]:
        """Calculate growth metrics."""
        metrics = []
        
        try:
            # Revenue Growth
            revenue_growth = info.get('revenueGrowth')
            if revenue_growth:
                revenue_growth_percent = revenue_growth * 100
                
                if revenue_growth_percent > 20:
                    revenue_trend = 'accelerating'
                elif revenue_growth_percent > 5:
                    revenue_trend = 'stable'
                else:
                    revenue_trend = 'declining'
                
                metrics.append(GrowthMetric(
                    name='Revenue Growth',
                    current_value=revenue_growth_percent,
                    historical_avg=revenue_growth_percent,  # Simplified
                    trend=revenue_trend,
                    description=f'Revenue growing at {revenue_growth_percent:.1f}% annually'
                ))
            
            # Earnings Growth
            earnings_growth = info.get('earningsGrowth')
            if earnings_growth:
                earnings_growth_percent = earnings_growth * 100
                
                if earnings_growth_percent > 25:
                    earnings_trend = 'accelerating'
                elif earnings_growth_percent > 10:
                    earnings_trend = 'stable'
                else:
                    earnings_trend = 'declining'
                
                metrics.append(GrowthMetric(
                    name='Earnings Growth',
                    current_value=earnings_growth_percent,
                    historical_avg=earnings_growth_percent,  # Simplified
                    trend=earnings_trend,
                    description=f'Earnings growing at {earnings_growth_percent:.1f}% annually'
                ))
            
            # Book Value Growth (estimated from ROE)
            roe = info.get('returnOnEquity')
            payout_ratio = info.get('payoutRatio', 0.3)  # Default 30% payout
            
            if roe:
                book_value_growth = (roe * (1 - payout_ratio)) * 100
                
                if book_value_growth > 15:
                    book_trend = 'accelerating'
                elif book_value_growth > 8:
                    book_trend = 'stable'
                else:
                    book_trend = 'declining'
                
                metrics.append(GrowthMetric(
                    name='Book Value Growth',
                    current_value=book_value_growth,
                    historical_avg=book_value_growth,
                    trend=book_trend,
                    description=f'Book value growing at ~{book_value_growth:.1f}% annually'
                ))
            
        except Exception as e:
            logger.error(f"Error calculating growth metrics: {e}")
        
        return metrics
    
    def calculate_fair_value(self, info: Dict[str, Any], valuation_metrics: List[ValuationMetric],
                           growth_metrics: List[GrowthMetric]) -> Tuple[float, float]:
        """Calculate fair value estimate using multiple methods."""
        try:
            current_price = info.get('currentPrice', 0)
            if not current_price:
                return 0, 0
            
            fair_values = []
            
            # DCF-based estimate using earnings
            eps = info.get('trailingEps')
            if eps and eps > 0:
                # Find earnings growth rate
                earnings_growth = 0.1  # Default 10%
                for metric in growth_metrics:
                    if metric.name == 'Earnings Growth':
                        earnings_growth = metric.current_value / 100
                        break
                
                # Estimate fair P/E based on growth
                fair_pe = min(max(earnings_growth * 100 * 0.5, 10), 30)  # Between 10-30
                dcf_value = eps * fair_pe
                fair_values.append(dcf_value)
            
            # Book value method
            book_value = info.get('bookValue')
            if book_value:
                # Find ROE
                roe = info.get('returnOnEquity', 0.1)
                
                # Fair P/B based on ROE
                fair_pb = max(roe * 10, 1)  # Minimum 1x book
                book_value_estimate = book_value * fair_pb
                fair_values.append(book_value_estimate)
            
            # Revenue multiple method
            revenue_per_share = info.get('revenuePerShare')
            if revenue_per_share:
                # Industry-adjusted P/S multiple
                sector = info.get('sector', 'Technology')
                
                # Default P/S ratios by sector
                sector_ps = {
                    'Technology': 8,
                    'Healthcare': 6,
                    'Financial Services': 3,
                    'Consumer Defensive': 2,
                    'Utilities': 2,
                    'Real Estate': 10,
                    'Energy': 1.5,
                    'Materials': 2
                }
                
                fair_ps = sector_ps.get(sector, 4)  # Default 4x
                revenue_value_estimate = revenue_per_share * fair_ps
                fair_values.append(revenue_value_estimate)
            
            if fair_values:
                fair_value = np.median(fair_values)  # Use median to reduce outlier impact
                upside_potential = ((fair_value - current_price) / current_price) * 100
                return fair_value, upside_potential
            
            return current_price, 0
            
        except Exception as e:
            logger.error(f"Error calculating fair value: {e}")
            return 0, 0
    
    def assess_risks_and_strengths(self, info: Dict[str, Any], ratios: List[FinancialRatio],
                                  growth_metrics: List[GrowthMetric]) -> Tuple[List[str], List[str]]:
        """Identify key risks and strengths."""
        risks = []
        strengths = []
        
        try:
            # Debt analysis
            debt_to_equity = info.get('debtToEquity', 0) / 100
            if debt_to_equity > 1:
                risks.append(f"High debt levels ({debt_to_equity:.1f}x equity)")
            elif debt_to_equity < 0.3:
                strengths.append("Strong balance sheet with low debt")
            
            # Profitability analysis
            roe = info.get('returnOnEquity')
            if roe and roe > 0.15:
                strengths.append(f"High return on equity ({roe*100:.1f}%)")
            elif roe and roe < 0.05:
                risks.append("Low profitability metrics")
            
            # Valuation risk
            pe_ratio = info.get('trailingPE')
            if pe_ratio and pe_ratio > 40:
                risks.append(f"High valuation (P/E: {pe_ratio:.1f})")
            elif pe_ratio and pe_ratio < 15:
                strengths.append("Attractively valued")
            
            # Growth analysis
            for metric in growth_metrics:
                if metric.name == 'Revenue Growth':
                    if metric.current_value > 20:
                        strengths.append("Strong revenue growth")
                    elif metric.current_value < 0:
                        risks.append("Declining revenue")
                
                if metric.name == 'Earnings Growth':
                    if metric.current_value > 25:
                        strengths.append("Excellent earnings growth")
                    elif metric.current_value < 0:
                        risks.append("Declining earnings")
            
            # Market position
            market_cap = info.get('marketCap', 0)
            if market_cap > 100_000_000_000:  # $100B+
                strengths.append("Large-cap stability")
            elif market_cap < 2_000_000_000:  # < $2B
                risks.append("Small-cap volatility risk")
            
            # Dividend analysis
            dividend_yield = info.get('dividendYield')
            if dividend_yield and dividend_yield > 0.04:
                strengths.append(f"Attractive dividend yield ({dividend_yield*100:.1f}%)")
            
            # Cash position
            total_cash = info.get('totalCash', 0)
            total_debt = info.get('totalDebt', 0)
            
            if total_cash > total_debt:
                strengths.append("Net cash position")
            elif total_debt > total_cash * 3:
                risks.append("High debt burden")
            
        except Exception as e:
            logger.error(f"Error assessing risks and strengths: {e}")
        
        return risks, strengths
    
    def calculate_overall_rating(self, valuation_metrics: List[ValuationMetric],
                               financial_ratios: List[FinancialRatio],
                               growth_metrics: List[GrowthMetric],
                               upside_potential: float) -> Tuple[str, float]:
        """Calculate overall investment rating."""
        try:
            scores = []
            
            # Valuation score
            valuation_scores = {'excellent': 5, 'good': 4, 'average': 3, 'poor': 2, 'very_poor': 1}
            for metric in valuation_metrics:
                scores.append(valuation_scores.get(metric.rating, 3))
            
            # Financial strength score
            for ratio in financial_ratios:
                scores.append(valuation_scores.get(ratio.rating, 3))
            
            # Growth score
            for metric in growth_metrics:
                if metric.trend == 'accelerating':
                    scores.append(5)
                elif metric.trend == 'stable':
                    scores.append(4)
                else:
                    scores.append(2)
            
            # Upside potential bonus
            if upside_potential > 50:
                scores.append(5)
            elif upside_potential > 20:
                scores.append(4)
            elif upside_potential > 0:
                scores.append(3)
            else:
                scores.append(2)
            
            if not scores:
                return 'hold', 50
            
            avg_score = np.mean(scores)
            confidence = min(max((len(scores) / 10) * 100, 50), 95)  # Based on data availability
            
            if avg_score >= 4.5:
                return 'strong_buy', confidence
            elif avg_score >= 3.5:
                return 'buy', confidence
            elif avg_score >= 2.5:
                return 'hold', confidence
            elif avg_score >= 1.5:
                return 'sell', confidence
            else:
                return 'strong_sell', confidence
                
        except Exception as e:
            logger.error(f"Error calculating overall rating: {e}")
            return 'hold', 50
    
    async def get_fundamental_analysis(self, ticker: str) -> FundamentalAnalysisResult:
        """Get comprehensive fundamental analysis."""
        cache_key = self._get_cache_key(ticker)
        
        # Check cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry['timestamp']):
                return cache_entry['result']
        
        try:
            # Get stock data
            stock_data = await self.get_stock_info(ticker)
            info = stock_data['info']
            financials = stock_data['financials']
            balance_sheet = stock_data['balance_sheet']
            cash_flow = stock_data['cash_flow']
            
            if not info:
                raise ValueError(f"No fundamental data available for {ticker}")
            
            # Calculate metrics
            valuation_metrics = self.calculate_valuation_metrics(info, financials)
            financial_ratios = self.calculate_financial_ratios(info, balance_sheet, financials)
            growth_metrics = self.calculate_growth_metrics(info)
            
            # Calculate fair value
            fair_value, upside_potential = self.calculate_fair_value(info, valuation_metrics, growth_metrics)
            
            # Assess risks and strengths
            risks, strengths = self.assess_risks_and_strengths(info, financial_ratios, growth_metrics)
            
            # Calculate overall rating
            overall_rating, confidence = self.calculate_overall_rating(
                valuation_metrics, financial_ratios, growth_metrics, upside_potential
            )
            
            result = FundamentalAnalysisResult(
                ticker=ticker,
                company_name=info.get('longName', ticker),
                timestamp=get_kst_now(),
                current_price=info.get('currentPrice', 0),
                market_cap=info.get('marketCap', 0),
                valuation_metrics=valuation_metrics,
                financial_ratios=financial_ratios,
                growth_metrics=growth_metrics,
                overall_rating=overall_rating,
                confidence=confidence,
                fair_value=fair_value,
                upside_potential=upside_potential,
                risk_factors=risks,
                strengths=strengths
            )
            
            # Cache the result
            self.cache[cache_key] = {
                'result': result,
                'timestamp': get_kst_now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in fundamental analysis for {ticker}: {e}")
            raise


# Global service instance
fundamental_analysis_service = FundamentalAnalysisService()


def get_fundamental_analysis_service() -> FundamentalAnalysisService:
    """Get the global fundamental analysis service instance."""
    return fundamental_analysis_service