"""Economic data analysis service using LLM for insights generation."""

import logging
import json
import asyncio
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import defaultdict

import aiohttp
from src.core.config import get_settings
from src.services.fred_service import get_fred_service, FredObservation
from src.models.base import get_kst_now

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisCategory(str, Enum):
    """Economic analysis category."""
    GROWTH_EMPLOYMENT = "growthEmployment"
    INFLATION_MONETARY = "inflationMonetary"  
    FINANCIAL_RISK = "financialRisk"
    REALESTATE_DEBT = "realEstateDebt"
    FISCAL_GLOBAL = "fiscal"


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    direction: str  # "증가", "감소", "횡보"
    strength: str   # "강함", "보통", "약함"
    confidence: float  # 0.0 - 1.0
    key_points: List[str]


@dataclass
class RiskAssessment:
    """Risk assessment result."""
    level: str      # "낮음", "보통", "높음", "매우높음"
    factors: List[str]
    outlook: str    # "긍정적", "중립적", "부정적"


@dataclass
class AnalysisResult:
    """Complete analysis result."""
    category: str
    summary: str
    key_insights: List[str]
    trend_analysis: TrendAnalysis
    risk_assessment: RiskAssessment
    recommendations: List[str]
    data_quality: float
    analysis_timestamp: datetime


