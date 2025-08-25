"""Economic events and major crisis markers for economic charts."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Types of economic events."""
    CRISIS = "crisis"
    RECESSION = "recession"
    POLICY_CHANGE = "policy_change"
    MARKET_EVENT = "market_event"
    GEOPOLITICAL = "geopolitical"
    PANDEMIC = "pandemic"


class EventSeverity(Enum):
    """Severity levels for economic events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EconomicEvent:
    """Economic event marker for charts."""
    date: datetime  # Original exact date
    title: str
    description: str
    event_type: EventType
    severity: EventSeverity
    color: str
    icon: str
    impact_duration_months: Optional[int] = None
    related_indicators: Optional[List[str]] = None
    priority: int = 5  # Higher number = higher priority (1-10 scale)
    
    @property
    def chart_date(self) -> datetime:
        """Date for chart display (1st of the month)"""
        return datetime(self.date.year, self.date.month, 1)
    
    @property
    def detail_date(self) -> datetime:
        """Detailed exact date for tooltips and precise positioning"""
        return self.date


class EconomicService:
    """Service for providing major economic events and crisis markers."""
    # Major economic events and crises
    MAJOR_EVENTS = [
        # 1970s - Oil Crisis
        EconomicEvent(
            date=datetime(1973, 10, 1),
            title="1973년 오일 쇼크",
            description="OPEC의 석유 금수 조치로 유가가 4배 급등",
            event_type=EventType.CRISIS,
            severity=EventSeverity.CRITICAL,
            color="#8B4513",
            icon="⛽",
            impact_duration_months=24,
            related_indicators=["DCOILWTICO", "CPIAUCSL", "UNRATE", "NYUCSFRCONDOSMSAMID"]
        ),
        EconomicEvent(
            date=datetime(1979, 6, 1),
            title="1979년 오일 쇼크",
            description="이란 혁명으로 석유 공급이 중단됨",
            event_type=EventType.CRISIS,
            severity=EventSeverity.HIGH,
            color="#8B4513",
            icon="⛽",
            impact_duration_months=18,
            related_indicators=["DCOILWTICO", "CPIAUCSL", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 1980년대 - 볼커 쇼크 & 경기침체
        EconomicEvent(
            date=datetime(1980, 3, 1),
            title="볼커 쇼크",
            description="연준 의장 폴 볼커가 인플레이션 억제를 위해 금리 대폭 인상",
            event_type=EventType.POLICY_CHANGE,
            severity=EventSeverity.CRITICAL,
            color="#FF4500",
            icon="📈",
            impact_duration_months=36,
            related_indicators=["FEDFUNDS", "CPIAUCSL", "UNRATE", "NYUCSFRCONDOSMSAMID"]
        ),
        EconomicEvent(
            date=datetime(1981, 7, 1),
            title="1980년대 초반 경기침체",
            description="긴축 통화정책으로 인한 심각한 경기침체",
            event_type=EventType.RECESSION,
            severity=EventSeverity.CRITICAL,
            color="#B22222",
            icon="📉",
            impact_duration_months=24,
            related_indicators=["GDP", "UNRATE", "INDPRO", "FEDFUNDS",  "TCU", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 1987년 - 블랙 먼데이
        EconomicEvent(
            date=datetime(1987, 10, 19),
            title="블랙 먼데이",
            description="주식시장이 하루 만에 22% 폭락",
            event_type=EventType.MARKET_EVENT,
            severity=EventSeverity.HIGH,
            color="#000000",
            icon="💥",
            impact_duration_months=6,
            related_indicators=["VIXCLS", "FEDFUNDS", "DGS10", "UNRATE", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 1990년대 - 걸프전 & 경기침체
        EconomicEvent(
            date=datetime(1990, 8, 1),
            title="걸프전 & 1990년대 경기침체",
            description="걸프전과 S&L 위기로 경기침체 발생",
            event_type=EventType.GEOPOLITICAL,
            severity=EventSeverity.HIGH,
            color="#8B0000",
            icon="⚔️",
            impact_duration_months=12,
            related_indicators=["GDP", "UNRATE", "DCOILWTICO", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 1997-1998년 - 아시아 외환위기
        EconomicEvent(
            date=datetime(1997, 7, 1),
            title="아시아 외환위기",
            description="아시아 각국의 통화 평가절하가 확산",
            event_type=EventType.CRISIS,
            severity=EventSeverity.HIGH,
            color="#DC143C",
            icon="🌏",
            impact_duration_months=18,
            related_indicators=["VIXCLS", "DGS10", "FEDFUNDS", "DEXUSEU", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2000년 - 닷컴 버블 붕괴
        EconomicEvent(
            date=datetime(2000, 3, 1),
            title="닷컴 버블 붕괴",
            description="기술주 버블 붕괴",
            event_type=EventType.MARKET_EVENT,
            severity=EventSeverity.HIGH,
            color="#4B0082",
            icon="💻",
            impact_duration_months=24,
            related_indicators=["VIXCLS", "UNRATE", "FEDFUNDS",  "INDPRO", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2001년 - 9/11 테러
        EconomicEvent(
            date=datetime(2001, 9, 11),
            title="9/11 테러",
            description="테러 공격으로 시장과 경제에 충격",
            event_type=EventType.GEOPOLITICAL,
            severity=EventSeverity.CRITICAL,
            color="#000000",
            icon="🏢",
            impact_duration_months=12,
            related_indicators=["VIXCLS", "UNRATE", "GDP", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2007-2009년 - 글로벌 금융위기
        EconomicEvent(
            date=datetime(2007, 8, 1),
            title="서브프라임 위기 시작",
            description="서브프라임 모기지 위기로 글로벌 금융위기 촉발",
            event_type=EventType.CRISIS,
            severity=EventSeverity.CRITICAL,
            color="#8B0000",
            icon="🏠",
            impact_duration_months=6,
            related_indicators=["CSUSHPISA", "MORTGAGE30US", "VIXCLS", "NYUCSFRCONDOSMSAMID"],
            priority=9
        ),
        EconomicEvent(
            date=datetime(2008, 9, 15),
            title="리먼 브라더스 파산",
            description="투자은행 파산으로 글로벌 금융위기 심화",
            event_type=EventType.CRISIS,
            severity=EventSeverity.CRITICAL,
            color="#8B0000",
            icon="🏦",
            impact_duration_months=36,
            related_indicators=["VIXCLS", "UNRATE", "GDP", "FEDFUNDS", "NYUCSFRCONDOSMSAMID"],
            priority=10  # 최고 우선순위
        ),
        EconomicEvent(
            date=datetime(2008, 12, 1),
            title="글로벌 대침체",
            description="대공황 이후 최악의 경기침체",
            event_type=EventType.RECESSION,
            severity=EventSeverity.CRITICAL,
            color="#8B0000",
            icon="📉",
            impact_duration_months=30,
            related_indicators=["GDP", "UNRATE", "PAYEMS", "INDPRO", "NYUCSFRCONDOSMSAMID"],
            priority=9
        ),
        
        # 2010년 - 유럽 재정위기
        EconomicEvent(
            date=datetime(2010, 5, 1),
            title="유럽 재정위기",
            description="유럽 국가들의 주권부채 위기",
            event_type=EventType.CRISIS,
            severity=EventSeverity.HIGH,
            color="#4682B4",
            icon="🇪🇺",
            impact_duration_months=36,
            related_indicators=["VIXCLS", "DGS10", "FEDFUNDS", "GFDEGDQ188S", "DEXUSEU", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2015년 - 중국 증시 폭락
        EconomicEvent(
            date=datetime(2015, 8, 1),
            title="중국 증시 폭락",
            description="중국 증시 변동성이 글로벌 시장에 영향",
            event_type=EventType.MARKET_EVENT,
            severity=EventSeverity.MEDIUM,
            color="#DC143C",
            icon="🇨🇳",
            impact_duration_months=6,
            related_indicators=["VIXCLS", "DCOILWTICO", "DEXCHUS",  "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2018년 - 미중 무역전쟁
        EconomicEvent(
            date=datetime(2018, 3, 1),
            title="미중 무역전쟁",
            description="미국과 중국 간 무역 갈등 심화",
            event_type=EventType.GEOPOLITICAL,
            severity=EventSeverity.MEDIUM,
            color="#FFA500",
            icon="🛡️",
            impact_duration_months=24,
            related_indicators=["VIXCLS", "BOPGSTB",  "INDPRO", "DEXCHUS", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2020년 - 코로나19 팬데믹
        EconomicEvent(
            date=datetime(2020, 3, 1),
            title="코로나19 팬데믹",
            description="전 세계적 팬데믹으로 경제 대혼란",
            event_type=EventType.PANDEMIC,
            severity=EventSeverity.CRITICAL,
            color="#8B0000",
            icon="🦠",
            impact_duration_months=36,
            related_indicators=["UNRATE", "GDP", "FEDFUNDS", "VIXCLS", "M2SL", "NYUCSFRCONDOSMSAMID"],
            priority=10  # 최고 우선순위
        ),
        EconomicEvent(
            date=datetime(2020, 3, 23),
            title="코로나19 증시 폭락",
            description="팬데믹 공포로 사상 최단기 약세장 진입",
            event_type=EventType.MARKET_EVENT,
            severity=EventSeverity.CRITICAL,
            color="#8B0000",
            icon="💥",
            impact_duration_months=12,
            related_indicators=["VIXCLS", "NYUCSFRCONDOSMSAMID"],
            priority=9
        ),
        
        # 2021-2022년 - 인플레이션 급등
        EconomicEvent(
            date=datetime(2021, 6, 1),
            title="인플레이션 급등 시작",
            description="공급망 혼란과 재정 부양책으로 인플레이션 상승",
            event_type=EventType.POLICY_CHANGE,
            severity=EventSeverity.HIGH,
            color="#FF6347",
            icon="📈",
            impact_duration_months=24,
            related_indicators=["CPIAUCSL", "FEDFUNDS", "M2SL", "DCOILWTICO",  "TCU", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2022년 - 우크라이나 전쟁
        EconomicEvent(
            date=datetime(2022, 2, 24),
            title="러시아-우크라이나 전쟁",
            description="우크라이나 전쟁으로 에너지·식량 가격 급등",
            event_type=EventType.GEOPOLITICAL,
            severity=EventSeverity.HIGH,
            color="#8B0000",
            icon="⚔️",
            impact_duration_months=24,
            related_indicators=["DCOILWTICO", "CPIAUCSL", "VIXCLS", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2022년 - 연준 금리 인상
        EconomicEvent(
            date=datetime(2022, 3, 16),
            title="연준의 공격적 금리 인상",
            description="연방준비제도가 공격적으로 금리 인상 시작",
            event_type=EventType.POLICY_CHANGE,
            severity=EventSeverity.HIGH,
            color="#FF4500",
            icon="📈",
            impact_duration_months=18,
            related_indicators=["FEDFUNDS", "DGS10", "DGS2", "MORTGAGE30US", "NYUCSFRCONDOSMSAMID"]
        ),
        
        # 2023년 - 지역 은행 위기
        EconomicEvent(
            date=datetime(2023, 3, 10),
            title="미국 지역 은행 위기",
            description="실리콘밸리은행 등 지역 은행 파산",
            event_type=EventType.CRISIS,
            severity=EventSeverity.MEDIUM,
            color="#8B4513",
            icon="🏦",
            impact_duration_months=6,
            related_indicators=["VIXCLS", "FEDFUNDS", "DGS10", "DGS2", "MORTGAGE30US", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2023년 - 미국 부채한도 협상 교착
        EconomicEvent(
            date=datetime(2023, 5, 27),
            title="미국 부채한도 협상 교착",
            description="미국 부채한도 정치적 교착으로 디폴트 위험 증가",
            event_type=EventType.GEOPOLITICAL,
            severity=EventSeverity.HIGH,
            color="#FFD700",
            icon="💰",
            impact_duration_months=2,
            related_indicators=["VIXCLS", "FEDFUNDS", "DGS10", "GFDEGDQ188S", "GFDEBTN", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2023년 - AI 주식 랠리
        EconomicEvent(
            date=datetime(2023, 6, 1),
            title="AI 주식 랠리",
            description="엔비디아 등 AI 관련 기술주 급등",
            event_type=EventType.MARKET_EVENT,
            severity=EventSeverity.HIGH,
            color="#00BFFF",
            icon="🤖",
            impact_duration_months=12,
            related_indicators=["VIXCLS",  "INDPRO", "TCU", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2023년 - 글로벌 인플레이션 완화
        EconomicEvent(
            date=datetime(2023, 9, 1),
            title="글로벌 인플레이션 완화",
            description="글로벌 인플레이션 완화, 중앙은행 금리 인상 중단",
            event_type=EventType.POLICY_CHANGE,
            severity=EventSeverity.MEDIUM,
            color="#32CD32",
            icon="🟢",
            impact_duration_months=6,
            related_indicators=["CPIAUCSL", "FEDFUNDS", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2024년 - 홍해 해상운송 위기
        EconomicEvent(
            date=datetime(2024, 1, 15),
            title="홍해 해상운송 위기",
            description="홍해 선박 공격으로 글로벌 공급망 차질",
            event_type=EventType.GEOPOLITICAL,
            severity=EventSeverity.HIGH,
            color="#FF0000",
            icon="🚢",
            impact_duration_months=4,
            related_indicators=["DCOILWTICO", "CPIAUCSL", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2024년 - 미국 대선 불확실성
        EconomicEvent(
            date=datetime(2024, 11, 5),
            title="미국 대선 불확실성",
            description="미국 대선으로 시장 변동성 및 정책 불확실성 증가",
            event_type=EventType.GEOPOLITICAL,
            severity=EventSeverity.HIGH,
            color="#00008B",
            icon="🇺🇸",
            impact_duration_months=2,
            related_indicators=["VIXCLS", "FEDFUNDS", "DGS10", "GFDEGDQ188S", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2024년 - 고금리 장기화
        EconomicEvent(
            date=datetime(2024, 12, 1),
            title="고금리 장기화",
            description="중앙은행이 인플레이션 억제를 위해 고금리 유지",
            event_type=EventType.POLICY_CHANGE,
            severity=EventSeverity.HIGH,
            color="#FF4500",
            icon="📈",
            impact_duration_months=12,
            related_indicators=["FEDFUNDS", "DGS10", "DGS2", "MORTGAGE30US", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2025년 - 세계 증시 급락 (주식 쇼크)
        EconomicEvent(
            date=datetime(2025, 4, 2),
            title="세계 증시 급락",
            description="미국의 새로운 관세 정책 발표 후 글로벌 증시 급락",
            event_type=EventType.MARKET_EVENT,
            severity=EventSeverity.HIGH,
            color="#FF1493",
            icon="📉",
            impact_duration_months=3,
            related_indicators=["VIXCLS",  "INDPRO", "BOPGSTB", "NYUCSFRCONDOSMSAMID"]
        ),
        # 2025년 - 연준의 금리 딜레마
        EconomicEvent(
            date=datetime(2025, 5, 1),
            title="연준의 금리 딜레마",
            description="AI 붐과 주택시장 침체 사이에서 연준이 금리 정책 결정에 갈등",
            event_type=EventType.POLICY_CHANGE,
            severity=EventSeverity.MEDIUM,
            color="#FFD700",
            icon="🏦",
            impact_duration_months=6,
            related_indicators=["FEDFUNDS", "MORTGAGE30US", "NYUCSFRCONDOSMSAMID"]
        ),
    ]
    
    def get_events_in_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        event_types: Optional[List[EventType]] = None,
        min_severity: Optional[EventSeverity] = None
    ) -> List[Dict[str, Any]]:
        """Get economic events within a date range."""
        filtered_events = []
        
        for event in self.MAJOR_EVENTS:
            # Check date range
            if not (start_date <= event.date <= end_date):
                continue
            
            # Filter by event types if specified
            if event_types and event.event_type not in event_types:
                continue
            
            # Filter by minimum severity if specified
            if min_severity:
                severity_order = {
                    EventSeverity.LOW: 1,
                    EventSeverity.MEDIUM: 2,
                    EventSeverity.HIGH: 3,
                    EventSeverity.CRITICAL: 4
                }
                if severity_order[event.severity] < severity_order[min_severity]:
                    continue
            
            filtered_events.append({
                "date": event.chart_date.isoformat(),  # 1st of month for chart positioning
                "detail_date": event.detail_date.isoformat(),  # Exact date for tooltips
                "title": event.title,
                "description": event.description,
                "type": event.event_type.value,
                "severity": event.severity.value,
                "color": event.color,
                "icon": event.icon,
                "impact_duration_months": event.impact_duration_months,
                "related_indicators": event.related_indicators or [],
                "priority": event.priority
            })
        
        # Sort by date
        filtered_events.sort(key=lambda x: x["date"])
        return filtered_events
    
    def get_events_for_indicator(
        self, 
        indicator: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get events that are relevant to a specific economic indicator."""
        relevant_events = []
        
        for event in self.MAJOR_EVENTS:
            # Check if this event is relevant to the indicator
            if event.related_indicators and indicator in event.related_indicators:
                # Check date range if provided
                if start_date and event.date < start_date:
                    continue
                if end_date and event.date > end_date:
                    continue
                
                relevant_events.append({
                    "date": event.chart_date.isoformat(),  # 1st of month for chart positioning
                    "detail_date": event.detail_date.isoformat(),  # Exact date for tooltips
                    "title": event.title,
                    "description": event.description,
                    "type": event.event_type.value,
                    "severity": event.severity.value,
                    "color": event.color,
                    "icon": event.icon,
                    "impact_duration_months": event.impact_duration_months,
                    "related_indicators": event.related_indicators or [],
                    "priority": event.priority
                })
        
        # Sort by date
        relevant_events.sort(key=lambda x: x["date"])
        return relevant_events
    
    def get_all_event_types(self) -> List[str]:
        """Get all available event types."""
        return [event_type.value for event_type in EventType]
    
    def get_all_severity_levels(self) -> List[str]:
        """Get all available severity levels."""
        return [severity.value for severity in EventSeverity]


# Global service instance
economic_events_service = EconomicService()


def get_economic_service() -> EconomicService:
    """Get the global economic events service instance."""
    return economic_events_service