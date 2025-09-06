"""Portfolio database seeder service for famous investors' portfolios."""

import logging
from typing import Dict, Any
from datetime import datetime

from src.models.portfolio import Portfolio, Base
from src.models.user import User
from src.core.database import get_database_manager
from src.core.config import get_settings
logger = logging.getLogger(__name__)


class PortfolioSeeder:
    """Portfolio database seeder with famous investors' portfolios."""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.settings = get_settings()
        
        # 거장들의 포트폴리오 데이터
        self.famous_portfolios = {
            
            "warren_buffett": {
                "name": "버핏의 가치투자 포트폴리오(예시)",
                "description": "워렌 버핏의 장기 가치투자 철학을 바탕으로 한 포트폴리오. 우량 기업에 집중 투자하며 브랜드 파워와 경제적 해자가 있는 기업들로 구성",
                "tickers": ["AAPL", "KO", "BAC", "AXP", "CVX", "KHC", "MCO", "OXY"],
                "ticker_weights": {
                    "AAPL": 0.45,  # 애플 집중투자 (버핏의 실제 스타일)
                    "KO": 0.15,    # 코카콜라 장기보유
                    "BAC": 0.12,   # 뱅크오브아메리카
                    "AXP": 0.08,   # 아메리칸익스프레스
                    "CVX": 0.07,   # 셰브론
                    "KHC": 0.05,   # 크래프트하인츠
                    "MCO": 0.04,   # 무디스
                    "OXY": 0.04    # 옥시덴탈 페트롤리움
                },
                "optimization_method": "max_sharpe",
                "rebalance_frequency": "quarterly"  # 버핏은 장기투자
            },
            "ray_dalio": {
                "name": "올 웨더 포트폴리오(예시)",
                "description": "레이 달리오의 브리지워터가 개발한 모든 경제 환경에서 안정적인 수익을 추구하는 포트폴리오. 주식, 채권, 원자재에 분산 투자",
                "tickers": ["VTI", "TLT", "IEF", "VNQ", "DBC", "GLD", "VEA", "VWO"],
                "ticker_weights": {
                    "VTI": 0.30,   # 미국 전체 주식시장
                    "TLT": 0.25,   # 장기 국채 (인플레이션 헤지)
                    "IEF": 0.15,   # 중기 국채
                    "VNQ": 0.10,   # 부동산 투자신탁
                    "DBC": 0.08,   # 원자재
                    "GLD": 0.07,   # 금 (안전자산)
                    "VEA": 0.03,   # 선진국 주식
                    "VWO": 0.02    # 신흥국 주식
                },
                "optimization_method": "risk_parity",
                "rebalance_frequency": "monthly"
            },
            "peter_lynch": {
                "name": "성장주 발굴 포트폴리오(예시)",
                "description": "피터 린치의 성장주 투자 철학을 반영한 포트폴리오. PEG 비율이 낮은 성장주와 소비자가 직접 이해할 수 있는 기업들로 구성",
                "tickers": ["MSFT", "GOOGL", "NVDA", "AMZN", "TSLA", "META", "NFLX", "AMD"],
                "ticker_weights": {
                    "MSFT": 0.20,  # 마이크로소프트 (안정적 성장)
                    "GOOGL": 0.18, # 구글 (검색 독점)
                    "NVDA": 0.15,  # 엔비디아 (AI 성장)
                    "AMZN": 0.15,  # 아마존 (클라우드+커머스)
                    "TSLA": 0.12,  # 테슬라 (전기차 혁신)
                    "META": 0.08,  # 메타 (소셜미디어)
                    "NFLX": 0.07,  # 넷플릭스 (스트리밍)
                    "AMD": 0.05    # AMD (반도체)
                },
                "optimization_method": "max_sharpe",
                "rebalance_frequency": "monthly"
                
            },
            "john_bogle": {
                "name": "보글헤드 3펀드 포트폴리오(예시)",
                "description": "존 보글의 인덱스 투자 철학을 바탕으로 한 단순하고 효과적인 포트폴리오. 전체 주식시장, 국제주식, 채권으로만 구성",
                "tickers": ["VTI", "VXUS", "BND"],
                "ticker_weights": {
                    "VTI": 0.60,   # 미국 전체 주식시장 (60%)
                    "VXUS": 0.20,  # 미국 외 국제주식 (20%) 
                    "BND": 0.20    # 미국 채권시장 (20%)
                },
                "optimization_method": "min_volatility",
                "rebalance_frequency": "quarterly"
            }
            
        }
    
    async def seed_database(self, force_refresh: bool = False) -> Dict[str, Any]:
        """데이터베이스에 거장들의 포트폴리오 시드 데이터 입력."""
        try:
            # DB 테이블 생성
            Base.metadata.create_all(bind=self.db_manager.engine)
            
            # 이미 데이터가 있는지 확인
            if not force_refresh:
                with self.db_manager.get_session() as session:
                    count = session.query(Portfolio).filter(
                        Portfolio.name.like("%포트폴리오")
                    ).count()
                    if count >= len(self.famous_portfolios):
                        logger.info(f"✅ Portfolio database already seeded with {count} famous portfolios")
                        return {'status': 'already_seeded', 'count': count}
            
            # Admin 유저 확인 (이미 존재해야 함)
            with self.db_manager.get_session() as session:
                admin_user = session.query(User).filter(
                    User.username == self.settings.ADMIN_USERNAME
                ).first()
                
                if not admin_user:
                    logger.error(f"Admin user not found: {self.settings.ADMIN_USERNAME}")
                    return {'status': 'error', 'error': 'Admin user not found'}
                
                admin_user_id = admin_user.id
            
            logger.info(f"🌱 Seeding database with {len(self.famous_portfolios)} famous portfolios...")
            
            successful_inserts = 0
            failed_inserts = 0
            
            with self.db_manager.get_session() as session:
                for portfolio_key, portfolio_data in self.famous_portfolios.items():
                    try:
                        # 기존 포트폴리오 확인
                        existing = session.query(Portfolio).filter(
                            Portfolio.name == portfolio_data["name"],
                            Portfolio.user_id == admin_user_id
                        ).first()
                        
                        if existing and not force_refresh:
                            continue
                        
                        if existing:
                            # 업데이트
                            existing.description = portfolio_data["description"]
                            existing.tickers = portfolio_data["tickers"]
                            existing.ticker_weights = portfolio_data.get("ticker_weights")
                            existing.optimization_method = portfolio_data["optimization_method"]
                            existing.rebalance_frequency = portfolio_data["rebalance_frequency"]

                            existing.updated_at = datetime.now()
                        else:
                            # 새로 생성 - 제공된 코드 패턴에 맞춤
                            db_portfolio = Portfolio(
                                user_id=admin_user_id,
                                name=portfolio_data["name"],
                                description=portfolio_data["description"],
                                tickers=portfolio_data["tickers"],
                                ticker_weights=portfolio_data.get("ticker_weights"),
                                optimization_method=portfolio_data["optimization_method"],
                                rebalance_frequency=portfolio_data["rebalance_frequency"],
                                is_active=True
                            )
                            session.add(db_portfolio)
                        
                        successful_inserts += 1
                        logger.info(f"✅ Added portfolio: {portfolio_data['name']}")
                        
                    except Exception as e:
                        failed_inserts += 1
                        logger.error(f"❌ Error adding portfolio {portfolio_key}: {e}")
                
                session.commit()
            
            logger.info(f"✅ Portfolio seeding completed! Success: {successful_inserts}, Failed: {failed_inserts}")
            
            return {
                'status': 'completed',
                'successful_inserts': successful_inserts,
                'failed_inserts': failed_inserts,
                'total_processed': successful_inserts + failed_inserts
            }
            
        except Exception as e:
            logger.error(f"❌ Error during portfolio seeding: {e}")
            return {'status': 'error', 'error': str(e)}


# 전역 seeder 인스턴스
portfolio_seeder = PortfolioSeeder()


async def seed_portfolio_database_on_startup(force_refresh: bool = False) -> Dict[str, Any]:
    """FastAPI 시작시 호출되는 포트폴리오 데이터베이스 시딩 함수."""
    return await portfolio_seeder.seed_database(force_refresh)