"""Economic analysis schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TrendAnalysisSchema(BaseModel):
    """Trend analysis schema."""
    direction: str = Field(..., description="트렌드 방향: 증가/감소/횡보")
    strength: str = Field(..., description="트렌드 강도: 강함/보통/약함")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도 (0.0-1.0)")
    key_points: List[str] = Field(..., description="주요 트렌드 포인트")


class RiskAssessmentSchema(BaseModel):
    """Risk assessment schema."""
    level: str = Field(..., description="위험 수준: 낮음/보통/높음/매우높음")
    factors: List[str] = Field(..., description="위험 요인들")
    outlook: str = Field(..., description="전망: 긍정적/중립적/부정적")


class EconomicAnalysisRequest(BaseModel):
    """Economic analysis request schema."""
    category: str = Field(..., description="분석 카테고리")
    time_range: str = Field(..., description="시간 범위: 1Y/5Y/10Y/20Y")
    start_date: str = Field(..., description="시작 날짜 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="종료 날짜 (YYYY-MM-DD)")


class EconomicAnalysisResponse(BaseModel):
    """Economic analysis response schema."""
    category: str = Field(..., description="분석 카테고리")
    summary: str = Field(..., description="전체 요약")
    key_insights: List[str] = Field(..., description="핵심 인사이트")
    trend_analysis: TrendAnalysisSchema = Field(..., description="트렌드 분석")
    risk_assessment: RiskAssessmentSchema = Field(..., description="위험 평가")
    recommendations: List[str] = Field(..., description="권고사항")
    data_quality: float = Field(..., ge=0.0, le=1.0, description="데이터 품질 점수")
    analysis_timestamp: datetime = Field(..., description="분석 시점")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }