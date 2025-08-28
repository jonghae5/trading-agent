"""Economic data analysis service using LLM for insights generation."""

import logging
import json
import asyncio
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
        AnalysisCategory.GROWTH_EMPLOYMENT: ['GDP', 'INDPRO', 'TCU', 'UNRATE', 'PAYEMS', 'ICSA'],
        AnalysisCategory.INFLATION_MONETARY: ['CPIAUCSL', 'PCEPILFE', 'T5YIE', 'FEDFUNDS', 'DGS10', 'DGS2', 'T10Y2Y'],
        AnalysisCategory.FINANCIAL_RISK: ['NFCI', 'BAMLH0A0HYM2', 'BAA', 'VIXCLS', 'UMCSENT'],
        AnalysisCategory.REALESTATE_DEBT: ['MORTGAGE30US', 'NYUCSFRCONDOSMSAMID', 'GFDEBTN', 'GFDEGDQ188S', 'NCBDBIQ027S'],
        AnalysisCategory.FISCAL_GLOBAL: ['FYFSGDA188S', 'DTWEXBGS', 'DGS30', 'DCOILWTICO', 'BOPGSTB']
    }
    
    def __init__(self):
        self.fred_service = get_fred_service()
        self.openai_api_key = settings.OPENAI_API_KEY
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        
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
                    'trend': self._calculate_trend(values),
                    'volatility': self._calculate_volatility(values),
                    'latest_date': observations[-1].date.isoformat()
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
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (coefficient of variation)."""
        if len(values) < 2:
            return 0.0
            
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
            
        std_val = statistics.stdev(values)
        return (std_val / abs(mean_val)) * 100
    
    async def _generate_llm_insights(
        self, 
        category: AnalysisCategory, 
        processed_data: Dict[str, Any], 
        raw_data: Dict[str, List[FredObservation]],
        time_range: str
    ) -> Dict[str, Any]:
        """Generate insights using LLM."""
        try:
            # 프롬프트 생성
            prompt = self._generate_category_prompt(category, processed_data, raw_data, time_range)
            
            # LLM API 호출 (OpenAI 우선, 실패시 Anthropic)
            if self.openai_api_key:
                try:
                    response = await self._call_openai_api(prompt)
                    return self._parse_llm_response(response)
                except Exception as e:
                    logger.warning(f"OpenAI API failed, trying Anthropic: {e}")
            
            # LLM 사용 불가시 기본 분석
            logger.warning("No LLM APIs available, using fallback analysis")
            return self._generate_fallback_insights(category, processed_data)
            
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
            AnalysisCategory.GROWTH_EMPLOYMENT: "성장 & 고용 지표 (GDP, 산업생산, 실업률, 일자리)",
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
            
            line = f"- {indicator}: 최신값 {latest_value} ({latest_date}), "
            line += f"전기대비 {change_pct:+.1f}% 변화{change_emphasis}, "
            line += f"트렌드: {trend}, 변동성: {volatility:.1f}%"
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
- 최신 GDP 성장률 변화가 향후 고용시장에 미칠 파급효과 분석
- 최근 실업률과 일자리 증가 트렌드가 소비와 경기회복에 미치는 영향
- 산업생산지수 최신 변화가 향후 제조업과 실물경제에 주는 신호 해석
- 최근 고용지표 개선/악화가 연준 정책과 인플레이션에 미칠 영향 예측
""",
            AnalysisCategory.INFLATION_MONETARY: """
특별 고려사항 - 최근 동향과 미래 영향 중심:
- 최신 인플레이션 데이터가 향후 연준 정책 결정에 미칠 영향 분석
- 최근 수익률곡선 변화가 향후 금융시장과 경기에 주는 신호 해석
- 최근 인플레이션 기대치 변화가 실제 물가와 소비에 미칠 파급효과
- 최신 연준 기준금리 변화가 향후 3-12개월 경제활동에 미칠 영향 예측
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
        """Generate basic insights when LLM is not available."""
        # 데이터 기반 기본 분석
        positive_trends = sum(1 for stats in data.values() 
                            if isinstance(stats, dict) and stats.get('trend') == '상승')
        negative_trends = sum(1 for stats in data.values() 
                            if isinstance(stats, dict) and stats.get('trend') == '하락')
        
        overall_trend = "상승" if positive_trends > negative_trends else "하락" if negative_trends > positive_trends else "횡보"
        
        return {
            "summary": f"{self._get_category_description(category)} 분석 결과, 전반적인 트렌드는 {overall_trend} 방향입니다.",
            "key_insights": [
                f"총 {len(data)}개 지표 중 {positive_trends}개가 상승 추세",
                f"데이터 기반 기본 분석 결과 제공",
                "상세 분석을 위해 LLM 서비스 연결이 필요합니다"
            ],
            "trend_analysis": {
                "direction": overall_trend,
                "strength": "보통",
                "confidence": 0.6,
                "key_points": ["기본 통계 분석 기반 결과"]
            },
            "risk_assessment": {
                "level": "보통",
                "factors": ["LLM 분석 불가로 인한 제한적 평가"],
                "outlook": "중립적"
            },
            "recommendations": [
                "LLM API 연결 상태를 확인해주세요",
                "데이터 품질을 개선하여 분석 정확도를 높이세요"
            ]
        }
    
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
        """Calculate data quality score (0.0 - 1.0)."""
        if not data:
            return 0.0
            
        total_indicators = len(data)
        valid_indicators = 0
        
        for indicator, stats in data.items():
            if isinstance(stats, dict) and stats.get('data_points', 0) > 0:
                valid_indicators += 1
        
        return valid_indicators / total_indicators if total_indicators > 0 else 0.0
    
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