class EconomicAnalysisService:
    """Service for LLM-based economic data analysis."""
    
    # Category-specific indicator mappings
    CATEGORY_INDICATORS = {
        AnalysisCategory.GROWTH_EMPLOYMENT: ['A191RL1Q225SBEA', 'INDPRO', 'UNRATE', 'PAYEMS', 'ICSA', 'RSAFS', 'MANEMP', 'PPIFIS'],
        AnalysisCategory.INFLATION_MONETARY: ['CPIAUCSL', 'PCEPILFE', 'T5YIE', 'FEDFUNDS', 'DGS10', 'DGS2', 'T10Y2Y', 'PPIFIS'],
        AnalysisCategory.FINANCIAL_RISK: ['NFCI', 'BAMLH0A0HYM2', 'BAA', 'VIXCLS', 'UMCSENT'],
        AnalysisCategory.REALESTATE_DEBT: ['MORTGAGE30US', 'NYUCSFRCONDOSMSAMID', 'GFDEBTN', 'GFDEGDQ188S', 'NCBDBIQ027S'],
        AnalysisCategory.FISCAL_GLOBAL: ['FYFSGDA188S', 'DTWEXBGS', 'DGS30', 'DCOILWTICO', 'BOPGSTB']
    }
    
    # Indicator-specific characteristics for proper interpretation
    INDICATOR_CHARACTERISTICS = {
        # 역방향 지표 (높을수록 나쁨)
        'UNRATE': {'direction': 'inverse', 'normal_range': (3.0, 7.0), 'alert_threshold': 8.0},
        'ICSA': {'direction': 'inverse', 'normal_range': (200, 400), 'alert_threshold': 500},
        'VIXCLS': {'direction': 'inverse', 'normal_range': (12, 25), 'alert_threshold': 30},
        'NFCI': {'direction': 'inverse', 'normal_range': (-1.0, 0.5), 'alert_threshold': 1.0},
        'BAMLH0A0HYM2': {'direction': 'inverse', 'normal_range': (200, 600), 'alert_threshold': 800},
        'BAA': {'direction': 'inverse', 'normal_range': (3.0, 6.0), 'alert_threshold': 7.0},
        
        # 정방향 지표 (높을수록 좋음)
        'A191RL1Q225SBEA': {'direction': 'normal', 'normal_range': (1.0, 4.0), 'alert_threshold': -1.0},
        'INDPRO': {'direction': 'normal', 'normal_range': (95, 110), 'alert_threshold': 85},
        'PAYEMS': {'direction': 'normal', 'normal_range': (100, 300), 'alert_threshold': 50},
        'UMCSENT': {'direction': 'normal', 'normal_range': (80, 110), 'alert_threshold': 70},
        'RSAFS': {'direction': 'normal', 'normal_range': (0.5, 4.0), 'alert_threshold': -2.0},
        'MANEMP': {'direction': 'normal', 'normal_range': (48, 60), 'alert_threshold': 45},
        
        # 중성 지표 (맥락에 따라 다름)
        'CPIAUCSL': {'direction': 'neutral', 'normal_range': (1.5, 3.5), 'alert_threshold': 5.0},
        'PCEPILFE': {'direction': 'neutral', 'normal_range': (1.5, 3.0), 'alert_threshold': 4.0},
        'PPIFIS': {'direction': 'neutral', 'normal_range': (1.0, 4.0), 'alert_threshold': 6.0},
        'T5YIE': {'direction': 'neutral', 'normal_range': (2.0, 3.5), 'alert_threshold': 5.0},
        'FEDFUNDS': {'direction': 'neutral', 'normal_range': (2.0, 6.0), 'alert_threshold': 8.0},
        'DGS10': {'direction': 'neutral', 'normal_range': (2.0, 5.0), 'alert_threshold': 7.0},
        'DGS2': {'direction': 'neutral', 'normal_range': (2.0, 5.0), 'alert_threshold': 7.0},
        'DGS30': {'direction': 'neutral', 'normal_range': (2.5, 5.5), 'alert_threshold': 7.5},
        
        # 스프레드 지표 (확대시 위험)
        'T10Y2Y': {'direction': 'spread', 'normal_range': (0.5, 2.5), 'alert_threshold': -0.5},
        
        # 부채 관련 (급격한 증가시 위험)
        'GFDEBTN': {'direction': 'debt', 'normal_range': (20, 35), 'alert_threshold': 40},
        'GFDEGDQ188S': {'direction': 'debt', 'normal_range': (60, 120), 'alert_threshold': 130},
        'NCBDBIQ027S': {'direction': 'debt', 'normal_range': (10, 20), 'alert_threshold': 25},
        
        # 글로벌 지표
        'DTWEXBGS': {'direction': 'neutral', 'normal_range': (90, 110), 'alert_threshold': 120},
        'DCOILWTICO': {'direction': 'neutral', 'normal_range': (50, 100), 'alert_threshold': 150},
        'MORTGAGE30US': {'direction': 'inverse', 'normal_range': (3.0, 7.0), 'alert_threshold': 8.0},
        'FYFSGDA188S': {'direction': 'neutral', 'normal_range': (-8.0, 2.0), 'alert_threshold': -10.0},
        'BOPGSTB': {'direction': 'neutral', 'normal_range': (-100, 50), 'alert_threshold': -150},
        'NYUCSFRCONDOSMSAMID': {'direction': 'neutral', 'normal_range': (80, 120), 'alert_threshold': 150}
    }
    
    # 지표명 한국어 매핑 (LLM 응답에서 사용)
    INDICATOR_KOREAN_NAMES = {
        'A191RL1Q225SBEA': 'GDP 실질성장률',
        'INDPRO': '산업생산지수',
        'UNRATE': '실업률',
        'PAYEMS': '비농업 일자리수',
        'ICSA': '실업수당 신청건수',
        'CPIAUCSL': '소비자물가지수(CPI)',
        'PCEPILFE': '근원 개인소비지출 물가지수',
        'PPIFIS': '생산자물가지수(PPI)',
        'RSAFS': '소매판매액',
        'MANEMP': '제조업 고용지수',
        'T5YIE': '5년 인플레이션 기대치',
        'FEDFUNDS': '연방기준금리',
        'DGS10': '10년 국채수익률',
        'DGS2': '2년 국채수익률',
        'T10Y2Y': '장단기 금리차(10년-2년)',
        'NFCI': '금융상황지수',
        'BAMLH0A0HYM2': '고수익 회사채 스프레드',
        'BAA': '회사채 수익률(BAA등급)',
        'VIXCLS': '변동성지수(VIX)',
        'UMCSENT': '소비자심리지수',
        'MORTGAGE30US': '30년 모기지금리',
        'NYUCSFRCONDOSMSAMID': '뉴욕 부동산가격지수',
        'GFDEBTN': '연방정부 총부채',
        'GFDEGDQ188S': 'GDP 대비 정부부채 비율',
        'NCBDBIQ027S': '기업 총부채',
        'FYFSGDA188S': '연방정부 재정수지',
        'DTWEXBGS': '달러지수',
        'DGS30': '30년 국채수익률',
        'DCOILWTICO': 'WTI 원유가격',
        'BOPGSTB': '상품무역수지'
    }
    
    def __init__(self):
        self.fred_service = get_fred_service()
        self.openai_api_key = settings.OPENAI_API_KEY
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        
        # 인메모리 캐시 시스템 초기화
        self.cache: Dict[str, Dict[str, Any]] = {}  # {cache_key: {result, timestamp}}
        self.cache_expiry_seconds = 3600  # 6시간 캐시 유효 (초)
        self._cache_hits = 0
        self._cache_requests = 0
        
    async def analyze_category_data(
        self,
        category: AnalysisCategory,
        time_range: str,
        start_date: datetime,
        end_date: datetime
    ) -> AnalysisResult:
        """Analyze economic data for a specific category."""
        try:
            # 1. 데이터 수집 및 전처리
            indicators = self.CATEGORY_INDICATORS[category]
            raw_data = await self._collect_indicator_data(indicators, start_date, end_date)
            
            # 2. 통계 계산
            processed_data = self._calculate_statistics(raw_data, time_range)
            
            # 3. LLM 분석 실행
            llm_insights = await self._generate_llm_insights(category, processed_data, raw_data, time_range)
            
            # 4. 분석 결과 구조화
            result = self._format_analysis_result(category, llm_insights, processed_data)
            
            logger.info(f"Successfully analyzed category {category} with {len(indicators)} indicators")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing category {category}: {e}")
            # 오류 발생 시 기본 분석 결과 반환
            return self._create_fallback_result(category, str(e))
    
    async def _collect_indicator_data(
        self, 
        indicators: List[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, List[FredObservation]]:
        """Collect data for specified indicators."""
        try:
            data = await self.fred_service.get_economic_indicators(
                indicators, start_date, end_date
            )
            
            # 데이터 유효성 검증
            valid_data = {}
            for indicator, observations in data.items():
                if observations and len(observations) > 0:
                    valid_data[indicator] = observations
                else:
                    logger.warning(f"No data available for indicator {indicator}")
            
            return valid_data
            
        except Exception as e:
            logger.error(f"Error collecting indicator data: {e}")
            return {}
    
    def _calculate_statistics(
        self, 
        raw_data: Dict[str, List[FredObservation]], 
        time_range: str
    ) -> Dict[str, Any]:
        """Calculate statistical measures for the data."""
        stats = {}
        
        for indicator, observations in raw_data.items():
            if not observations:
                continue
                
            values = [obs.value for obs in observations if obs.value is not None]
            if len(values) < 2:
                continue
                
            try:
                # 기본 통계
                latest_value = values[-1]
                previous_value = values[-2] if len(values) > 1 else latest_value
                
                # 데이터 품질 검증 및 이상치 탐지
                data_quality_info = self._validate_data_quality(values, indicator, observations)
                
                # 지표별 특성을 고려한 분석
                characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
                trend_analysis = self._calculate_enhanced_trend(values, indicator)
                risk_level = self._assess_indicator_risk(latest_value, indicator)
                
                stats[indicator] = {
                    'latest_value': latest_value,
                    'previous_value': previous_value,
                    'change_pct': ((latest_value - previous_value) / previous_value * 100) if previous_value != 0 else 0,
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                    'min': min(values),
                    'max': max(values),
                    'data_points': len(values),
                    'trend': trend_analysis['direction'],
                    'trend_strength': trend_analysis['strength'],
                    'trend_interpretation': trend_analysis['interpretation'],
                    'volatility': self._calculate_volatility(values),
                    'risk_level': risk_level,
                    'latest_date': observations[-1].date.isoformat(),
                    'characteristics': characteristics,
                    'data_quality': data_quality_info
                }
                
            except Exception as e:
                logger.warning(f"Error calculating statistics for {indicator}: {e}")
                continue
        
        return stats
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from time series data."""
        if len(values) < 3:
            return "불충분한 데이터"
        
        # 단순 선형 회귀를 통한 트렌드 계산
        n = len(values)
        x_vals = list(range(n))
        
        # 기울기 계산
        x_mean = sum(x_vals) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_vals[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "횡보"
            
        slope = numerator / denominator
        
        # 트렌드 판정
        if abs(slope) < 0.001:
            return "횡보"
        elif slope > 0:
            return "상승"
        else:
            return "하락"
    
    def _calculate_enhanced_trend(self, values: List[float], indicator: str) -> Dict[str, str]:
        """Calculate enhanced trend analysis with indicator-specific interpretation."""
        if len(values) < 3:
            return {
                'direction': "불충분한 데이터",
                'strength': "알 수 없음",
                'interpretation': "데이터 부족으로 트렌드 분석 불가"
            }
        
        # 기본 트렌드 계산
        n = len(values)
        x_vals = list(range(n))
        x_mean = sum(x_vals) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_vals[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return {
                'direction': "횡보",
                'strength': "보통",
                'interpretation': "변화 없음"
            }
        
        slope = numerator / denominator
        
        # 최근 데이터에 가중치를 둔 트렌드 계산
        recent_values = values[-6:] if len(values) >= 6 else values[-3:]
        recent_trend = self._calculate_recent_momentum(recent_values)
        
        # R-squared 계산으로 트렌드 강도 측정
        y_pred = [y_mean + slope * (x - x_mean) for x in x_vals]
        ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # 트렌드 방향 결정
        if abs(slope) < 0.001:
            direction = "횡보"
        elif slope > 0:
            direction = "상승"
        else:
            direction = "하락"
        
        # 트렌드 강도 결정
        if r_squared > 0.7:
            strength = "강함"
        elif r_squared > 0.4:
            strength = "보통"
        else:
            strength = "약함"
        
        # 지표별 해석
        interpretation = self._interpret_trend_by_indicator(direction, strength, indicator, values[-1])
        
        return {
            'direction': direction,
            'strength': strength,
            'interpretation': interpretation
        }
    
    def _calculate_recent_momentum(self, values: List[float]) -> float:
        """Calculate recent momentum for short-term trend analysis."""
        if len(values) < 2:
            return 0.0
        
        momentum = 0.0
        weights = [0.5, 0.3, 0.2] if len(values) >= 3 else [0.7, 0.3]
        
        for i in range(min(len(values) - 1, len(weights))):
            momentum += ((values[-(i+1)] - values[-(i+2)]) / values[-(i+2)]) * weights[i]
        
        return momentum
    
    def _interpret_trend_by_indicator(self, direction: str, strength: str, indicator: str, current_value: float) -> str:
        """Interpret trend based on indicator characteristics."""
        characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
        indicator_type = characteristics.get('direction', 'neutral')
        
        interpretations = {
            'inverse': {
                '상승': "우려스러운 증가 추세",
                '하락': "긍정적인 개선 추세", 
                '횡보': "안정적 수준 유지"
            },
            'normal': {
                '상승': "긍정적인 성장 추세",
                '하락': "우려스러운 둔화 추세",
                '횡보': "성장 모멘텀 정체"
            },
            'neutral': {
                '상승': "증가 추세 (맥락적 판단 필요)",
                '하락': "감소 추세 (맥락적 판단 필요)",
                '횡보': "안정적 수준"
            },
            'spread': {
                '상승': "스프레드 확대 (위험 증가)",
                '하락': "스프레드 축소 (위험 감소)",
                '횡보': "스프레드 안정"
            },
            'debt': {
                '상승': "부채 증가 추세 (주의 필요)",
                '하락': "부채 감소 추세 (긍정적)",
                '횡보': "부채 수준 안정"
            }
        }
        
        base_interpretation = interpretations.get(indicator_type, interpretations['neutral']).get(direction, "트렌드 불분명")
        
        # 강도 추가
        if strength == "강함":
            return f"{base_interpretation} (명확한 신호)"
        elif strength == "약함":
            return f"{base_interpretation} (불분명한 신호)"
        else:
            return base_interpretation
    
    def _assess_indicator_risk(self, current_value: float, indicator: str) -> str:
        """Assess risk level based on current indicator value."""
        characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
        
        if not characteristics:
            return "보통"
        
        normal_range = characteristics.get('normal_range', (0, 100))
        alert_threshold = characteristics.get('alert_threshold', 100)
        indicator_type = characteristics.get('direction', 'neutral')
        
        # 범위 기반 위험 평가
        if indicator_type == 'inverse':
            # 역방향 지표: 높을수록 위험
            if current_value >= alert_threshold:
                return "매우높음"
            elif current_value > normal_range[1]:
                return "높음"
            elif current_value >= normal_range[0]:
                return "보통"
            else:
                return "낮음"
        
        elif indicator_type == 'normal':
            # 정방향 지표: 낮을수록 위험
            if current_value <= alert_threshold:
                return "매우높음"
            elif current_value < normal_range[0]:
                return "높음"
            elif current_value <= normal_range[1]:
                return "보통"
            else:
                return "낮음"
        
        elif indicator_type == 'spread':
            # 스프레드: 역전시 매우 위험
            if current_value < alert_threshold:
                return "매우높음"
            elif current_value < normal_range[0]:
                return "높음"
            elif current_value <= normal_range[1]:
                return "보통"
            else:
                return "높음"  # 스프레드가 너무 클 때도 위험
        
        else:
            # 중성/부채 지표: 정상 범위 기준
            if current_value >= alert_threshold or current_value <= (alert_threshold * -1 if alert_threshold > 0 else alert_threshold):
                return "매우높음"
            elif current_value > normal_range[1] or current_value < normal_range[0]:
                return "높음"
            else:
                return "보통"
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (coefficient of variation)."""
        if len(values) < 2:
            return 0.0
            
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
            
        std_val = statistics.stdev(values)
        return (std_val / abs(mean_val)) * 100
    
    def _validate_data_quality(self, values: List[float], indicator: str, observations: List[FredObservation]) -> Dict[str, Any]:
        """Validate data quality and detect anomalies."""
        quality_info = {
            'score': 1.0,
            'issues': [],
            'outliers': [],
            'missing_periods': 0,
            'reliability': 'high'
        }
        
        if len(values) < 3:
            quality_info['score'] = 0.3
            quality_info['issues'].append("데이터 포인트 부족")
            quality_info['reliability'] = 'low'
            return quality_info
        
        # 1. 결측값 비율 확인
        total_expected_periods = self._calculate_expected_periods(observations)
        missing_ratio = (total_expected_periods - len(observations)) / total_expected_periods if total_expected_periods > 0 else 0
        quality_info['missing_periods'] = total_expected_periods - len(observations)
        
        # 2. 이상치 탐지
        outliers = self._detect_outliers(values, indicator)
        quality_info['outliers'] = outliers
        
        # 3. 급격한 변화 탐지
        extreme_changes = self._detect_extreme_changes(values, indicator)
        
        # 4. 데이터 일관성 검증
        consistency_issues = self._check_data_consistency(values, indicator)
        
        # 품질 점수 계산
        score_deductions = 0
        
        # Missing data penalty
        if missing_ratio > 0.1:
            score_deductions += 0.2
            quality_info['issues'].append(f"결측값 비율 높음 ({missing_ratio:.1%})")
        
        # Outliers penalty
        if len(outliers) > 0:
            outlier_ratio = len(outliers) / len(values)
            if outlier_ratio > 0.05:
                score_deductions += min(0.3, outlier_ratio * 2)
                quality_info['issues'].append(f"이상치 {len(outliers)}개 탐지")
        
        # Extreme changes penalty
        if extreme_changes:
            score_deductions += 0.15
            quality_info['issues'].append("급격한 변화 감지")
        
        # Consistency penalty
        if consistency_issues:
            score_deductions += 0.1
            quality_info['issues'].extend(consistency_issues)
        
        quality_info['score'] = max(0.1, 1.0 - score_deductions)
        
        # Reliability assessment
        if quality_info['score'] >= 0.8:
            quality_info['reliability'] = 'high'
        elif quality_info['score'] >= 0.6:
            quality_info['reliability'] = 'medium'
        else:
            quality_info['reliability'] = 'low'
        
        return quality_info
    
    def _calculate_expected_periods(self, observations: List[FredObservation]) -> int:
        """Calculate expected number of periods based on data frequency."""
        if len(observations) < 2:
            return len(observations)
        
        # Estimate frequency from first few observations
        dates = [obs.date for obs in observations[:10] if obs.date]
        if len(dates) < 2:
            return len(observations)
        
        # Calculate average interval
        intervals = []
        for i in range(1, len(dates)):
            interval = (dates[i] - dates[i-1]).days
            intervals.append(interval)
        
        if not intervals:
            return len(observations)
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Determine frequency
        if avg_interval <= 1:
            frequency = 'daily'
        elif avg_interval <= 7:
            frequency = 'weekly'
        elif avg_interval <= 32:
            frequency = 'monthly'
        elif avg_interval <= 95:
            frequency = 'quarterly'
        else:
            frequency = 'yearly'
        
        # Calculate expected periods based on date range and frequency
        start_date = observations[0].date
        end_date = observations[-1].date
        total_days = (end_date - start_date).days
        
        frequency_days = {'daily': 1, 'weekly': 7, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        expected = total_days / frequency_days.get(frequency, 30)
        
        return max(len(observations), int(expected))
    
    def _detect_outliers(self, values: List[float], indicator: str) -> List[Dict[str, Any]]:
        """Detect statistical outliers using IQR method."""
        if len(values) < 4:
            return []
        
        outliers = []
        
        # Calculate IQR
        sorted_values = sorted(values)
        q1_idx = len(sorted_values) // 4
        q3_idx = 3 * len(sorted_values) // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        if iqr == 0:  # No variation
            return []
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Identify outliers
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                # Check if it's a reasonable outlier for this indicator
                characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
                normal_range = characteristics.get('normal_range')
                
                # Don't flag as outlier if within known normal range
                if normal_range and normal_range[0] <= value <= normal_range[1]:
                    continue
                
                outliers.append({
                    'index': i,
                    'value': value,
                    'type': 'high' if value > upper_bound else 'low',
                    'deviation': abs(value - (q1 + q3) / 2) / iqr
                })
        
        return outliers
    
    def _detect_extreme_changes(self, values: List[float], indicator: str) -> bool:
        """Detect extreme period-to-period changes."""
        if len(values) < 2:
            return False
        
        # Calculate percentage changes
        changes = []
        for i in range(1, len(values)):
            if values[i-1] != 0:
                change = abs((values[i] - values[i-1]) / values[i-1])
                changes.append(change)
        
        if not changes:
            return False
        
        # Define extreme change thresholds by indicator type
        characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
        indicator_type = characteristics.get('direction', 'neutral')
        
        # Different thresholds for different indicator types
        thresholds = {
            'inverse': 0.5,  # VIX, unemployment can change rapidly
            'normal': 0.3,   # GDP, employment are usually more stable
            'neutral': 0.4,  # Interest rates, inflation
            'spread': 1.0,   # Spreads can be volatile
            'debt': 0.2      # Debt ratios change slowly
        }
        
        threshold = thresholds.get(indicator_type, 0.4)
        
        # Check for extreme changes
        extreme_changes = [c for c in changes if c > threshold]
        
        # Flag as extreme if multiple large changes or very large single change
        return len(extreme_changes) > 2 or any(c > threshold * 2 for c in changes)
    
    def _check_data_consistency(self, values: List[float], indicator: str) -> List[str]:
        """Check for data consistency issues."""
        issues = []
        
        if len(values) < 3:
            return issues
        
        # Check for impossible values
        characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
        
        # Check against known reasonable ranges
        if indicator == 'UNRATE' and any(v < 0 or v > 50 for v in values):
            issues.append("실업률 비정상적 수치")
        elif indicator in ['DGS10', 'DGS2', 'FEDFUNDS'] and any(v < -5 or v > 20 for v in values):
            issues.append("금리 비정상적 수치")
        elif indicator == 'VIXCLS' and any(v < 5 or v > 100 for v in values):
            issues.append("VIX 비정상적 수치")
        
        # Check for repeated identical values (potential data staleness)
        if len(set(values[-5:])) == 1 and len(values) >= 5:
            issues.append("최근 데이터 동일값 반복")
        
        # Check for monotonic sequences (potential data error)
        if len(values) >= 5:
            last_5 = values[-5:]
            if all(last_5[i] <= last_5[i+1] for i in range(4)) or all(last_5[i] >= last_5[i+1] for i in range(4)):
                issues.append("단조 증가/감소 패턴 감지")
        
        return issues
    
    def _generate_cache_key(self, category: AnalysisCategory, processed_data: Dict[str, Any], 
                           raw_data: Dict[str, List[FredObservation]], time_range: str) -> str:
        """Generate unique cache key for analysis request."""
        # 최신 데이터의 날짜들을 기준으로 키 생성
        latest_dates = []
        for indicator, observations in raw_data.items():
            if observations:
                latest_dates.append(observations[-1].date.isoformat())
        
        # 주요 통계값들로 데이터 변화 감지
        key_stats = []
        for indicator, stats in processed_data.items():
            if isinstance(stats, dict):
                latest_value = stats.get('latest_value', 0)
                change_pct = stats.get('change_pct', 0)
                key_stats.append(f"{indicator}:{latest_value:.3f}:{change_pct:.2f}")
        
        # 캐시 키 생성
        cache_data = {
            'category': category.value,
            'time_range': time_range,
            'latest_dates': sorted(latest_dates),
            'key_stats': sorted(key_stats)
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result if valid."""
        try:
            self._cache_requests += 1
            
            if cache_key not in self.cache:
                return None
            
            cached_entry = self.cache[cache_key]
            current_time = time.time()
            
            # 캐시 만료 확인
            if current_time - cached_entry['timestamp'] > self.cache_expiry_seconds:
                # 만료된 캐시 삭제
                del self.cache[cache_key]
                return None
            
            self._cache_hits += 1
            logger.info(f"Cache hit for analysis: {cache_key}")
            return cached_entry['result']
            
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None
    
    def _save_to_cache(self, cache_key: str, analysis_result: Dict[str, Any]) -> None:
        """Save analysis result to cache."""
        try:
            current_time = time.time()
            self.cache[cache_key] = {
                'result': analysis_result,
                'timestamp': current_time
            }
            
            # 캐시 크기 제한 (최대 100개 항목 유지)
            if len(self.cache) > 100:
                self._cleanup_old_cache()
            
            logger.info(f"Analysis result cached: {cache_key}")
            
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
    
    def _cleanup_old_cache(self) -> None:
        """Clean up old cache entries."""
        try:
            current_time = time.time()
            expired_keys = []
            
            for cache_key, cached_entry in self.cache.items():
                if current_time - cached_entry['timestamp'] > self.cache_expiry_seconds:
                    expired_keys.append(cache_key)
            
            # 만료된 캐시 항목들 삭제
            for key in expired_keys:
                del self.cache[key]
            
            # 캐시 크기가 너무 클 경우 오래된 항목부터 삭제
            if len(self.cache) > 50:
                # 타임스탬프 기준으로 정렬해서 오래된 것부터 삭제
                sorted_items = sorted(
                    self.cache.items(), 
                    key=lambda x: x[1]['timestamp']
                )
                items_to_remove = len(self.cache) - 50
                for i in range(items_to_remove):
                    key_to_remove = sorted_items[i][0]
                    del self.cache[key_to_remove]
            
            if expired_keys or len(self.cache) > 50:
                logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries, cache size: {len(self.cache)}")
                    
        except Exception as e:
            logger.warning(f"Error cleaning cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for cached_entry in self.cache.values():
            if current_time - cached_entry['timestamp'] > self.cache_expiry_seconds:
                expired_entries += 1
            else:
                valid_entries += 1
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_hit_rate': getattr(self, '_cache_hits', 0) / max(1, getattr(self, '_cache_requests', 1)),
            'expiry_seconds': self.cache_expiry_seconds
        }
    
    def _convert_tickers_to_korean(self, text: str) -> str:
        """Convert ticker symbols to Korean names in text."""
        if not text:
            return text
        
        converted_text = text
        for ticker, korean_name in self.INDICATOR_KOREAN_NAMES.items():
            # 여러 패턴으로 ticker 교체
            patterns = [
                ticker,  # 기본 ticker
                f"({ticker})",  # 괄호 안의 ticker
                f" {ticker} ",  # 공백으로 둘러싸인 ticker
                f"{ticker}:",  # 콜론이 뒤따르는 ticker
                f"{ticker},",  # 콤마가 뒤따르는 ticker
            ]
            
            for pattern in patterns:
                converted_text = converted_text.replace(pattern, korean_name)
        
        return converted_text
    
    async def _generate_llm_insights(
        self, 
        category: AnalysisCategory, 
        processed_data: Dict[str, Any], 
        raw_data: Dict[str, List[FredObservation]],
        time_range: str
    ) -> Dict[str, Any]:
        """Generate insights using LLM with caching."""
        try:
            # 캐시 키 생성
            cache_key = self._generate_cache_key(category, processed_data, raw_data, time_range)
            
            # 캐시된 결과 확인
            cached_result = self._get_cached_analysis(cache_key)
            if cached_result:
                logger.info(f"Using cached analysis for category {category}")
                return cached_result
            
            # 프롬프트 생성
            prompt = self._generate_category_prompt(category, processed_data, raw_data, time_range)
            
            # LLM API 호출 (OpenAI 우선, 실패시 Anthropic)
            llm_response = None
            if self.openai_api_key:
                try:
                    response = await self._call_openai_api(prompt)
                    llm_response = self._parse_llm_response(response)
                except Exception as e:
                    logger.warning(f"OpenAI API failed, trying Anthropic: {e}")
            
            # Anthropic API 시도 (OpenAI 실패시 또는 키 없을 시)
            if not llm_response and self.anthropic_api_key:
                try:
                    response = await self._call_anthropic_api(prompt)
                    llm_response = self._parse_llm_response(response)
                except Exception as e:
                    logger.warning(f"Anthropic API also failed: {e}")
            
            # LLM 응답 후처리 (티커를 한국어로 변환)
            if llm_response:
                # summary, key_insights, recommendations에서 티커 변환
                if 'summary' in llm_response:
                    llm_response['summary'] = self._convert_tickers_to_korean(llm_response['summary'])
                
                if 'key_insights' in llm_response:
                    llm_response['key_insights'] = [
                        self._convert_tickers_to_korean(insight) 
                        for insight in llm_response['key_insights']
                    ]
                
                if 'recommendations' in llm_response:
                    llm_response['recommendations'] = [
                        self._convert_tickers_to_korean(rec) 
                        for rec in llm_response['recommendations']
                    ]
                
                # 트렌드 분석과 위험 평가의 텍스트 필드도 변환
                if 'trend_analysis' in llm_response and isinstance(llm_response['trend_analysis'], dict):
                    trend_data = llm_response['trend_analysis']
                    if 'key_points' in trend_data:
                        trend_data['key_points'] = [
                            self._convert_tickers_to_korean(point) 
                            for point in trend_data['key_points']
                        ]
                
                if 'risk_assessment' in llm_response and isinstance(llm_response['risk_assessment'], dict):
                    risk_data = llm_response['risk_assessment']
                    if 'factors' in risk_data:
                        risk_data['factors'] = [
                            self._convert_tickers_to_korean(factor) 
                            for factor in risk_data['factors']
                        ]
                
                # 성공적인 LLM 응답을 캐시에 저장
                self._save_to_cache(cache_key, llm_response)
                logger.info(f"LLM analysis completed and cached for category {category}")
                
                return llm_response
            
            # LLM 사용 불가시 기본 분석
            logger.warning("No LLM APIs available, using fallback analysis")
            fallback_result = self._generate_fallback_insights(category, processed_data)
            
            # 폴백 결과도 캐시 (짧은 시간으로)
            fallback_cache_key = f"fallback_{cache_key}"
            self._save_to_cache(fallback_cache_key, fallback_result)
            
            return fallback_result
            
        except Exception as e:
            logger.error(f"Error generating LLM insights: {e}")
            return self._generate_fallback_insights(category, processed_data)
    
    def _generate_category_prompt(
        self, 
        category: AnalysisCategory, 
        data: Dict[str, Any], 
        raw_data: Dict[str, List[FredObservation]],
        time_range: str
    ) -> str:
        """Generate category-specific analysis prompt."""
        
        # 현재 날짜 정보
        current_date = get_kst_now().strftime("%Y년 %m월 %d일")
        
        # 기본 프롬프트 템플릿
        base_prompt = f"""
당신은 전문 경제 분석가입니다. 다음 거시경제 데이터를 분석하여 통찰력 있는 보고서를 작성해주세요.

분석 기준일: {current_date}
분석 대상: {self._get_category_description(category)}
분석 기간: {time_range}

데이터 요약:
{self._format_data_for_prompt(data, raw_data)}

**중요 분석 지침:**
1. 가장 최근 발표된 지표들의 변화에 특별히 주목하세요
2. 제공된 시계열 데이터를 활용하여 최근 12개월간의 패턴과 추세를 분석하세요
3. 최근 지표 트렌드가 현재 경제 상황에 미치는 영향을 분석하세요  
4. 시계열 데이터의 변화 패턴을 바탕으로 향후 3-6개월, 1년 후의 경제 전망을 예측하세요
5. 최신 지표의 모멘텀과 방향성이 미래에 어떤 파급효과를 가져올지 평가하세요
6. 최근 변화가 기존 트렌드의 연속인지 아니면 전환점인지 시계열 데이터를 통해 판단하세요
7. 각 지표간의 상관관계와 선행/후행 관계를 고려하여 분석하세요

**경제 지표 해석 가이드라인:**
- 실업률(UNRATE), VIX, 스프레드 등은 역방향 지표입니다 (상승 = 악화, 하락 = 개선)
- GDP, 산업생산, 소비자심리 등은 정방향 지표입니다 (상승 = 개선, 하락 = 악화)
- 데이터 품질이 낮은 지표는 해석에 주의가 필요합니다
- 급격한 변화나 이상치가 있는 경우 그 원인을 고려하세요
- 각 지표의 위험 수준과 트렌드 해석을 종합적으로 판단하세요

다음 형식의 JSON으로 응답해주세요:
{{
    "summary": "최근 지표 변화를 중심으로 한 전체적인 상황 요약 (2-3문장)",
    "key_insights": ["최근 데이터 기반 핵심 인사이트 1", "향후 전망 인사이트 2", "현재 영향 분석 3"],
    "trend_analysis": {{
        "direction": "증가/감소/횡보",
        "strength": "강함/보통/약함", 
        "confidence": 0.85,
        "key_points": ["최근 트렌드 변화 포인트", "미래 트렌드 전망"]
    }},
    "risk_assessment": {{
        "level": "낮음/보통/높음/매우높음",
        "factors": ["최근 데이터 기반 리스크 요인들"],
        "outlook": "긍정적/중립적/부정적"
    }},
    "recommendations": ["최근 변화를 고려한 권고사항 1", "향후 대응방안 2", "모니터링 포인트 3"]
}}

한국어로 작성하고, 최신 데이터의 미래 파급효과를 중심으로 객관적이고 실용적인 분석을 제공해주세요.
"""
        
        # 카테고리별 특화 프롬프트 추가
        category_specific = self._get_category_specific_prompt(category)
        
        return base_prompt + "\n" + category_specific
    
    def _get_category_description(self, category: AnalysisCategory) -> str:
        """Get description for each category."""
        descriptions = {
            AnalysisCategory.GROWTH_EMPLOYMENT: "성장 & 고용 지표 (GDP, GDP 실질성장률, 산업생산, 실업률, 일자리)",
            AnalysisCategory.INFLATION_MONETARY: "인플레이션 & 통화정책 지표 (CPI, 인플레이션 기대, 연방기준금리, 수익률곡선)",
            AnalysisCategory.FINANCIAL_RISK: "금융 & 시장위험 지표 (금융상황지수, 회사채 스프레드, VIX, 소비자심리)",
            AnalysisCategory.REALESTATE_DEBT: "부동산 & 부채 지표 (모기지금리, 주택가격, 정부부채, GDP 대비 부채비율)",
            AnalysisCategory.FISCAL_GLOBAL: "재정 & 글로벌 지표 (재정수지, 달러지수, 30년 국채, 유가, 무역수지)"
        }
        return descriptions.get(category, "거시경제 지표")
    
    def _format_data_for_prompt(self, processed_data: Dict[str, Any], raw_data: Dict[str, List[FredObservation]]) -> str:
        """Format both statistical and time series data for LLM prompt."""
        formatted_lines = []
        
        # 통계 요약 섹션
        formatted_lines.append("## 통계 요약:")
        
        for indicator, stats in processed_data.items():
            if not isinstance(stats, dict):
                continue
            
            latest_value = stats.get('latest_value', 'N/A')
            change_pct = stats.get('change_pct', 0)
            trend = stats.get('trend', 'N/A')
            latest_date = stats.get('latest_date', 'N/A')
            volatility = stats.get('volatility', 0)
            
            # 변화율 강조 표현
            change_emphasis = ""
            if abs(change_pct) >= 5:
                change_emphasis = " [큰 변화]"
            elif abs(change_pct) >= 2:
                change_emphasis = " [주목할 변화]"
            
            # 지표별 상세 정보 추가
            trend_strength = stats.get('trend_strength', 'N/A')
            trend_interpretation = stats.get('trend_interpretation', 'N/A')
            risk_level = stats.get('risk_level', 'N/A')
            data_quality = stats.get('data_quality', {})
            quality_score = data_quality.get('score', 1.0)
            quality_reliability = data_quality.get('reliability', 'medium')
            quality_issues = data_quality.get('issues', [])
            
            line = f"- {indicator}: 최신값 {latest_value} ({latest_date}), "
            line += f"전기대비 {change_pct:+.1f}% 변화{change_emphasis}, "
            line += f"트렌드: {trend}({trend_strength}), "
            line += f"해석: {trend_interpretation}, "
            line += f"위험도: {risk_level}, 변동성: {volatility:.1f}%, "
            line += f"데이터 품질: {quality_reliability}({quality_score:.2f})"
            
            if quality_issues:
                line += f" [주의: {', '.join(quality_issues[:2])}]"
            
            formatted_lines.append(line)
        
        # 최근 변화가 큰 지표들을 상단에 배치
        stats_lines = formatted_lines[1:]  # "## 통계 요약:" 제외
        stats_lines.sort(key=lambda x: abs(float(x.split('전기대비 ')[1].split('%')[0])), reverse=True)
        formatted_lines = [formatted_lines[0]] + stats_lines
        
        # 시계열 데이터 섹션 추가
        formatted_lines.append("\n## 최근 12개월 시계열 데이터:")
        
        for indicator, observations in raw_data.items():
            if not observations:
                continue
            
            # 최근 12개월 데이터만 선택
            recent_data = observations[-12:] if len(observations) >= 12 else observations
            
            formatted_lines.append(f"\n### {indicator}:")
            data_points = []
            for obs in recent_data:
                data_points.append(f"{obs.date.strftime('%Y-%m')}: {obs.value}")
            formatted_lines.append(", ".join(data_points))
        
        return "\n".join(formatted_lines)
    
    def _get_category_specific_prompt(self, category: AnalysisCategory) -> str:
        """Get category-specific analysis instructions."""
        prompts = {
            AnalysisCategory.GROWTH_EMPLOYMENT: """
특별 고려사항 - 최근 동향과 미래 영향 중심:
- 최신 GDP와 GDP 실질성장률 변화가 향후 고용시장에 미칠 파급효과 분석
- GDP 실질성장률의 최근 추세가 경제 모멘텀과 향후 성장 지속성에 주는 신호 해석
- 최근 실업률과 일자리 증가 트렌드가 소비와 경기회복에 미치는 영향
- 산업생산지수 최신 변화가 향후 제조업과 실물경제에 주는 신호 해석
- 소매판매액(RSAFS) 최근 변화가 향후 소비지출과 경기에 미칠 파급효과 분석
- 제조업 고용지수(MANEMP) 변화가 제조업 전반과 공급망에 주는 신호 해석
- 생산자물가지수(PPI) 최근 동향이 향후 소비자물가와 기업 수익성에 미칠 영향
- 최근 고용지표 개선/악화가 연준 정책과 인플레이션에 미칠 영향 예측
- GDP 실질성장률과 고용지표 간의 상관관계를 통한 경제 전반적 건전성 평가
""",
            AnalysisCategory.INFLATION_MONETARY: """
특별 고려사항 - 최근 동향과 미래 영향 중심:
- 최신 인플레이션 데이터가 향후 연준 정책 결정에 미칠 영향 분석
- 생산자물가지수(PPI) 최근 변화가 향후 소비자물가와 인플레이션 전망에 미칠 영향
- 최근 수익률곡선 변화가 향후 금융시장과 경기에 주는 신호 해석
- 최근 인플레이션 기대치 변화가 실제 물가와 소비에 미칠 파급효과
- 최신 연준 기준금리 변화가 향후 3-12개월 경제활동에 미칠 영향 예측
- PPI와 CPI 간의 시차와 상관관계를 통한 미래 인플레이션 압력 예측
""",
            AnalysisCategory.FINANCIAL_RISK: """
특별 고려사항 - 최근 동향과 미래 영향 중심:
- 최근 금융상황지수 변화가 향후 신용시장과 대출에 미칠 영향
- 최신 VIX와 회사채 스프레드 변화가 시사하는 향후 시장 위험도
- 최근 소비자심리 변화가 향후 소비지출과 경기에 미칠 파급효과
- 최신 금융시장 지표들이 향후 기업 투자와 자금조달에 주는 신호 분석
""",
            AnalysisCategory.REALESTATE_DEBT: """
특별 고려사항 - 최근 동향과 미래 영향 중심:
- 최근 모기지 금리 변화가 향후 주택시장과 가계부채에 미칠 영향
- 최신 주택가격 트렌드가 향후 부동산 시장 안정성에 주는 신호
- 최근 정부부채 증가가 향후 재정건전성과 금리에 미칠 파급효과
- 최신 가계/기업 부채 수준이 향후 경제 충격 대응력에 미치는 영향 분석
""",
            AnalysisCategory.FISCAL_GLOBAL: """
특별 고려사항 - 최근 동향과 미래 영향 중심:
- 최근 재정수지 변화가 향후 정부정책과 경제성장에 미칠 영향
- 최신 달러지수 변동이 향후 미국 수출입과 글로벌 경제에 주는 파급효과
- 최근 유가 변화가 향후 인플레이션과 소비지출에 미칠 영향 예측
- 최신 무역수지 트렌드가 향후 대외경제정책과 환율에 주는 신호 분석
"""
        }
        return prompts.get(category, "")
    
    async def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API for analysis."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "당신은 전문 거시경제 분석가입니다. 항상 JSON 형식으로 응답하세요."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 10000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    raise Exception(f"OpenAI API error: {response.status}")
    
    async def _call_anthropic_api(self, prompt: str) -> str:
        """Call Anthropic Claude API for analysis."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 2000,
            "temperature": 0.3,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["content"][0]["text"]
                else:
                    raise Exception(f"Anthropic API error: {response.status}")
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data."""
        try:
            # JSON 추출 시도
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = response[start:end]
                parsed = json.loads(json_str)
                return parsed
            else:
                # JSON 형식이 아닌 경우 파싱 시도
                return self._fallback_parse_response(response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}, attempting fallback parsing")
            return self._fallback_parse_response(response)
    
    def _fallback_parse_response(self, llm_response: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails."""
        return {
            "summary": "LLM 응답 파싱에 실패했습니다. 데이터 분석을 통한 기본 해석을 제공합니다.",
            "key_insights": ["응답 파싱 오류로 인해 기본 분석을 제공합니다"],
            "trend_analysis": {
                "direction": "불확실",
                "strength": "보통",
                "confidence": 0.5,
                "key_points": ["응답 파싱 실패"]
            },
            "risk_assessment": {
                "level": "보통",
                "factors": ["분석 결과 파싱 실패"],
                "outlook": "중립적"
            },
            "recommendations": ["LLM 응답을 확인하고 재분석을 권장합니다"]
        }
    
    def _generate_fallback_insights(
        self, 
        category: AnalysisCategory, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate enhanced insights when LLM is not available."""
        # 지표별 특성을 고려한 개선된 분석
        category_risk = self._assess_category_risk(category, data)
        trend_analysis = self._analyze_category_trends(category, data)
        
        # 주요 위험 요인 식별
        high_risk_indicators = [
            indicator for indicator, stats in data.items()
            if isinstance(stats, dict) and stats.get('risk_level') in ['높음', '매우높음']
        ]
        
        # 긍정적/부정적 신호 계산 (지표 특성 고려)
        positive_signals = 0
        negative_signals = 0
        
        for indicator, stats in data.items():
            if not isinstance(stats, dict):
                continue
            
            characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
            trend = stats.get('trend', '횡보')
            indicator_type = characteristics.get('direction', 'neutral')
            
            # 지표별 특성에 따른 신호 평가
            if indicator_type == 'inverse':
                if trend == '하락':
                    positive_signals += 1
                elif trend == '상승':
                    negative_signals += 1
            elif indicator_type == 'normal':
                if trend == '상승':
                    positive_signals += 1
                elif trend == '하락':
                    negative_signals += 1
        
        # 전체적 방향 결정
        if positive_signals > negative_signals:
            overall_direction = "개선"
            outlook = "긍정적"
        elif negative_signals > positive_signals:
            overall_direction = "악화"
            outlook = "부정적"
        else:
            overall_direction = "혼재"
            outlook = "중립적"
        
        return {
            "summary": f"{self._get_category_description(category)} 분석 결과, {overall_direction} 신호가 나타나고 있습니다. 위험 수준: {category_risk['level']}",
            "key_insights": self._generate_category_insights(category, data, trend_analysis, high_risk_indicators),
            "trend_analysis": {
                "direction": trend_analysis['direction'],
                "strength": trend_analysis['strength'],
                "confidence": trend_analysis['confidence'],
                "key_points": trend_analysis['key_points']
            },
            "risk_assessment": {
                "level": category_risk['level'],
                "factors": category_risk['factors'],
                "outlook": outlook
            },
            "recommendations": self._generate_category_recommendations(category, data, high_risk_indicators)
        }
    
    def _assess_category_risk(self, category: AnalysisCategory, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall risk for a specific category."""
        risk_scores = []
        risk_factors = []
        
        risk_mapping = {"낮음": 1, "보통": 2, "높음": 3, "매우높음": 4}
        
        for indicator, stats in data.items():
            if not isinstance(stats, dict):
                continue
            
            risk_level = stats.get('risk_level', '보통')
            risk_scores.append(risk_mapping.get(risk_level, 2))
            
            if risk_level in ['높음', '매우높음']:
                characteristics = self.INDICATOR_CHARACTERISTICS.get(indicator, {})
                risk_factors.append(f"{indicator} 지표 {risk_level} 위험")
        
        if not risk_scores:
            return {"level": "보통", "factors": ["데이터 부족"]}
        
        avg_risk = sum(risk_scores) / len(risk_scores)
        
        if avg_risk >= 3.5:
            level = "매우높음"
        elif avg_risk >= 2.5:
            level = "높음"
        elif avg_risk >= 1.5:
            level = "보통"
        else:
            level = "낮음"
        
        # 카테고리별 특수 위험 요인 추가
        category_specific_risks = self._get_category_specific_risks(category, data)
        risk_factors.extend(category_specific_risks)
        
        return {
            "level": level,
            "factors": risk_factors if risk_factors else ["전반적으로 안정적 수준"]
        }
    
    def _analyze_category_trends(self, category: AnalysisCategory, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall trends for a category."""
        trends = []
        strengths = []
        
        for indicator, stats in data.items():
            if not isinstance(stats, dict):
                continue
            
            trend = stats.get('trend', '횡보')
            strength = stats.get('trend_strength', '보통')
            
            trends.append(trend)
            if strength == '강함':
                strengths.append(3)
            elif strength == '보통':
                strengths.append(2)
            else:
                strengths.append(1)
        
        if not trends:
            return {
                "direction": "불확실",
                "strength": "약함",
                "confidence": 0.3,
                "key_points": ["데이터 부족으로 트렌드 분석 제한적"]
            }
        
        # 주요 방향 결정
        trend_counts = {"상승": trends.count("상승"), "하락": trends.count("하락"), "횡보": trends.count("횡보")}
        dominant_trend = max(trend_counts, key=trend_counts.get)
        
        # 강도 계산
        avg_strength = sum(strengths) / len(strengths) if strengths else 1
        if avg_strength >= 2.5:
            strength = "강함"
            confidence = 0.8
        elif avg_strength >= 1.5:
            strength = "보통"
            confidence = 0.6
        else:
            strength = "약함"
            confidence = 0.4
        
        key_points = [f"주요 지표들의 {dominant_trend} 추세 우세"]
        
        return {
            "direction": dominant_trend,
            "strength": strength,
            "confidence": confidence,
            "key_points": key_points
        }
    
    def _get_category_specific_risks(self, category: AnalysisCategory, data: Dict[str, Any]) -> List[str]:
        """Get category-specific risk factors."""
        risks = []
        
        if category == AnalysisCategory.GROWTH_EMPLOYMENT:
            if any(stats.get('risk_level') == '매우높음' for ind, stats in data.items() 
                   if isinstance(stats, dict) and ind in ['UNRATE', 'A191RL1Q225SBEA']):
                risks.append("경기침체 가능성 증대")
        
        elif category == AnalysisCategory.INFLATION_MONETARY:
            if any(stats.get('latest_value', 0) > 4 for ind, stats in data.items()
                   if isinstance(stats, dict) and ind in ['CPIAUCSL', 'PCEPILFE']):
                risks.append("인플레이션 압력 가중")
        
        elif category == AnalysisCategory.FINANCIAL_RISK:
            if any(stats.get('risk_level') == '매우높음' for ind, stats in data.items()
                   if isinstance(stats, dict) and ind in ['VIXCLS', 'NFCI']):
                risks.append("금융시장 불안정성 확대")
        
        elif category == AnalysisCategory.REALESTATE_DEBT:
            if any(stats.get('risk_level') in ['높음', '매우높음'] for ind, stats in data.items()
                   if isinstance(stats, dict) and ind in ['GFDEGDQ188S', 'NCBDBIQ027S']):
                risks.append("부채 지속가능성 우려")
        
        elif category == AnalysisCategory.FISCAL_GLOBAL:
            if any(stats.get('risk_level') == '매우높음' for ind, stats in data.items()
                   if isinstance(stats, dict) and ind in ['FYFSGDA188S', 'DCOILWTICO']):
                risks.append("글로벌 경제 불확실성 증가")
        
        return risks
    
    def _generate_category_insights(self, category: AnalysisCategory, data: Dict[str, Any], 
                                   trend_analysis: Dict, high_risk_indicators: List[str]) -> List[str]:
        """Generate category-specific insights."""
        insights = []
        
        # 기본 통계 인사이트
        insights.append(f"총 {len(data)}개 지표 중 주요 트렌드: {trend_analysis['direction']}")
        
        # 위험 지표 인사이트
        if high_risk_indicators:
            insights.append(f"주의 필요 지표: {', '.join(high_risk_indicators[:3])}")
        else:
            insights.append("대부분의 지표가 안정적 수준 유지")
        
        # 카테고리별 특화 인사이트 추가
        category_insights = self._get_category_specific_insights(category, data)
        insights.extend(category_insights)
        
        return insights
    
    def _get_category_specific_insights(self, category: AnalysisCategory, data: Dict[str, Any]) -> List[str]:
        """Get category-specific insights based on indicator analysis."""
        insights = []
        
        if category == AnalysisCategory.GROWTH_EMPLOYMENT:
            unemployment = next((stats for ind, stats in data.items() if ind == 'UNRATE' and isinstance(stats, dict)), None)
            if unemployment:
                trend_interp = unemployment.get('trend_interpretation', '')
                insights.append(f"실업률 동향: {trend_interp}")
            
            gdp_growth = next((stats for ind, stats in data.items() if ind == 'A191RL1Q225SBEA' and isinstance(stats, dict)), None)
            if gdp_growth:
                trend_interp = gdp_growth.get('trend_interpretation', '')
                latest_value = gdp_growth.get('latest_value', 0)
                insights.append(f"GDP 실질성장률: {latest_value:.1f}%, {trend_interp}")
                
            retail_sales = next((stats for ind, stats in data.items() if ind == 'RSAFS' and isinstance(stats, dict)), None)
            if retail_sales:
                trend_interp = retail_sales.get('trend_interpretation', '')
                latest_value = retail_sales.get('latest_value', 0)
                insights.append(f"소매판매액: {latest_value:.1f}%, {trend_interp}")
                
            mfg_employment = next((stats for ind, stats in data.items() if ind == 'MANEMP' and isinstance(stats, dict)), None)
            if mfg_employment:
                trend_interp = mfg_employment.get('trend_interpretation', '')
                latest_value = mfg_employment.get('latest_value', 0)
                insights.append(f"제조업 고용지수: {latest_value:.1f}, {trend_interp}")
                
            ppi = next((stats for ind, stats in data.items() if ind == 'PPIFIS' and isinstance(stats, dict)), None)
            if ppi:
                trend_interp = ppi.get('trend_interpretation', '')
                latest_value = ppi.get('latest_value', 0)
                insights.append(f"생산자물가지수: {latest_value:.1f}%, {trend_interp}")
        
        elif category == AnalysisCategory.FINANCIAL_RISK:
            vix = next((stats for ind, stats in data.items() if ind == 'VIXCLS' and isinstance(stats, dict)), None)
            if vix:
                risk_level = vix.get('risk_level', '보통')
                insights.append(f"시장 변동성(VIX) 위험도: {risk_level}")
        
        # 추가 카테고리별 인사이트는 필요시 확장 가능
        
        return insights
    
    def _generate_category_recommendations(self, category: AnalysisCategory, data: Dict[str, Any], 
                                         high_risk_indicators: List[str]) -> List[str]:
        """Generate category-specific recommendations."""
        recommendations = []
        
        if high_risk_indicators:
            recommendations.append(f"{', '.join(high_risk_indicators)} 지표를 중점 모니터링하세요")
        
        # 카테고리별 맞춤 권고사항
        if category == AnalysisCategory.GROWTH_EMPLOYMENT:
            recommendations.extend([
                "고용시장 동향과 GDP 성장률 변화를 주시하세요", 
                "GDP 실질성장률의 분기별 변화와 지속성을 면밀히 모니터링하세요",
                "경기 선행지표들의 변화 패턴을 분석하세요"
            ])
        elif category == AnalysisCategory.INFLATION_MONETARY:
            recommendations.extend([
                "연준 정책 변화와 인플레이션 기대치를 모니터링하세요",
                "수익률곡선의 형태 변화에 주목하세요"
            ])
        elif category == AnalysisCategory.FINANCIAL_RISK:
            recommendations.extend([
                "시장 변동성과 신용 스프레드 확대에 대비하세요",
                "소비자 심리 변화가 소비에 미치는 영향을 분석하세요"
            ])
        
        recommendations.append("정기적인 데이터 업데이트를 통해 추세 변화를 파악하세요")
        
        return recommendations
    
    def _format_analysis_result(
        self, 
        category: AnalysisCategory, 
        llm_insights: Dict[str, Any],
        processed_data: Dict[str, Any]
    ) -> AnalysisResult:
        """Format the complete analysis result."""
        
        # 데이터 품질 점수 계산
        data_quality = self._calculate_data_quality(processed_data)
        
        # TrendAnalysis 객체 생성
        trend_data = llm_insights.get("trend_analysis", {})
        trend_analysis = TrendAnalysis(
            direction=trend_data.get("direction", "불확실"),
            strength=trend_data.get("strength", "보통"),
            confidence=float(trend_data.get("confidence", 0.5)),
            key_points=trend_data.get("key_points", [])
        )
        
        # RiskAssessment 객체 생성
        risk_data = llm_insights.get("risk_assessment", {})
        risk_assessment = RiskAssessment(
            level=risk_data.get("level", "보통"),
            factors=risk_data.get("factors", []),
            outlook=risk_data.get("outlook", "중립적")
        )
        
        return AnalysisResult(
            category=category.value,
            summary=llm_insights.get("summary", "분석 결과를 생성하지 못했습니다."),
            key_insights=llm_insights.get("key_insights", []),
            trend_analysis=trend_analysis,
            risk_assessment=risk_assessment,
            recommendations=llm_insights.get("recommendations", []),
            data_quality=data_quality,
            analysis_timestamp=datetime.now()
        )
    
    def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """Calculate overall data quality score (0.0 - 1.0)."""
        if not data:
            return 0.0
        
        quality_scores = []
        
        for indicator, stats in data.items():
            if not isinstance(stats, dict):
                continue
            
            # Get individual indicator quality score
            data_quality_info = stats.get('data_quality', {})
            indicator_score = data_quality_info.get('score', 0.5)
            
            # Weight by data points availability
            data_points = stats.get('data_points', 0)
            if data_points == 0:
                indicator_score = 0.0
            elif data_points < 5:
                indicator_score *= 0.5  # Penalize insufficient data
            
            quality_scores.append(indicator_score)
        
        if not quality_scores:
            return 0.0
        
        # Return weighted average
        return sum(quality_scores) / len(quality_scores)
    
    def _create_fallback_result(self, category: AnalysisCategory, error_msg: str) -> AnalysisResult:
        """Create fallback result when analysis fails."""
        return AnalysisResult(
            category=category.value,
            summary=f"데이터 분석 중 오류가 발생했습니다: {error_msg}",
            key_insights=["분석 오류로 인해 결과를 제공할 수 없습니다"],
            trend_analysis=TrendAnalysis(
                direction="불확실",
                strength="알 수 없음", 
                confidence=0.0,
                key_points=["분석 실패"]
            ),
            risk_assessment=RiskAssessment(
                level="알 수 없음",
                factors=["분석 오류"],
                outlook="불확실"
            ),
            recommendations=["시스템 관리자에게 문의하시기 바랍니다"],
            data_quality=0.0,
            analysis_timestamp=datetime.now()
        )


# Global service instance
economic_analysis_service = EconomicAnalysisService()


def get_economic_analysis_service() -> EconomicAnalysisService:
    """Get the global economic analysis service instance."""
    return economic_analysis_service