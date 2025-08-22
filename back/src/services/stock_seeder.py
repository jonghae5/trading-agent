"""Stock database seeder service for FastAPI startup."""

import logging
import asyncio
import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert

from src.models.stock_universe import Base, StockInfo
from src.core.database import get_database_manager
from src.core.config import settings

logger = logging.getLogger(__name__)


class StockSeeder:
    """Stock database seeder for FastAPI application."""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.db_manager = get_database_manager()
        
        # S&P 500 + 주요 ETF + 인기 종목들 (약 600개)
        self.seed_tickers = {
            # S&P 500 주요 종목들 (시가총액 순)
            'mega_cap': [
                'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'BRK.B', 'META', 'TSLA', 'LLY',
                'V', 'UNH', 'XOM', 'WMT', 'JPM', 'JNJ', 'MA', 'PG', 'HD', 'CVX',
                'ABBV', 'BAC', 'KO', 'AVGO', 'PEP', 'COST', 'TMO', 'MRK', 'ABT', 'ADBE',
                'CRM', 'ACN', 'NFLX', 'AMD', 'LIN', 'CSCO', 'DHR', 'TXN', 'QCOM', 'VZ',
                'PM', 'NKE', 'INTU', 'WFC', 'IBM', 'UPS', 'CAT', 'GS', 'HON', 'MS'
            ],
            
            # Tech 종목들
            'tech': [
                'ORCL', 'NOW', 'UBER', 'SNAP', 'ZOOM', 'SHOP', 'SQ', 'PYPL', 'ROKU', 'PINS',
                'DOCU', 'ZM', 'TEAM', 'OKTA', 'TWLO', 'DDOG', 'SNOW', 'PLTR', 'NET', 'CRWD',
                'INTC', 'MRVL', 'KLAC', 'LRCX', 'ADI', 'AMAT', 'SNPS', 'CDNS', 'FTNT', 'PANW'
            ],
            
            # 주요 ETF들
            'etfs': [
                'SPY', 'QQQ', 'VTI', 'IWM', 'VOO', 'VEA', 'IEFA', 'VWO', 'VTV', 'VUG',
                'IEMG', 'IJH', 'VB', 'VXUS', 'BND', 'AGG', 'VNQ', 'GLD', 'IVV', 'VIG',
                'SCHD', 'XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLB', 'XLU',
                'XLRE', 'VDE', 'VFH', 'VGT', 'VAW', 'VCR', 'VDC', 'VIS', 'VOX', 'VPU',
                'TLT', 'SHY', 'IEF', 'LQD', 'HYG', 'JNK', 'ARKK', 'ARKQ', 'ARKG', 'ARKF'
            ],
            
            # Financial 섹터
            'financial': [
                'C', 'AXP', 'COF', 'USB', 'PNC', 'TFC', 'SCHW', 'BLK', 'SPGI', 'MCO',
                'CB', 'MMC', 'AON', 'ICE', 'CME', 'MSCI', 'ALL', 'TRV', 'AFL', 'PFG'
            ],
            
            # Healthcare 섹터
            'healthcare': [
                'PFE', 'BMY', 'AMGN', 'MDT', 'SYK', 'GILD', 'REGN', 'VRTX', 'ISRG', 'CI',
                'HUM', 'ANTM', 'CVS', 'WBA', 'BAX', 'EW', 'A', 'IQV', 'RMD', 'ILMN',
                'DXCM', 'ALGN', 'MRNA', 'BNTX', 'PFE', 'BIIB', 'ZBH', 'BSX', 'HOLX', 'COO'
            ],
            
            # Consumer 섹터
            'consumer': [
                'AMZN', 'HD', 'MCD', 'SBUX', 'NKE', 'TJX', 'LOW', 'TGT', 'MAR', 'CMG',
                'YUM', 'ROST', 'DIS', 'NFLX', 'CHTR', 'CMCSA', 'EA', 'ATVI', 'LVS', 'MGM'
            ],
            
            # Industrial 섹터
            'industrial': [
                'GE', 'RTX', 'LMT', 'NOC', 'GD', 'BA', 'DE', 'FDX', 'UPS', 'WM',
                'NSC', 'UNP', 'CSX', 'EMR', 'ETN', 'ITW', 'ECL', 'CARR', 'OTIS', 'PWR'
            ],
            
            # Energy 섹터
            'energy': [
                'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'MPC', 'PSX', 'VLO', 'KMI', 'WMB',
                'OKE', 'DVN', 'FANG', 'MRO', 'APA', 'HAL', 'BKR', 'OXY', 'PXD', 'CTRA'
            ],
            
            # 기타 인기 종목들
            'others': [
                'BTC-USD', 'ETH-USD',  # 암호화폐
                'GC=F', 'SI=F', 'CL=F',  # 선물
                '^GSPC', '^DJI', '^IXIC', '^RUT', '^VIX',  # 지수
                'USDKRW=X', 'EURUSD=X', 'USDJPY=X'  # 환율
            ]
        }
    
    def _get_stock_info_sync(self, ticker: str) -> Optional[Dict[str, Any]]:
        """동기 방식으로 주식 정보 가져오기 (최적화됨)."""
        try:
            stock = yf.Ticker(ticker)
            
            # fast_info 먼저 시도
            try:
                fast_info = stock.fast_info
                if hasattr(fast_info, 'last_price') and fast_info.last_price:
                    # 주요 종목들만 전체 정보 가져오기
                    if ticker in self.seed_tickers['mega_cap'] or ticker in self.seed_tickers['etfs']:
                        info = stock.info
                        
                        return {
                            'symbol': ticker.upper(),
                            'name': info.get('longName', info.get('shortName', ticker)),
                            'short_name': info.get('shortName', ticker),
                            'exchange': info.get('exchange', self._guess_exchange(ticker)),
                            'sector': info.get('sector'),
                            'industry': info.get('industry'),
                            'market_cap': info.get('marketCap'),
                            'currency': info.get('currency', 'USD'),
                            'country': info.get('country', 'US'),
                            'stock_type': 'etf' if info.get('quoteType') == 'ETF' else 'equity',
                            'avg_volume': info.get('averageVolume'),
                            'shares_outstanding': info.get('sharesOutstanding'),
                            'is_popular': True
                        }
                    else:
                        # 기타 종목들은 기본 정보만
                        return {
                            'symbol': ticker.upper(),
                            'name': ticker,
                            'short_name': ticker,
                            'exchange': self._guess_exchange(ticker),
                            'sector': None,
                            'industry': None,
                            'market_cap': getattr(fast_info, 'market_cap', None),
                            'currency': 'USD',
                            'country': 'US',
                            'stock_type': 'equity',
                            'avg_volume': None,
                            'shares_outstanding': None,
                            'is_popular': False
                        }
            except:
                pass  # fallback으로 진행
            
            # 전체 정보 가져오기 (fallback)
            info = stock.info
            if not info or 'symbol' not in info:
                return None
                
            return {
                'symbol': ticker.upper(),
                'name': info.get('longName', info.get('shortName', ticker)),
                'short_name': info.get('shortName', ticker),
                'exchange': info.get('exchange', self._guess_exchange(ticker)),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'market_cap': info.get('marketCap'),
                'currency': info.get('currency', 'USD'),
                'country': info.get('country', 'US'),
                'stock_type': 'etf' if info.get('quoteType') == 'ETF' else 'equity',
                'avg_volume': info.get('averageVolume'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'is_popular': ticker in self.seed_tickers['mega_cap'] or ticker in self.seed_tickers['etfs']
            }
            
        except Exception as e:
            logger.debug(f"Error getting info for {ticker}: {e}")
            return None
    
    def _guess_exchange(self, ticker: str) -> str:
        """티커 심볼로 거래소 추측."""
        if ticker.endswith('.KS'):
            return 'KRX'
        elif ticker.endswith('.TO'):
            return 'TSE'
        elif ticker.endswith('.L'):
            return 'LSE'
        elif '=' in ticker or '-USD' in ticker:
            return 'INDEX'
        elif ticker in self.seed_tickers['etfs']:
            return 'ARCA'
        else:
            return 'NASDAQ'
    
    async def seed_database(self, force_refresh: bool = False) -> Dict[str, Any]:
        """데이터베이스에 주식 정보 시드 데이터 입력."""
        try:
            # DB 테이블 생성 (StockInfo 모델 사용)
            Base.metadata.create_all(bind=self.db_manager.engine)
            
            # 이미 데이터가 있는지 확인
            if not force_refresh:
                with self.db_manager.get_session() as session:
                    count = session.query(StockInfo).count()
                    if count > 100:  # 충분한 데이터가 있으면 스킵
                        logger.info(f"✅ Stock database already seeded with {count} stocks")
                        return {'status': 'already_seeded', 'count': count}
            
            # 모든 티커 수집
            all_tickers = set()
            for category_tickers in self.seed_tickers.values():
                all_tickers.update(category_tickers)
            
            ticker_list = list(all_tickers)
            logger.info(f"🌱 Seeding database with {len(ticker_list)} stocks...")
            
            # 배치별로 처리
            batch_size = 20
            successful_inserts = 0
            failed_inserts = 0
            
            for i in range(0, len(ticker_list), batch_size):
                batch = ticker_list[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(ticker_list) - 1) // batch_size + 1
                
                logger.info(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)")
                
                # 병렬로 주식 정보 가져오기
                loop = asyncio.get_event_loop()
                tasks = []
                
                for ticker in batch:
                    task = loop.run_in_executor(
                        self.executor,
                        self._get_stock_info_sync,
                        ticker
                    )
                    tasks.append((ticker, task))
                
                # 결과 처리 (기존 DB 연결 사용)
                with self.db_manager.get_session() as session:
                    for ticker, task in tasks:
                        try:
                            stock_data = await task
                            if stock_data:
                                self._upsert_stock_info_sync(session, stock_data)
                                successful_inserts += 1
                            else:
                                failed_inserts += 1
                                logger.debug(f"❌ Failed to get data for {ticker}")
                        except Exception as e:
                            failed_inserts += 1
                            logger.error(f"❌ Error processing {ticker}: {e}")
                    
                    session.commit()
                
                # API 속도 제한 방지
                await asyncio.sleep(0.2)
            
            # 인기도 순위 설정
            with self.db_manager.get_session() as session:
                self._set_popularity_rankings_sync(session)
                session.commit()
            
            logger.info(f"✅ Database seeding completed! Success: {successful_inserts}, Failed: {failed_inserts}")
            
            return {
                'status': 'completed',
                'successful_inserts': successful_inserts,
                'failed_inserts': failed_inserts,
                'total_processed': successful_inserts + failed_inserts
            }
            
        except Exception as e:
            logger.error(f"❌ Error during database seeding: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _upsert_stock_info_sync(self, session, stock_data: Dict[str, Any]):
        """주식 정보 삽입/업데이트 (동기식)."""
        try:
            # 기존 레코드 확인
            existing = session.query(StockInfo).filter(
                StockInfo.symbol == stock_data['symbol']
            ).first()
            
            if existing:
                # 업데이트
                for key, value in stock_data.items():
                    if key != 'symbol':  # primary key는 업데이트하지 않음
                        if key == 'name':
                            existing.name = value
                            existing.name_upper = value.upper()
                        else:
                            setattr(existing, key, value)
                existing.updated_at = datetime.now()
            else:
                # 새로 삽입
                stock_info = StockInfo(
                    symbol=stock_data['symbol'],
                    name=stock_data['name'],
                    short_name=stock_data.get('short_name'),
                    name_upper=stock_data['name'].upper(),
                    exchange=stock_data['exchange'],
                    sector=stock_data.get('sector'),
                    industry=stock_data.get('industry'),
                    market_cap=stock_data.get('market_cap'),
                    currency=stock_data.get('currency', 'USD'),
                    country=stock_data.get('country', 'US'),
                    stock_type=stock_data.get('stock_type', 'equity'),
                    avg_volume=stock_data.get('avg_volume'),
                    shares_outstanding=stock_data.get('shares_outstanding'),
                    is_active=True,
                    is_popular=stock_data.get('is_popular', False),
                    updated_at=datetime.now()
                )
                session.add(stock_info)
            
        except Exception as e:
            logger.error(f"Error upserting stock info for {stock_data.get('symbol', 'UNKNOWN')}: {e}")
    
    def _set_popularity_rankings_sync(self, session):
        """시가총액 기준으로 인기도 순위 설정 (동기식)."""
        try:
            # 시가총액 기준으로 정렬하여 순위 부여
            stocks = session.query(StockInfo).filter(
                StockInfo.is_active == True,
                StockInfo.market_cap.isnot(None)
            ).order_by(StockInfo.market_cap.desc()).all()
            
            for i, stock in enumerate(stocks):
                stock.popularity_rank = i + 1
            
            logger.info(f"📊 Set popularity rankings for {len(stocks)} stocks")
            
        except Exception as e:
            logger.error(f"Error setting popularity rankings: {e}")


# 전역 seeder 인스턴스
stock_seeder = StockSeeder()


async def seed_stock_database_on_startup(force_refresh: bool = False) -> Dict[str, Any]:
    """FastAPI 시작시 호출되는 데이터베이스 시딩 함수."""
    return await stock_seeder.seed_database(force_refresh)