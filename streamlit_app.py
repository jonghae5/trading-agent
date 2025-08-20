import streamlit as st
import datetime
import time
import logging
import os
from collections import deque
import pandas as pd
from dotenv import load_dotenv
import pytz
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from fredapi import Fred
from typing import Dict, List, Optional, Tuple, Any, Union
from db_manager import DatabaseManager

# Security and Configuration Constants
SESSION_DURATION_SECONDS = 3600  # 1 hour
MAX_LOGIN_ATTEMPTS = 5
BLOCK_DURATION_MINUTES = 15
CACHE_TTL_SECONDS = 300  # 5 minutes
MAX_MESSAGE_BUFFER_SIZE = 500
MAX_LOG_DISPLAY_SIZE = 50

# UI Constants
DEFAULT_TICKER = "SPY"
DEFAULT_RESEARCH_DEPTH = 3
MIN_PASSWORD_LENGTH = 8
MAX_TICKER_LENGTH = 10

# Time zone settings
KST = pytz.timezone('Asia/Seoul')

# Environment variables validation
def validate_environment() -> bool:
    """Validate required environment variables are set"""
    required_vars = []  # Add any required env vars here
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    return True

def sanitize_ticker(ticker: str) -> str:
    """Sanitize and validate ticker input"""
    if not ticker:
        return ""
    
    # Remove dangerous characters and limit length
    sanitized = ''.join(c for c in ticker.upper() if c.isalnum())
    return sanitized[:MAX_TICKER_LENGTH]

def validate_ticker(ticker: str) -> bool:
    """Validate ticker format"""
    if not ticker:
        return False
    
    # Basic validation: only alphanumeric, reasonable length
    return (ticker.isalnum() and 
            1 <= len(ticker) <= MAX_TICKER_LENGTH and
            ticker.isascii())

def validate_date_input(date_input: Any) -> bool:
    """Validate date input"""
    if not date_input:
        return False
    
    try:
        if isinstance(date_input, str):
            datetime.datetime.strptime(date_input, "%Y-%m-%d")
        elif hasattr(date_input, 'strftime'):
            # It's a date object
            pass
        else:
            return False
        return True
    except (ValueError, AttributeError):
        return False

def sanitize_log_message(message: str) -> str:
    """Sanitize log messages to prevent log injection"""
    if not isinstance(message, str):
        message = str(message)
    
    # Remove newlines and control characters that could be used for log injection
    sanitized = ''.join(c for c in message if c.isprintable() and c not in '\n\r\t')
    
    # Limit length to prevent log spam
    return sanitized[:1000] + "..." if len(sanitized) > 1000 else sanitized

def get_kst_now() -> datetime.datetime:
    """현재 KST 시간을 반환 (timezone-aware)"""
    return datetime.datetime.now(KST)

def get_kst_naive_now():
    """현재 KST 시간을 naive datetime으로 반환"""
    return get_kst_now().replace(tzinfo=None)

def to_kst_string(dt):
    """datetime을 KST 문자열로 변환"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # naive datetime은 KST로 가정
        dt = KST.localize(dt)
    else:
        # timezone-aware datetime을 KST로 변환
        dt = dt.astimezone(KST)
    return dt.strftime("%Y-%m-%d %H:%M:%S KST")

def get_kst_date():
    """현재 KST 날짜를 date 객체로 반환"""
    return get_kst_now().date()

def get_economic_crisis_dates():
    """경제 위기 및 주식시장 타격 시점 정의 - 공통 함수"""
    return [
        # ('1929-10-24', '월스트리트 대폭락'),            # 대공황 시작[9]
        # ('1973-01-01', '석유 파동'),                  # 오일쇼크, 글로벌 시장 붕괴[5][7]
        # ('1987-10-19', '블랙 먼데이'),                # 다우지수 하루 22.6% 폭락[6][7]
        ('2000-03-01', '닷컴 버블 붕괴'),             # IT·기술주 급락[7]
        ('2001-09-01', '9·11 테러'),                  # 미국/글로벌 주가 급락[2]
        ('2006-01-01', '부동산 버블 정점'),           # 미국 주택시장 고점
        ('2008-09-01', '리먼 브라더스'),               # 2008 금융위기[7]
        ('2012-01-01', '주택시장 회복'),               # W형 경기 침체 끝
        ('2018-12-01', '미국 증시 19% 조정'),          # S&P500 4분기 하락[7]
        ('2020-03-01', 'COVID-19 팬데믹'),            # 글로벌 증시 폭락[4][6]
        ('2022-02-01', '러-우 침공 및 러시아 증시 붕괴'),  # 지정학적 리스크[2]
        ('2022-03-01', 'Fed 긴축 시작'),               # 미국 금리 인상 시작
        ('2024-02-01', '중국 주식 시장 붕괴'),         # 상하이종합지수 급락[2]
        ('2024-08-01', '도쿄 증시 붕괴'),              # 닛케이 평균 주가 급락[2]
        ('2025-04-01', '미·중 무역갈등 악화'),         # 관세전쟁, 증시 폭락[2]
    ]


def add_crisis_markers_to_chart(fig, data_series, crisis_dates=None, date_column=None):
    """차트에 경제 위기 시점 마커 추가하는 공통 함수"""
    if crisis_dates is None:
        crisis_dates = get_economic_crisis_dates()
    
    crisis_x_dates = []
    crisis_y_values = []
    crisis_labels = []
    
    for date_str, label in crisis_dates:
        try:
            target_date = pd.to_datetime(date_str)
            
            # date_column이 별도로 제공된 경우 (fg_data처럼)
            if date_column is not None:
                # 별도 날짜 컬럼에서 범위 확인
                if target_date < date_column.min() or target_date > date_column.max():
                    continue
                
                # 가장 가까운 날짜 찾기
                time_diffs = np.abs((date_column - target_date).dt.days)
                nearest_idx = time_diffs.argmin()
                exact_date = date_column.iloc[nearest_idx]
                exact_value = data_series.iloc[nearest_idx]
            else:
                # 기존 Series 방식 (index가 날짜인 경우)
                if target_date < data_series.index.min() or target_date > data_series.index.max():
                    continue
                    
                # 정확한 날짜가 있는지 확인
                if target_date in data_series.index:
                    exact_date = target_date
                    exact_value = data_series.loc[exact_date]
                else:
                    # 가장 가까운 날짜 찾기
                    time_diffs = np.abs(data_series.index.astype('int64') - target_date.value)
                    nearest_idx = time_diffs.argmin()
                    exact_date = data_series.index[nearest_idx]
                    exact_value = data_series.iloc[nearest_idx]
            
            # 유효한 값인지 확인
            if pd.isna(exact_date) or pd.isna(exact_value):
                continue
                
            crisis_x_dates.append(exact_date)
            crisis_y_values.append(exact_value)
            crisis_labels.append(label)
            
        except Exception:
            continue
    
    # 위기 시점 마커 추가
    if crisis_x_dates:
        fig.add_trace(go.Scatter(
            x=crisis_x_dates,
            y=crisis_y_values,
            mode='markers+text',
            marker=dict(
                symbol='triangle-down',
                size=12,
                color='red',
                line=dict(width=2, color='darkred')
            ),
            text=crisis_labels,
            textposition='top center',
            textfont=dict(size=10, color='red'),
            name='경제 위기 시점',
            showlegend=True
        ))
    
    return fig

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_fear_greed_index():
    """CNN 공포탐욕지수 가져오기 (대체 지표로 VIX 사용)"""
    try:
        # VIX 지수를 공포탐욕지수의 대체 지표로 사용
        vix_data = yf.download('^VIX', period='5y', interval='1d')
        
        # Close 컬럼만 선택하고 인덱스를 reset
        vix_df = vix_data[['Close']].reset_index()
        vix_df.columns = ['Date', 'VIX']
        
        # VIX를 0-100 스케일로 변환 (공포탐욕지수 형태로)
        vix_df['Fear_Greed'] = 100 - np.clip((vix_df['VIX'] - 10) / 70 * 100, 0, 100)
        
        return vix_df.dropna()
    except Exception as e:
        st.error(f"공포탐욕지수(VIX) 데이터 로딩 실패: {e}")
        return None

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_put_call_ratio():
    """풋콜레이쇼 데이터 가져오기"""
    try:
        # CBOE 풋콜레이쇼 대신 관련 지표들로 근사치 계산
        spx_data = yf.download('^SPX', period='5y', interval='1d')
        vix_data = yf.download('^VIX', period='5y', interval='1d')
        
        # Close 컬럼만 선택하고 인덱스를 reset
        spx_df = spx_data[['Close']].reset_index()
        vix_df = vix_data[['Close']].reset_index()
        
        # 컬럼명 변경
        spx_df.columns = ['Date', 'SPX']
        vix_df.columns = ['Date', 'VIX']
        
        # 날짜로 병합
        put_call_data = pd.merge(spx_df, vix_df, on='Date', how='inner')
        
        # VIX와 SPX 관계를 이용한 Put/Call Ratio 근사치
        put_call_data['Put_Call_Ratio'] = (put_call_data['VIX'] / 20) * 1.2
        
        return put_call_data.dropna()
    except Exception as e:
        st.error(f"풋콜레이쇼 데이터 로딩 실패: {e}")
        return None


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_additional_indicators():
    """추가 필수 지표들 로드"""
    indicators = {}    
    # 금 가격
    try:
        gold_data = yf.download('GC=F', period='5y', interval='1mo')
        if not gold_data.empty:
            gold_df = gold_data[['Close']].reset_index()
            gold_df.columns = ['Date', 'Gold']
            indicators['gold'] = gold_df
    except:
        indicators['gold'] = None
    
    return indicators

# ==============================
# ① FRED API 거시경제 지표 함수들
# ==============================

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_fred_macro_indicators() -> Optional[Dict]:
    """FRED API를 사용하여 주요 거시경제 지표들을 가져오는 함수"""
    try:
        from fredapi import Fred
        FRED_AVAILABLE = True
    except ImportError:
        FRED_AVAILABLE = False
    
    if not FRED_AVAILABLE:
        return None
    
    # FRED API Key를 환경 변수에서 가져오기
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        st.warning("FRED_API_KEY 환경 변수를 설정해주세요.")
        return None
    
    try:
        fred = Fred(api_key=fred_api_key)
        indicators = {}
        
        # 미국 기준금리 (Federal Funds Rate)
        try:
            federal_rate = fred.get_series('FEDFUNDS', observation_start='1/1/1990')
            if federal_rate is not None and len(federal_rate) > 0:
                indicators['federal_rate'] = federal_rate.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Federal Funds Rate: {error_msg}")
        
        # 미국 GDP
        try:
            gdp = fred.get_series('GDP', observation_start='1/1/1990')
            if gdp is not None and len(gdp) > 0:
                indicators['gdp'] = gdp.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch GDP: {error_msg}")
        
        # 구매관리자지수 (PMI) - ISM Manufacturing PMI 
        try:
            # ISM Manufacturing PMI의 정확한 시리즈 코드
            pmi = fred.get_series('MANEMP', observation_start='1/1/1990')  # Manufacturing Employment Index
            if pmi is not None and len(pmi) > 0:
                indicators['pmi'] = pmi.dropna()
            else:
                # 대체 지표: Industrial Production Index
                pmi = fred.get_series('INDPRO', observation_start='1/1/1990')
                if pmi is not None and len(pmi) > 0:
                    indicators['pmi'] = pmi.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Manufacturing indicators: {error_msg}")
        
        # 통화량 (M2)
        try:
            m2 = fred.get_series('M2SL', observation_start='1/1/1990')
            if m2 is not None and len(m2) > 0:
                indicators['m2'] = m2.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch M2: {error_msg}")
        
        # 소매판매 (Retail Sales) - 소비 동향을 나타내는 중요 지표
        try:
            retail_sales = fred.get_series('RSAFS', observation_start='1/1/1990')  # Advance Retail Sales: Retail Trade
            if retail_sales is not None and len(retail_sales) > 0:
                indicators['retail_sales'] = retail_sales.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Retail Sales: {error_msg}")
        
        # 주택시장 추가 지표 (USAUCSFRCONDOSMSAMID)
        try:
            housing_market = fred.get_series('USAUCSFRCONDOSMSAMID', observation_start='1/1/1990')
            if housing_market is not None and len(housing_market) > 0:
                indicators['housing_market'] = housing_market.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Housing Market data: {error_msg}")
        

        
        # High Yield Spread - ICE BofA US High Yield Index Option-Adjusted Spread
        try:
            high_yield_spread = fred.get_series('BAMLH0A0HYM2', observation_start='1/1/1990')
            if high_yield_spread is not None and len(high_yield_spread) > 0:
                indicators['high_yield_spread'] = high_yield_spread.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch High Yield Spread: {error_msg}")
        
        # 실업률
        try:
            unemployment = fred.get_series('UNRATE', observation_start='1/1/1990')
            if unemployment is not None and len(unemployment) > 0:
                indicators['unemployment'] = unemployment.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Unemployment Rate: {error_msg}")
        
        # 소비자물가지수 (CPI)
        try:
            cpi = fred.get_series('CPIAUCSL', observation_start='1/1/1990')
            if cpi is not None and len(cpi) > 0:
                indicators['cpi'] = cpi.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch CPI: {error_msg}")
        
        # 절대 부채 (Total Public Debt)
        try:
            debt = fred.get_series('GFDEBTN', observation_start='1/1/1990')  # 2000년부터 시작 (장기 트렌드 확인)
            if debt is not None and len(debt) > 0:
                indicators['total_debt'] = debt.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Total Debt: {error_msg}")
        
        return indicators if indicators else None
        
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        logger.error(f"[FRED] Failed to initialize FRED client: {error_msg}")
        return None

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_additional_fred_indicators() -> Optional[Dict]:
    """추가 FRED 경제 지표들"""
    try:
        from fredapi import Fred
        FRED_AVAILABLE = True
    except ImportError:
        FRED_AVAILABLE = False
    
    if not FRED_AVAILABLE:
        return None
    
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        return None
    
    try:
        fred = Fred(api_key=fred_api_key)
        indicators = {}
        
        # VIX Index (CBOE Volatility Index)
        try:
            vix = fred.get_series('VIXCLS', observation_start='1/1/1990')
            if vix is not None and len(vix) > 0:
                indicators['vix'] = vix.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch VIX: {error_msg}")
        
        # 달러 인덱스 (Trade Weighted U.S. Dollar Index)
        try:
            dollar_index = fred.get_series('DTWEXBGS', observation_start='1/1/1990')
            if dollar_index is not None and len(dollar_index) > 0:
                indicators['dollar_index'] = dollar_index.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Dollar Index: {error_msg}")
        
        # 10년-2년 수익률 곡선
        try:
            ten_year_yield = fred.get_series('DGS10', observation_start='1/1/1990')
            two_year_yield = fred.get_series('DGS2', observation_start='1/1/1990')
            if ten_year_yield is not None and two_year_yield is not None:
                yield_spread = ten_year_yield - two_year_yield
                indicators['yield_spread'] = yield_spread.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Yield Spread: {error_msg}")
        
        
        # 원유 가격 (WTI Oil Price)
        try:
            oil_price = fred.get_series('DCOILWTICO', observation_start='1/1/1990')
            if oil_price is not None and len(oil_price) > 0:
                indicators['oil_price'] = oil_price.dropna()
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            logger.warning(f"[FRED] Failed to fetch Oil Price: {error_msg}")
        
        return indicators if indicators else None
        
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        logger.error(f"[FRED] Failed to fetch additional FRED indicators: {error_msg}")
        return None

def create_financial_indicators_charts():
    """통합 금융 지표 대시보드 - 모든 지표 + 상관관계 분석"""
    st.header("📊 거시 경제 대시보드")
    
    # 모든 데이터 로드 (기존 + 새로운 FRED 지표)
    fg_data = get_fear_greed_index()
    pc_data = get_put_call_ratio()
    additional_data = get_additional_indicators()
    
    # 새로운 FRED 지표들 로드
    fred_macro = get_fred_macro_indicators()
    fred_additional = get_additional_fred_indicators()
    
    # 데이터 로딩 상태 간단히 표시 (확장된 지표 포함)
    with st.expander("🔍 데이터 로딩 상태", expanded=False):
        indicators_status = [
            ("공포탐욕지수", fg_data),
            ("풋콜레이쇼", pc_data),
            ("금가격", additional_data.get('gold')),
        ]
        
        # FRED 지표들 상태도 추가
        if fred_macro:
            fred_indicators = [
                ("기준금리(FRED)", fred_macro.get('federal_rate')),
                ("GDP(FRED)", fred_macro.get('gdp')),
                ("제조업지수(FRED)", fred_macro.get('pmi')),
                ("M2통화량(FRED)", fred_macro.get('m2')),
                ("하이일드스프레드(FRED)", fred_macro.get('high_yield_spread')),
                ("소매판매(FRED)", fred_macro.get('retail_sales')),
                ("주택시장지수(FRED)", fred_macro.get('housing_market')),
                ("실업률(FRED)", fred_macro.get('unemployment')),
                ("CPI(FRED)", fred_macro.get('cpi')),
                ("절대부채(FRED)", fred_macro.get('total_debt'))
            ]
            indicators_status.extend(fred_indicators)
        
        if fred_additional:
            additional_fred = [
                ("VIX(FRED)", fred_additional.get('vix')),
                ("달러인덱스(FRED)", fred_additional.get('dollar_index')),
                ("수익률곡선(FRED)", fred_additional.get('yield_spread')),
                ("원유가격(FRED)", fred_additional.get('oil_price'))
            ]
            indicators_status.extend(additional_fred)
        
        for name, data in indicators_status:
            status = "✅ 성공" if data is not None and len(data) > 0 else "❌ 실패"
            st.write(f"- {name}: {status}")
    
    # 새로운 FRED 지표들 섹션 추가
    if fred_macro or fred_additional:
        st.markdown("---")
        st.subheader("🏦 FRED 거시경제 지표")
        
        # FRED 지표들을 위한 3열 레이아웃
        fred_col1, fred_col2, fred_col3 = st.columns(3)
        
        with fred_col1:
            # GDP
            if fred_macro and 'gdp' in fred_macro:
                gdp_data = fred_macro['gdp']
                if not gdp_data.empty:
                    current_gdp = gdp_data.iloc[-1] / 1000  # 조 달러로 변환
                    prev_gdp = gdp_data.iloc[-2] / 1000 if len(gdp_data) > 1 else current_gdp
                    gdp_growth = ((current_gdp - prev_gdp) / prev_gdp) * 100
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #059669, #10b981); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">📈 GDP</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">${current_gdp:.1f}조 | QoQ {gdp_growth:+.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # GDP 성장률 차트
                    gdp_growth_rate = gdp_data.pct_change() * 100
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=gdp_growth_rate.index,
                        y=gdp_growth_rate.values,
                        name='GDP Growth Rate',
                        marker_color=['green' if x >= 0 else 'red' for x in gdp_growth_rate.values]
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, gdp_growth_rate)
                    
                    fig.update_layout(
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 GDP 성장 = 경기 확장, 감소 = 경기 둔화")
            
            # 제조업 지수 (Industrial Production 또는 Manufacturing Employment)
            if fred_macro and 'pmi' in fred_macro:
                manufacturing_data = fred_macro['pmi']
                if not manufacturing_data.empty:
                    # YoY 성장률 계산 (지수이므로)
                    manufacturing_growth = manufacturing_data.pct_change(periods=12) * 100
                    current_growth = manufacturing_growth.iloc[-1] if not manufacturing_growth.empty else 0
                    current_index = manufacturing_data.iloc[-1]
                    
                    # 제조업 상태에 따른 색상 (성장률 기준)
                    if current_growth > 3:
                        manufacturing_color = "#10b981"  # 강한 성장
                    elif current_growth > 0:
                        manufacturing_color = "#3b82f6"  # 성장
                    elif current_growth > -3:
                        manufacturing_color = "#f59e0b"  # 둔화
                    else:
                        manufacturing_color = "#ef4444"  # 위축
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, {manufacturing_color}, #64748b); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">🏭 제조업 지수</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">{current_index:.1f} | YoY {current_growth:+.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 제조업 성장률 차트
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=manufacturing_growth.index,
                        y=manufacturing_growth.values,
                        mode='lines',
                        name='Manufacturing Growth Rate',
                        line=dict(color=manufacturing_color, width=2),
                        fill='tozeroy',
                        fillcolor=f'rgba({int(manufacturing_color[1:3], 16)}, {int(manufacturing_color[3:5], 16)}, {int(manufacturing_color[5:7], 16)}, 0.1)'
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, manufacturing_growth)
                    
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="기준선 0%")
                    fig.update_layout(
                        title='제조업 지수 성장률 (YoY)',
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='%'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 양수 = 제조업 성장, 음수 = 제조업 위축")

            # CPI (인플레이션)
            if fred_macro and 'cpi' in fred_macro:
                cpi_data = fred_macro['cpi']
                if not cpi_data.empty:
                    # YoY 인플레이션율 계산
                    inflation_rate = cpi_data.pct_change(periods=12) * 100  # 12개월 전 대비
                    if not inflation_rate.empty:
                        current_inflation = inflation_rate.iloc[-1]
                        
                        # 인플레이션 상태에 따른 색상
                        if current_inflation < 2:
                            inflation_color = "#3b82f6"  # 파랑 (디플레이션 우려)
                        elif current_inflation <= 3:
                            inflation_color = "#10b981"  # 녹색 (목표 수준)
                        elif current_inflation <= 5:
                            inflation_color = "#f59e0b"  # 주황 (높음)
                        else:
                            inflation_color = "#ef4444"  # 빨강 (매우 높음)
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(90deg, {inflation_color}, #6366f1); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                            <span style="color: white; font-weight: bold; font-size: 14px;">📊 CPI 인플레이션</span>
                            <span style="color: white; font-size: 12px; margin-left: 10px;">{current_inflation:.1f}% YoY</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 인플레이션율 차트
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=inflation_rate.index,
                            y=inflation_rate.values,
                            mode='lines',
                            name='CPI Inflation YoY',
                            line=dict(color=inflation_color, width=2),
                            fill='tozeroy',
                            fillcolor=f'rgba({int(inflation_color[1:3], 16)}, {int(inflation_color[3:5], 16)}, {int(inflation_color[5:7], 16)}, 0.1)'
                        ))
                        
                        # 주요 경제 위기 시점 표시
                        fig = add_crisis_markers_to_chart(fig, inflation_rate)
                        
                        fig.add_hline(y=2, line_dash="dash", line_color="gray", annotation_text="FED 목표 2%")
                        fig.update_layout(
                            title='CPI 인플레이션율 (YoY)',
                            height=200,
                            showlegend=True,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="center",
                                x=0.5
                            ),
                            margin=dict(l=20, r=20, t=40, b=20),
                            yaxis_title='%'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption("💡 2% 목표치. 높으면 긴축 압력, 낮으면 완화 신호")
        
            if fred_macro and 'unemployment' in fred_macro:
                unemployment = fred_macro['unemployment']
                if not unemployment.empty:
                    current_unemployment = unemployment.iloc[-1]
                    prev_unemployment = unemployment.iloc[-2] if len(unemployment) > 1 else current_unemployment
                    unemployment_change = current_unemployment - prev_unemployment
                    
                    # 실업률 상태에 따른 색상
                    if current_unemployment < 4:
                        unemployment_color = "#10b981"  # 녹색 (양호)
                    elif current_unemployment < 6:
                        unemployment_color = "#f59e0b"  # 주황 (보통)
                    else:
                        unemployment_color = "#ef4444"  # 빨강 (나쁨)
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, {unemployment_color}, #6b7280); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">👥 실업률</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">{current_unemployment:.1f}% | 전월대비 {unemployment_change:+.1f}%p</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 실업률 차트
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=unemployment.index,
                        y=unemployment.values,
                        mode='lines+markers',
                        name='Unemployment Rate',
                        line=dict(color=unemployment_color, width=2),
                        marker=dict(size=4)
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, unemployment)
                    
                    fig.add_hline(y=4, line_dash="dash", line_color="green", annotation_text="완전고용 기준")
                    fig.update_layout(
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='%'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 실업률 하락 = 경기 회복, 상승 = 경기 둔화")
              # 수익률 곡선 (FRED)
            
            # 실업률
            if fred_additional and 'yield_spread' in fred_additional:
                yield_data = fred_additional['yield_spread']
                if not yield_data.empty:
                    current_spread = yield_data.iloc[-1]
                    
                    if current_spread < 0:
                        curve_status = "⚠️ 역전"
                        curve_color = "#ef4444"
                    elif current_spread < 100:  # 1% 미만
                        curve_status = "🟡 평탄"
                        curve_color = "#f59e0b"
                    else:
                        curve_status = "✅ 정상"
                        curve_color = "#10b981"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, {curve_color}, #6366f1); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">📊 수익률곡선</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">{current_spread:.2f}bp ({curve_status})</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 수익률 곡선 차트
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=yield_data.index,
                        y=yield_data.values,
                        mode='lines',
                        name='Yield Spread',
                        line=dict(color=curve_color, width=2),
                        fill='tozeroy',
                        fillcolor=f'rgba({int(curve_color[1:3], 16)}, {int(curve_color[3:5], 16)}, {int(curve_color[5:7], 16)}, 0.1)'
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, yield_data)
                    
                    fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="역전선 0%")
                    fig.update_layout(
                        title='10Y-2Y 수익률 곡선',
                        height=180,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='Basis Points'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 양수=정상, 음수=역전(경기침체 신호)")
            
         
             # 달러 인덱스 이동
        with fred_col2:
            # 기준금리
            if fred_macro and 'federal_rate' in fred_macro:
                fed_rate = fred_macro['federal_rate']
                if not fed_rate.empty:
                    current_rate = fed_rate.iloc[-1]
                    prev_rate = fed_rate.iloc[-2] if len(fed_rate) > 1 else current_rate
                    rate_change = current_rate - prev_rate
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #6366f1, #8b5cf6); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">🏦 연방기준금리</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">{current_rate:.2f}% | 전월대비 {rate_change:+.2f}%p</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 기준금리 차트
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=fed_rate.index,
                        y=fed_rate.values,
                        mode='lines',
                        name='Federal Funds Rate',
                        line=dict(color='#6366f1', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(99, 102, 241, 0.1)'
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, fed_rate)
                    
                    fig.update_layout(
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='%'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 금리 상승 = 주식 약세 압력, 하락 = 유동성 증가")
        
            # 절대 부채 (FRED 공식 데이터)
            if fred_macro and 'total_debt' in fred_macro:
                debt_data = fred_macro['total_debt']
                if not debt_data.empty:
                    current_debt = debt_data.iloc[-1] / 1000  # 조 달러로 변환
                    prev_debt = debt_data.iloc[-2] / 1000 if len(debt_data) > 1 else current_debt
                    
                    # QoQ 증가율 계산 (분기별 데이터)
                    debt_qoq = debt_data.pct_change() * 100
                    current_debt_qoq = debt_qoq.iloc[-1] if not debt_qoq.empty else 0
                    
                    # YoY 증가율 계산 (4분기 전 대비)
                    debt_yoy = debt_data.pct_change(periods=4) * 100
                    current_debt_yoy = debt_yoy.iloc[-1] if not debt_yoy.empty else 0
                    
                    # 부채 수준에 따른 색상
                    if current_debt > 35:  # 35조 달러 이상
                        debt_status = "🔴 매우높음"
                        debt_color = "#ef4444"
                    elif current_debt > 30:  # 30-35조
                        debt_status = "🟡 높음"
                        debt_color = "#f59e0b"
                    elif current_debt > 25:  # 25-30조
                        debt_status = "🟢 보통"
                        debt_color = "#10b981"
                    else:  # 25조 미만
                        debt_status = "🔵 낮음"
                        debt_color = "#3b82f6"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, {debt_color}, #6366f1); padding: 8px 12px; border-radius:20px; margin: 8px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <span style="color: white; font-weight: bold; font-size: 14px;">🏛️ 미국 절대부채</span>
                    <span style="color: white; font-size: 12px; margin-left: 10px;">${current_debt:.1f}조 | QoQ {current_debt_qoq:+.1f}% | YoY {current_debt_yoy:+.1f}% | {debt_status}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 절대 부채 원본 시계열 차트
                    fig = go.Figure()
                    
                    # 부채 라인 (조 달러 단위)
                    debt_in_trillions = debt_data / 1000
                    fig.add_trace(go.Scatter(
                        x=debt_data.index,
                        y=debt_in_trillions.values,
                        mode='lines',
                        name='Total Public Debt',
                        line=dict(color=debt_color, width=3),
                        fill='tozeroy',
                        fillcolor=f'rgba({int(debt_color[1:3], 16)}, {int(debt_color[3:5], 16)}, {int(debt_color[5:7], 16)}, 0.1)'
                    ))
                    
                    fig = add_crisis_markers_to_chart(fig, debt_in_trillions)
                    
                    fig.update_layout(
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='조 달러 (Trillions USD)'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 절대 부채 증가율 차트 (YoY, QoQ)
                    fig2 = go.Figure()
                    
                    # YoY 증가율
                    fig2.add_trace(go.Scatter(
                        x=debt_yoy.index,
                        y=debt_yoy.values,
                        mode='lines',
                        name='YoY Growth Rate',
                        line=dict(color='#3b82f6', width=2)
                    ))
                    
                    # QoQ 증가율 (보조축)
                    fig2.add_trace(go.Scatter(
                        x=debt_qoq.index,
                        y=debt_qoq.values,
                        mode='lines',
                        name='QoQ Growth Rate',
                        line=dict(color='#f59e0b', width=2),
                        yaxis='y2'
                    ))
                    
                  
                    
                    fig2.update_layout(
                        title='절대부채 증가율 (YoY, QoQ)',
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis=dict(title='YoY %', side='left'),
                        yaxis2=dict(title='QoQ %', side='right', overlaying='y'),
                        xaxis=dict(title='Date')
                    )
                    
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Debt-to-GDP 비율 계산 및 차트
                    if fred_macro and 'gdp' in fred_macro:
                        gdp_data = fred_macro['gdp']
                        if not gdp_data.empty:
                            # 두 시계열을 같은 날짜로 맞춤 (분기별 데이터)
                            common_dates = debt_data.index.intersection(gdp_data.index)
                            if len(common_dates) > 0:
                                debt_aligned = debt_data.loc[common_dates]
                                gdp_aligned = gdp_data.loc[common_dates]
                                
                                # Debt-to-GDP 비율 계산 (%)
                                debt_to_gdp = (debt_aligned / gdp_aligned) * 100
                                
                                current_debt_to_gdp = debt_to_gdp.iloc[-1]
                                
                                # Debt-to-GDP 비율에 따른 색상
                                if current_debt_to_gdp > 120:  # 120% 이상
                                    ratio_status = "🔴 위험"
                                    ratio_color = "#ef4444"
                                elif current_debt_to_gdp > 100:  # 100-120%
                                    ratio_status = "🟡 높음"
                                    ratio_color = "#f59e0b"
                                elif current_debt_to_gdp > 80:  # 80-100%
                                    ratio_status = "🟢 보통"
                                    ratio_color = "#10b981"
                                else:  # 80% 미만
                                    ratio_status = "🔵 낮음"
                                    ratio_color = "#3b82f6"
                                
                                fig3 = go.Figure()
                                
                                fig3.add_trace(go.Scatter(
                                    x=debt_to_gdp.index,
                                    y=debt_to_gdp.values,
                                    mode='lines',
                                    name='Debt-to-GDP Ratio',
                                    line=dict(color=ratio_color, width=3),
                                    fill='tozeroy',
                                    fillcolor=f'rgba({int(ratio_color[1:3], 16)}, {int(ratio_color[3:5], 16)}, {int(ratio_color[5:7], 16)}, 0.1)'
                                ))
                                
                              
                                
                                # 위험 구간 표시
                                fig3.add_hline(y=80, line_dash="dot", line_color="green", annotation_text="안전 구간 (80%)")
                                fig3.add_hline(y=100, line_dash="dash", line_color="orange", annotation_text="주의 구간 (100%)")
                                fig3.add_hline(y=120, line_dash="dash", line_color="red", annotation_text="위험 구간 (120%)")
                                
                                fig3.update_layout(
                                    title=f'Debt-to-GDP 비율 - 현재: {current_debt_to_gdp:.1f}% ({ratio_status})',
                                    height=200,
                                    showlegend=True,
                                    legend=dict(
                                        orientation="h",
                                        yanchor="bottom",
                                        y=1.02,
                                        xanchor="center",
                                        x=0.5
                                    ),
                                    margin=dict(l=20, r=20, t=40, b=20),
                                    yaxis_title='Debt-to-GDP (%)'
                                )
                                
                                st.plotly_chart(fig3, use_container_width=True)
                                st.caption("💡 Debt-to-GDP 비율이 높을수록 재정 건전성 우려. 일반적으로 100% 초과 시 주의 필요")
            
            # M2 통화량
            if fred_macro and 'm2' in fred_macro:
                m2_data = fred_macro['m2']
                if not m2_data.empty:
                    current_m2 = m2_data.iloc[-1] / 1000  # 조 달러로 변환
                    # YoY 증가율 계산
                    m2_growth = m2_data.pct_change(periods=12) * 100
                    current_m2_growth = m2_growth.iloc[-1] if not m2_growth.empty else 0
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #7c3aed, #a855f7); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">💰 M2 통화량</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">${current_m2:.1f}조 | YoY {current_m2_growth:+.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # M2 성장률 차트
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=m2_growth.index,
                        y=m2_growth.values,
                        mode='lines',
                        name='M2 Growth Rate',
                        line=dict(color='#7c3aed', width=2)
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, m2_growth)
                    
                    fig.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig.update_layout(
                        title='M2 통화량 증가율 (YoY)',
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='%'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 통화량 증가 = 유동성 공급, 감소 = 긴축")
            
                        # 하이일드 스프레드 (FRED 공식 데이터) 이동
            # 하이일드 스프레드
            if fred_macro and 'high_yield_spread' in fred_macro:
                high_yield_data = fred_macro['high_yield_spread']
                if not high_yield_data.empty:
                    current_spread_bp = high_yield_data.iloc[-1]
                    prev_spread_bp = high_yield_data.iloc[-2] if len(high_yield_data) > 1 else current_spread_bp
                    spread_change = current_spread_bp - prev_spread_bp
                    
                    # 스프레드 상태에 따른 색상
                    if current_spread_bp > 8:  # 8% 이상
                        spread_status = "🔴 위험"
                        spread_color = "#ef4444"
                    elif current_spread_bp > 5:  # 5-8%
                        spread_status = "🟡 주의"
                        spread_color = "#f59e0b"
                    elif current_spread_bp > 3:  # 3-5%
                        spread_status = "🟢 보통"
                        spread_color = "#10b981"
                    else:  # 3% 미만
                        spread_status = "🔵 안전"
                        spread_color = "#3b82f6"
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, {spread_color}, #6366f1); padding: 8px 12px; border-radius:20px; margin: 8px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <span style="color: white; font-weight: bold; font-size: 14px;">🏛️ 하이일드 스프레드</span>
                    <span style="color: white; font-size: 12px; margin-left: 10px;">{current_spread_bp:.0f}bp | 전일대비 {spread_change:+.0f}bp | {spread_status}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 하이일드 스프레드 차트
                    fig = go.Figure()
                    
                    # 스프레드 라인
                    fig.add_trace(go.Scatter(
                        x=high_yield_data.index,
                        y=high_yield_data.values,
                        mode='lines',
                        name='High Yield Spread',
                        line=dict(color=spread_color, width=3),
                        fill='tozeroy',
                        fillcolor=f'rgba({int(spread_color[1:3], 16)}, {int(spread_color[3:5], 16)}, {int(spread_color[5:7], 16)}, 0.1)'
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, high_yield_data)
                    
                    # 위험 구간 표시
                    fig.add_hline(y=3, line_dash="dot", line_color="green", annotation_text="안전 구간 (300bp)")
                    fig.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="주의 구간 (500bp)")
                    fig.add_hline(y=8, line_dash="dash", line_color="red", annotation_text="위험 구간 (800bp)")
                    
                    fig.update_layout(
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='Basis Points (bp)'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 ICE BofA US High Yield Index Option-Adjusted Spread. 높을수록 신용위험 증가, 경기침체 신호")
                
        with fred_col3:
            
            # 풋콜레이쇼 이동
            current_pc = pc_data['Put_Call_Ratio'].iloc[-1] if pc_data is not None and len(pc_data) > 0 else 0
            if current_pc > 1.2:
                sentiment = "😨 극도공포"
                badge_color = "#FF4757"
            elif current_pc > 1.0:
                sentiment = "😰 공포"
                badge_color = "#FF6B35"
            elif current_pc > 0.8:
                sentiment = "😐 중립"
                badge_color = "#FFA502"
            else:
                sentiment = "😎 탐욕"
                badge_color = "#26C6DA"
                
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #9B59B6, {badge_color}); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                <span style="color: white; font-weight: bold; font-size: 14px;">⚖️ 풋콜레이쇼</span>
                <span style="color: white; font-size: 12px; margin-left: 10px;">{current_pc:.3f} ({sentiment})</span>
            </div>
            """, unsafe_allow_html=True)
            
            if pc_data is not None and len(pc_data) > 0:
                ratio_chart = pc_data.set_index('Date')[['Put_Call_Ratio']]
                st.line_chart(ratio_chart, color="#9B59B6", height=200)
                st.caption("💡 1.0 이상 = 풋옵션 우세(공포), 1.0 미만 = 콜옵션 우세(탐욕)")
            
            # VIX/공포탐욕지수 이동
            if fg_data is not None and len(fg_data) > 0:
                current_vix = fg_data['VIX'].iloc[-1]
                current_fg = fg_data['Fear_Greed'].iloc[-1]
                
                if current_fg >= 75:
                    fg_sentiment = "🤑 탐욕"
                    fg_color = "#26C6DA"
                elif current_fg >= 50:
                    fg_sentiment = "😎 중립+"
                    fg_color = "#3498DB"
                elif current_fg >= 25:
                    fg_sentiment = "😐 중립"
                    fg_color = "#FFA502"
                else:
                    fg_sentiment = "😨 공포"
                    fg_color = "#FF6B35"
                
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, #E74C3C, {fg_color}); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                    <span style="color: white; font-weight: bold; font-size: 14px;">😱 공포탐욕지수</span>
                    <span style="color: white; font-size: 12px; margin-left: 10px;">VIX {current_vix:.2f} | 지수 {current_fg:.1f} ({fg_sentiment})</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 공포탐욕지수 차트
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=fg_data['Date'],
                    y=fg_data['Fear_Greed'],
                    mode='lines',
                    name='Fear Greed Index',
                    line=dict(color=fg_color, width=2)
                ))
                
                # 주요 경제 위기 시점 표시
                fig = add_crisis_markers_to_chart(fig, fg_data['Fear_Greed'], date_column=fg_data['Date'])
                
                fig.update_layout(
                    height=200,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis_title='Index (0-100)'
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("💡 VIX는 변동성 지수, 높을수록 시장 불안정. 지수는 VIX 역산 (0=극도공포, 100=극도탐욕)")
            
            # 금 가격 이동
            if additional_data.get('gold') is not None and len(additional_data['gold']) > 0:
                gold_data = additional_data['gold']
                current_gold = gold_data['Gold'].iloc[-1]
                # 30일 변화율 계산
                prev_gold = gold_data['Gold'].iloc[-30] if len(gold_data) > 30 else gold_data['Gold'].iloc[0]
                gold_change = ((current_gold - prev_gold) / prev_gold) * 100
                
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, #FFD700, #FFA000); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                    <span style="color: white; font-weight: bold; font-size: 14px;">🥇 금 가격</span>
                    <span style="color: white; font-size: 12px; margin-left: 10px;">${current_gold:.2f} | 30일 {gold_change:+.2f}%</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 금 가격 차트
                gold_chart = gold_data.set_index('Date')[['Gold']]
                st.line_chart(gold_chart, color="#FFD700", height=200)
                st.caption("💡 인플레이션 헤지 자산, 달러 약세/지정학적 리스크 시 상승")
            
            # 원유가격 이동 (FRED 데이터 사용)
            if fred_additional and 'oil_price' in fred_additional:
                
                oil_data = fred_additional['oil_price']
                if not oil_data.empty:
                    current_oil = oil_data.iloc[-1]
                    # 30일 변화율 계산
                    prev_oil = oil_data.iloc[-30] if len(oil_data) > 30 else oil_data.iloc[0]
                    oil_change = ((current_oil - prev_oil) / prev_oil) * 100
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #2C3E50, #34495E); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">🛢️ 원유가격</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">${current_oil:.2f} | 30일 {oil_change:+.2f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 원유가격 차트
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=oil_data.index,
                        y=oil_data.values,
                        mode='lines',
                        name='Oil Price',
                        line=dict(color='#2C3E50', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(44, 62, 80, 0.1)'
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, oil_data)
                    
                    fig.update_layout(
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='USD'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 인플레이션 선행지표, 상승 시 에너지/운송비용 증가로 물가 압력")
            # 달러인덱스 이동
            if fred_additional and 'dollar_index' in fred_additional:
                dollar_data = fred_additional['dollar_index']
                if not dollar_data.empty:
                    current_dollar = dollar_data.iloc[-1]
                    # 30일 변화율 계산 (일별 데이터이므로)
                    prev_dollar = dollar_data.iloc[-22] if len(dollar_data) > 22 else dollar_data.iloc[0]  # 대략 1개월
                    dollar_change = ((current_dollar - prev_dollar) / prev_dollar) * 100
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #FFD700, #FFA000); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                        <span style="color: white; font-weight: bold; font-size: 14px;">💵 달러 인덱스</span>
                        <span style="color: white; font-size: 12px; margin-left: 10px;">{current_dollar:.2f} | 30일 {dollar_change:+.2f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 달러 인덱스 차트
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=dollar_data.index,
                        y=dollar_data.values,
                        mode='lines',
                        name='Dollar Index',
                        line=dict(color='#FFD700', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(255, 215, 0, 0.1)'
                    ))
                    
                    # 주요 경제 위기 시점 표시
                    fig = add_crisis_markers_to_chart(fig, dollar_data)
                    
                    fig.update_layout(
                        height=200,
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
                        yaxis_title='Index'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("💡 달러 강세 → 신흥국/금 약세, 달러 약세 → 원자재/신흥국 강세")
        
        # 소매판매 지수 추가
        if fred_macro and 'retail_sales' in fred_macro:
            retail_data = fred_macro['retail_sales']
            if not retail_data.empty:
                # YoY 성장률 계산
                retail_growth = retail_data.pct_change(periods=12) * 100
                current_retail_growth = retail_growth.iloc[-1] if not retail_growth.empty else 0
                current_retail = retail_data.iloc[-1] / 1000  # 천억 달러로 변환
                
                # 소매판매 상태에 따른 색상
                if current_retail_growth > 5:
                    retail_color = "#10b981"  # 강한 성장
                elif current_retail_growth > 2:
                    retail_color = "#3b82f6"  # 성장
                elif current_retail_growth > -2:
                    retail_color = "#f59e0b"  # 둔화
                else:
                    retail_color = "#ef4444"  # 위축
                
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, {retail_color}, #9333ea); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                    <span style="color: white; font-weight: bold; font-size: 14px;">🛒 소매판매</span>
                    <span style="color: white; font-size: 12px; margin-left: 10px;">${current_retail:.0f}천억 | YoY {current_retail_growth:+.1f}%</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 소매판매 성장률 차트
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=retail_growth.index,
                    y=retail_growth.values,
                    mode='lines+markers',
                    name='Retail Sales Growth',
                    line=dict(color=retail_color, width=2),
                    marker=dict(size=3)
                ))
                
                # 주요 경제 위기 시점 표시
                fig = add_crisis_markers_to_chart(fig, retail_growth)
                
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                fig.update_layout(
                    title='소매판매 성장률 (YoY)',
                    height=200,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis_title='%'
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("💡 소비 동향의 핵심 지표. 높을수록 경기 호조")
        
        # 주택시장 지수 (USAUCSFRCONDOSMSAMID)
        if fred_macro and 'housing_market' in fred_macro:
            housing_data = fred_macro['housing_market']
            if not housing_data.empty:
                current_housing = housing_data.iloc[-1]
                # YoY 증가율 계산
                housing_growth = housing_data.pct_change(periods=12) * 100
                current_housing_growth = housing_growth.iloc[-1] if not housing_growth.empty else 0
                
                # 주택시장 상태에 따른 색상
                if current_housing_growth > 15:
                    housing_color = "#ef4444"  # 빨강 (과열)
                elif current_housing_growth > 8:
                    housing_color = "#f59e0b"  # 주황 (강한 상승)
                elif current_housing_growth > 3:
                    housing_color = "#10b981"  # 녹색 (건전한 상승)
                elif current_housing_growth > -3:
                    housing_color = "#3b82f6"  # 파랑 (보정)
                else:
                    housing_color = "#6366f1"  # 보라 (하락)
                
                st.markdown(f"""
                <div style="background: linear-gradient(90deg, {housing_color}, #475569); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                    <span style="color: white; font-weight: bold; font-size: 14px;">🏘️ 주택시장 지수</span>
                    <span style="color: white; font-size: 12px; margin-left: 10px;">{current_housing:.0f} | YoY {current_housing_growth:+.1f}%</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 주택시장 지수 차트 (장기 트렌드)
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=housing_data.index,
                    y=housing_data.values,
                    mode='lines',
                    name='Housing Market Index',
                    line=dict(color=housing_color, width=2),
                    fill='tozeroy',
                    fillcolor=f'rgba({int(housing_color[1:3], 16)}, {int(housing_color[3:5], 16)}, {int(housing_color[5:7], 16)}, 0.1)'
                ))
                
                # 주요 경제 위기 시점 표시 (2000년부터 데이터이므로)
                fig = add_crisis_markers_to_chart(fig, housing_data)
                fig.update_layout(
                    height=250,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis_title='Index'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # YoY 성장률 차트
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=housing_growth.index,
                    y=housing_growth.values,
                    mode='lines+markers',
                    name='Housing Growth Rate',
                    line=dict(color=housing_color, width=2),
                    marker=dict(size=2)
                ))
                
                # 주요 경제 위기 시점 표시
                fig2 = add_crisis_markers_to_chart(fig2, housing_growth)
                
                # 건전성 기준선
                fig2.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="기준선")
                fig2.add_hline(y=8, line_dash="dot", line_color="orange", annotation_text="과열 주의")
                fig2.add_hline(y=15, line_dash="dot", line_color="red", annotation_text="과열 위험")
                fig2.add_hline(y=-10, line_dash="dot", line_color="purple", annotation_text="급락 위험")
                
                fig2.update_layout(
                    title='주택시장 성장률 (YoY)',
                    height=200,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    yaxis_title='%'
                )
                st.plotly_chart(fig2, use_container_width=True)
                st.caption("💡 2000년부터 장기 데이터. 15% 초과 시 과열, -10% 미만 시 급락 위험")
        
    

    # 개선된 통합 상관관계 분석 섹션
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, var(--primary-600), var(--primary-700)); padding: 20px 24px; border-radius: 20px; margin: 24px 0; box-shadow: 0 8px 32px rgba(14, 165, 233, 0.15);">
        <span style="color: white; font-weight: bold; font-size: 18px;">🔗 지표간 상관관계 분석</span>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">다양한 경제지표들의 상호관계를 분석하여 시장 동향을 파악합니다</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # 개선된 지표 데이터 수집 - FRED 데이터 우선 활용
        correlation_data_dict = {}
        data_sources = {}  # 데이터 출처 추적
        
        # FRED 매크로 데이터 (최우선)
        if fred_macro:
            for key, data in fred_macro.items():
                if data is not None and len(data) > 10:  # 최소 10개 데이터 포인트
                    korean_names = {
                        'federal_rate': '연방기준금리',
                        'gdp': 'GDP', 
                        'pmi': '제조업지수',
                        'm2': 'M2통화량',
                        'high_yield_spread': '하이일드스프레드',
                        'retail_sales': '소매판매',
                        'housing_market': '주택시장지수',
                        'unemployment': '실업률',
                        'cpi': '소비자물가지수',
                        'total_debt': '절대부채'
                    }
                    name = korean_names.get(key, key)
                    correlation_data_dict[name] = data
                    data_sources[name] = 'FRED'
        
        # FRED 추가 지표
        if fred_additional:
            additional_names = {
                'vix': 'VIX지수',
                'dollar_index': '달러인덱스', 
                'yield_spread': '수익률곡선',
                'oil_price': '원유가격'
            }
            for key, data in fred_additional.items():
                if data is not None and len(data) > 10:
                    name = additional_names.get(key, key)
                    correlation_data_dict[name] = data
                    data_sources[name] = 'FRED'
        
        # 기존 야후파이낸스 데이터 (보조)
        if fg_data is not None and len(fg_data) > 10:
            correlation_data_dict['공포탐욕지수'] = fg_data['Fear_Greed']
            data_sources['공포탐욕지수'] = 'Yahoo Finance'
        
        if pc_data is not None and len(pc_data) > 10:
            correlation_data_dict['풋콜레이쇼'] = pc_data['Put_Call_Ratio']
            data_sources['풋콜레이쇼'] = 'Yahoo Finance'
        
        # 기존 Yahoo Finance 하이일드 스프레드는 제거 - FRED 버전 사용
        
        
        if additional_data.get('gold') is not None and len(additional_data['gold']) > 10:
            correlation_data_dict['금가격'] = additional_data['gold']['Gold']
            data_sources['금가격'] = 'Yahoo Finance'
        
        # 데이터 검증 및 정제
        valid_data = {}
        for name, data in correlation_data_dict.items():
            try:
                # 숫자형 데이터로 변환 시도
                numeric_data = pd.to_numeric(data, errors='coerce').dropna()
                if len(numeric_data) >= 10:  # 최소 데이터 포인트 확인
                    valid_data[name] = numeric_data
                    
            except Exception as e:
                st.warning(f"⚠️ {name} 데이터 처리 중 오류: {str(e)[:50]}...")
                continue
        
        if len(valid_data) >= 3:
            # 모든 데이터를 같은 길이로 맞추기
            min_len = min([len(v) for v in valid_data.values()])
            max_len = max([len(v) for v in valid_data.values()])
            
            # 데이터 길이 정보 표시
            st.markdown(f"""
            <div style="background: var(--gray-50); padding: 16px; border-radius: 12px; margin: 16px 0; border-left: 4px solid var(--primary-500);">
                <h4 style="margin: 0 0 8px 0; color: var(--gray-700);">📊 분석 데이터 현황</h4>
                <p style="margin: 0; color: var(--gray-600);">
                    <strong>{len(valid_data)}개 지표</strong> | 
                    <strong>{min_len}~{max_len} 데이터 포인트</strong> | 
                    <strong>{min_len} 포인트</strong>로 정규화하여 분석
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # DataFrame 생성 (최신 데이터 기준으로)
            correlation_df = pd.DataFrame({
                k: v.tail(min_len).values for k, v in valid_data.items()
            })
            
            # 상관관계 매트릭스 계산
            corr_matrix = correlation_df.corr()
            
            # 두 열로 나누어 표시
            corr_col1, corr_col2 = st.columns([1.2, 0.8])
            
            with corr_col1:
                st.markdown("### 📈 상관관계 히트맵")
                
                # Plotly를 사용한 인터랙티브 히트맵
                fig = px.imshow(
                    corr_matrix.values,
                    labels=dict(x="지표", y="지표", color="상관계수"),
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    color_continuous_scale='RdBu_r',
                    range_color=[-1, 1],
                    title="지표간 상관관계 히트맵"
                )
                
                # 히트맵 스타일링
                fig.update_layout(
                    height=600,
                    font=dict(size=10),
                    title_font_size=16,
                    coloraxis_colorbar=dict(
                        title="상관계수",
                        tickmode="linear",
                        tick0=-1,
                        dtick=0.2,
                        len=0.8,
                        thickness=15
                    )
                )
                
                # 각 셀에 상관계수 값 표시
                for i in range(len(corr_matrix.index)):
                    for j in range(len(corr_matrix.columns)):
                        fig.add_annotation(
                            x=j, y=i,
                            text=f"{corr_matrix.iloc[i, j]:.2f}",
                            showarrow=False,
                            font=dict(color="black" if abs(corr_matrix.iloc[i, j]) < 0.5 else "white", size=9)
                        )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with corr_col2:
                st.markdown("### 🔍 주요 분석 결과")
                
                # 강한 상관관계 TOP 5
                mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
                corr_pairs = corr_matrix.mask(mask).stack().abs().sort_values(ascending=False)
                
                st.markdown("**🔥 강한 상관관계 TOP 5:**")
                
                for i, (pair, abs_corr_val) in enumerate(corr_pairs.head(5).items()):
                    if abs_corr_val > 0.1:  # 의미있는 상관관계만 표시
                        original_corr = corr_matrix.loc[pair[0], pair[1]]
                        
                        # 상관관계 강도와 방향
                        if abs_corr_val > 0.8:
                            strength = "매우 강한"
                            strength_color = "#ef4444"
                        elif abs_corr_val > 0.6:
                            strength = "강한"
                            strength_color = "#f97316"
                        elif abs_corr_val > 0.4:
                            strength = "중간"
                            strength_color = "#eab308"
                        else:
                            strength = "약한"
                            strength_color = "#22c55e"
                        
                        direction = "📈 양의 상관" if original_corr > 0 else "📉 음의 상관"
                        direction_color = "#10b981" if original_corr > 0 else "#ef4444"
                        
                        st.markdown(f"""
                        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 8px 0;">
                            <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 4px;">
                                {i+1}. {pair[0][:15]}{'...' if len(pair[0]) > 15 else ''} ↔ {pair[1][:15]}{'...' if len(pair[1]) > 15 else ''}
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: {strength_color}; font-weight: 600; font-size: 0.85rem;">
                                    {strength} ({original_corr:.3f})
                                </span>
                                <span style="color: {direction_color}; font-size: 0.8rem;">
                                    {direction}
                                </span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # 데이터 출처 정보
                st.markdown("### 📋 데이터 출처")
                source_info = {}
                for name, source in data_sources.items():
                    if name in valid_data:
                        if source not in source_info:
                            source_info[source] = []
                        source_info[source].append(name)
                
                for source, indicators in source_info.items():
                    st.markdown(f"**{source}:** {len(indicators)}개 지표")
                    with st.expander(f"{source} 상세", expanded=False):
                        for indicator in indicators:
                            st.write(f"• {indicator}")
                
                # 시장 인사이트 개선
                st.markdown("### 💡 시장 인사이트")
                
                insights = []
                
                # VIX 관련 분석
                vix_cols = [col for col in corr_matrix.columns if 'VIX' in col or 'vix' in col.lower()]
                if vix_cols:
                    vix_col = vix_cols[0]
                    negative_corr = corr_matrix[vix_col][corr_matrix[vix_col] < -0.3].sort_values()
                    if not negative_corr.empty:
                        insights.append(f"🔴 **위험회피 신호**: {vix_col}가 {negative_corr.index[0]}와 강한 역상관(-{abs(negative_corr.iloc[0]):.2f})")
                
                # 금리 관련 분석
                rate_cols = [col for col in corr_matrix.columns if '금리' in col or '수익률' in col]
                if rate_cols:
                    rate_col = rate_cols[0]
                    negative_corr = corr_matrix[rate_col][corr_matrix[rate_col] < -0.2].sort_values()
                    if not negative_corr.empty:
                        insights.append(f"📊 **금리 영향**: {rate_col} 상승 시 {negative_corr.index[0]} 하락 경향")
                
                # 달러 관련 분석  
                dollar_cols = [col for col in corr_matrix.columns if '달러' in col]
                if dollar_cols:
                    dollar_col = dollar_cols[0]
                    negative_corr = corr_matrix[dollar_col][corr_matrix[dollar_col] < -0.2].sort_values()
                    if not negative_corr.empty:
                        insights.append(f"💵 **달러 강세**: {dollar_col} 상승 시 {negative_corr.index[0]} 하락")
                
                # 인사이트 표시
                if insights:
                    for insight in insights:
                        st.markdown(f"• {insight}")
                else:
                    st.markdown("• 📈 현재 데이터로는 명확한 패턴 식별 어려움")
                    st.markdown("• 🔄 더 많은 데이터 수집 후 재분석 권장")
        
        else:
            st.markdown("""
            <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 12px; padding: 20px; text-align: center;">
                <h3 style="color: #92400e; margin: 0 0 12px 0;">📊 상관관계 분석 준비 중</h3>
                <p style="color: #92400e; margin: 0;">
                    현재 <strong>{len(valid_data)}개</strong> 지표만 사용 가능합니다.<br>
                    최소 3개 이상의 지표가 필요하며, FRED API 설정을 확인해보세요.
                </p>
            </div>
            """.format(len(valid_data)), unsafe_allow_html=True)
            
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.markdown(f"""
        <div style="background: #fee2e2; border: 1px solid #ef4444; border-radius: 12px; padding: 20px;">
            <h4 style="color: #b91c1c; margin: 0 0 8px 0;">⚠️ 상관관계 분석 오류</h4>
            <p style="color: #b91c1c; margin: 0; font-family: monospace; font-size: 0.9rem;">
                {error_msg}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # 업데이트 시간 표시
    st.markdown("---")
    st.markdown(f"**📅 마지막 업데이트:** {get_kst_now().strftime('%Y-%m-%d %H:%M:%S KST')}")
    st.markdown("**💡 참고:** 실제 거래 전 공식 데이터를 확인하시기 바랍니다.")


# 🔍 데이터 로딩 상태 스타일을 차용한 로딩 화면
def show_loading_status(message: str):
    """🔍 데이터 로딩 상태 스타일 로딩 화면"""
    return st.info(f"🔍 {message}")

def show_step_status(step_number: int, total_steps: int, current_step: str):
    """단계별 상태 표시"""
    progress_percentage = (step_number / total_steps) * 100
    
    # 단계별 아이콘 매핑
    step_icons = {
        1: "📡",
        2: "🔢", 
        3: "📈",
        4: "✨"
    }
    
    icon = step_icons.get(step_number, "🔍")
    
    # 진행률에 따른 상태 메시지
    if step_number == total_steps:
        return st.success(f"{icon} {current_step} (완료!)")
    else:
        return st.info(f"{icon} {current_step} ({progress_percentage:.0f}% 완료)")

# Market Agent 데이터 시각화 함수들
@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_stock_data_for_viz(symbol: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """주식 데이터 가져오기 with enhanced error handling and validation"""
    try:
        # Input validation
        if not symbol:
            return None
            
        # Sanitize and validate the symbol
        clean_symbol = sanitize_ticker(symbol)
        if not validate_ticker(clean_symbol):
            st.error(f"Invalid ticker symbol: {symbol}")
            return None
        
        # Validate period parameter
        valid_periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        if period not in valid_periods:
            st.warning(f"Invalid period '{period}', using default '6mo'")
            period = "6mo"
            
        # Fetch data with timeout and error handling
        ticker = yf.Ticker(clean_symbol)
        
        # Add progress indicator for slow requests
        with st.spinner(f"Loading data for {clean_symbol}..."):
            data = ticker.history(period=period, timeout=10)
        
        if data.empty:
            st.error(f"No data found for {clean_symbol}. Please verify the ticker symbol.")
            return None
        
        # Basic data validation
        if len(data) < 2:
            st.warning(f"Insufficient data for {clean_symbol} (only {len(data)} data points)")
            return None
            
        # Check for missing essential columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            st.error(f"Missing required data columns for {clean_symbol}: {missing_columns}")
            return None
            
        return data
        
    except TimeoutError:
        st.error(f"Timeout loading data for {symbol}. Please try again later.")
        return None
    except ConnectionError:
        st.error("Network connection error. Please check your internet connection.")
        return None
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.error(f"Data loading failed for {symbol}: {error_msg}")
        logger.error(f"[STOCK_DATA] Failed to load data for {symbol}: {error_msg}")
        return None

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def calculate_technical_indicators(data: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """기술적 지표 계산 with improved error handling and validation"""
    if data is None or data.empty:
        return None
    
    try:
        df = data.copy()
        
        # Validate required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns for technical analysis: {missing_columns}")
            return None
        
        # 인덱스가 날짜인 경우 Date 컬럼으로 저장
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            df.rename(columns={'Date': 'Date'}, inplace=True)
        else:
            df = df.reset_index()
        
        # Minimum data validation
        min_data_points = 50  # Need at least 50 data points for meaningful indicators
        if len(df) < min_data_points:
            st.warning(f"Insufficient data for technical analysis (need at least {min_data_points} points, got {len(df)})")
            return df  # Return basic data without indicators
        
        # 기본 이동평균들 (with validation)
        try:
            df['sma_10'] = df['Close'].rolling(window=min(10, len(df))).mean()
            df['sma_20'] = df['Close'].rolling(window=min(20, len(df))).mean()
            df['sma_50'] = df['Close'].rolling(window=min(50, len(df))).mean()
            df['sma_200'] = df['Close'].rolling(window=min(200, len(df))).mean()
        except Exception as e:
            logger.warning(f"[INDICATORS] SMA calculation error: {sanitize_log_message(str(e))}")
        
        # 지수이동평균
        try:
            df['ema_10'] = df['Close'].ewm(span=10).mean()
            df['ema_20'] = df['Close'].ewm(span=20).mean()
        except Exception as e:
            logger.warning(f"[INDICATORS] EMA calculation error: {sanitize_log_message(str(e))}")
        
        # RSI 계산 (with zero division protection)
        try:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            
            # Prevent division by zero
            loss = loss.replace(0, 0.0001)
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Clamp RSI values to valid range [0, 100]
            df['rsi'] = df['rsi'].clip(0, 100)
        except Exception as e:
            logger.warning(f"[INDICATORS] RSI calculation error: {sanitize_log_message(str(e))}")
        
        # MACD 계산
        try:
            ema_12 = df['Close'].ewm(span=12).mean()
            ema_26 = df['Close'].ewm(span=26).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
        except Exception as e:
            logger.warning(f"[INDICATORS] MACD calculation error: {sanitize_log_message(str(e))}")
        
        # 볼린저 밴드 (with validation)
        try:
            df['bb_middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            
            # Ensure standard deviation is valid
            bb_std = bb_std.fillna(0)
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        except Exception as e:
            logger.warning(f"[INDICATORS] Bollinger Bands calculation error: {sanitize_log_message(str(e))}")
        
        # ATR 계산 (with validation)
        try:
            high_low = df['High'] - df['Low']
            high_close = abs(df['High'] - df['Close'].shift())
            low_close = abs(df['Low'] - df['Close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
        except Exception as e:
            logger.warning(f"[INDICATORS] ATR calculation error: {sanitize_log_message(str(e))}")
        
        # VWMA 계산 (with zero volume protection)
        try:
            def vwma(price: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
                volume_safe = volume.replace(0, 1)  # Prevent division by zero
                return (price * volume_safe).rolling(window=window).sum() / volume_safe.rolling(window=window).sum()
            
            df['vwma'] = vwma(df['Close'], df['Volume'], 20)
        except Exception as e:
            logger.warning(f"[INDICATORS] VWMA calculation error: {sanitize_log_message(str(e))}")
        
        # 스토캐스틱 계산 (with zero division protection)
        try:
            low_min = df['Low'].rolling(window=14).min()
            high_max = df['High'].rolling(window=14).max()
            
            # Prevent division by zero
            range_diff = high_max - low_min
            range_diff = range_diff.replace(0, 0.0001)
            
            df['stoch_k'] = 100 * (df['Close'] - low_min) / range_diff
            df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
            
            # Clamp values to valid range [0, 100]
            df['stoch_k'] = df['stoch_k'].clip(0, 100)
            df['stoch_d'] = df['stoch_d'].clip(0, 100)
        except Exception as e:
            logger.warning(f"[INDICATORS] Stochastic calculation error: {sanitize_log_message(str(e))}")
        
        return df
        
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.error(f"Technical indicators calculation failed: {error_msg}")
        logger.error(f"[INDICATORS] Calculation failed: {error_msg}")
        return data  # Return original data if calculation fails

def create_price_chart(data, symbol):
    """가격 차트 생성"""
    if data is None or data.empty:
        return None
        
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=[f'{symbol} 주가 차트', '거래량']
    )
    
    # 캔들스틱 차트 - 인덱스가 날짜인지 확인하고 처리
    if 'Date' in data.columns:
        x_axis = data['Date']
    else:
        x_axis = data.index
    
    fig.add_trace(
        go.Candlestick(
            x=x_axis,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="가격",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    # 이동평균선 추가
    if 'sma_20' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=data['sma_20'],
                name='SMA 20',
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )
    
    if 'sma_50' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=data['sma_50'],
                name='SMA 50',
                line=dict(color='orange', width=2)
            ),
            row=1, col=1
        )
    
    if 'ema_10' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=data['ema_10'],
                name='EMA 10',
                line=dict(color='purple', width=2)
            ),
            row=1, col=1
        )
    
    # 볼린저 밴드
    if all(col in data.columns for col in ['bb_upper', 'bb_middle', 'bb_lower']):
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=data['bb_upper'],
                name='볼린저 상단',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=False
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=data['bb_lower'],
                name='볼린저 하단',
                line=dict(color='gray', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(128,128,128,0.1)',
                showlegend=False
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=data['bb_middle'],
                name='볼린저 중간 (SMA 20)',
                line=dict(color='red', width=1, dash='dot')
            ),
            row=1, col=1
        )
    
    # 거래량
    fig.add_trace(
        go.Bar(
            x=x_axis,
            y=data['Volume'],
            name='거래량',
            marker_color='lightblue'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title=f'{symbol} 주가 및 기술적 지표',
        xaxis_rangeslider_visible=False,
        height=800,
        showlegend=True,
        # 모바일 최적화
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 터치 드래그는 유지, 줌만 비활성화
        dragmode='pan'
    )
    
    # 모바일에서 줌 비활성화하되 스크롤은 유지
    fig.update_layout(
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )
    
    return fig

def create_macd_chart(data, symbol):
    """MACD 차트 생성"""
    if data is None or not all(col in data.columns for col in ['macd', 'macd_signal', 'macd_histogram']):
        return None
    
    # NaN 값들을 제거
    valid_data = data.dropna(subset=['macd', 'macd_signal', 'macd_histogram'])
    if valid_data.empty:
        st.warning("MACD 계산을 위한 충분한 데이터가 없습니다.")
        return None
    
    fig = go.Figure()
    
    # X축 데이터 결정
    if 'Date' in valid_data.columns:
        x_axis = valid_data['Date']
    else:
        x_axis = valid_data.index
    
    # MACD 라인
    fig.add_trace(
        go.Scatter(
            x=x_axis,
            y=valid_data['macd'],
            name='MACD',
            line=dict(color='blue', width=2)
        )
    )
    
    # MACD 시그널
    fig.add_trace(
        go.Scatter(
            x=x_axis,
            y=valid_data['macd_signal'],
            name='MACD Signal',
            line=dict(color='orange', width=2)
        )
    )
    
    # MACD 히스토그램
    colors = ['red' if val < 0 else 'green' for val in valid_data['macd_histogram']]
    fig.add_trace(
        go.Bar(
            x=x_axis,
            y=valid_data['macd_histogram'],
            name='MACD Histogram',
            marker_color=colors,
            opacity=0.7
        )
    )
    
    fig.update_layout(
        title=f'{symbol} MACD 지표',
        xaxis_title='날짜',
        yaxis_title='값',
        height=400,
        # 모바일 최적화
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 터치 드래그는 유지, 줌만 비활성화
        dragmode='pan',
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )
    
    return fig

def create_rsi_chart(data, symbol):
    """RSI 차트 생성"""
    if data is None or 'rsi' not in data.columns:
        return None
    
    # NaN 값들을 제거
    valid_data = data.dropna(subset=['rsi'])
    if valid_data.empty:
        st.warning("RSI 계산을 위한 충분한 데이터가 없습니다.")
        return None
    
    fig = go.Figure()
    
    # X축 데이터 결정
    if 'Date' in valid_data.columns:
        x_axis = valid_data['Date']
    else:
        x_axis = valid_data.index
    
    # RSI 라인
    fig.add_trace(
        go.Scatter(
            x=x_axis,
            y=valid_data['rsi'],
            name='RSI',
            line=dict(color='purple', width=2)
        )
    )
    
    # 과매수/과매도 라인
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="과매수 (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="과매도 (30)")
    fig.add_hline(y=50, line_dash="dot", line_color="gray", annotation_text="중립 (50)")
    
    fig.update_layout(
        title=f'{symbol} RSI 지표',
        xaxis_title='날짜',
        yaxis_title='RSI',
        yaxis=dict(range=[0, 100], fixedrange=True),
        height=400,
        # 모바일 최적화
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 터치 드래그는 유지, 줌만 비활성화
        dragmode='pan',
        xaxis=dict(fixedrange=True)
    )
    
    return fig

def create_atr_chart(data, symbol):
    """ATR 차트 생성"""
    if data is None or 'atr' not in data.columns:
        return None
    
    fig = go.Figure()
    
    # X축 데이터 결정
    if 'Date' in data.columns:
        x_axis = data['Date']
    else:
        x_axis = data.index
    
    # ATR 라인
    fig.add_trace(
        go.Scatter(
            x=x_axis,
            y=data['atr'],
            name='ATR',
            line=dict(color='red', width=2),
            fill='tozeroy',
            fillcolor='rgba(255,0,0,0.1)'
        )
    )
    
    fig.update_layout(
        title=f'{symbol} ATR (Average True Range) 변동성 지표',
        xaxis_title='날짜',
        yaxis_title='ATR',
        height=400,
        # 모바일 최적화
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 터치 드래그는 유지, 줌만 비활성화
        dragmode='pan',
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )
    
    return fig

def create_volume_analysis_chart(data, symbol):
    """거래량 분석 차트"""
    if data is None:
        return None
    
    if 'Volume' not in data.columns or 'Close' not in data.columns:
        return None
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.4],
        subplot_titles=[f'{symbol} 거래량 vs 가격', '거래량 이동평균']
    )
    
    # X축 데이터 결정
    if 'Date' in data.columns:
        x_axis = data['Date']
    else:
        x_axis = data.index
    
    # 가격 변화에 따른 거래량 색상
    price_change = data['Close'].pct_change()
    colors = ['red' if change < 0 else 'green' for change in price_change]
    
    # 거래량 바
    fig.add_trace(
        go.Bar(
            x=x_axis,
            y=data['Volume'],
            name='거래량',
            marker_color=colors,
            opacity=0.7
        ),
        row=1, col=1
    )
    
    # VWMA (Volume Weighted Moving Average)
    if 'vwma' in data.columns:
        fig.add_trace(
            go.Scatter(
                x=x_axis,
                y=data['vwma'],
                name='VWMA',
                line=dict(color='orange', width=2)
            ),
            row=1, col=1
        )
    
    # 거래량 이동평균
    volume_ma = data['Volume'].rolling(window=20).mean()
    fig.add_trace(
        go.Scatter(
            x=x_axis,
            y=volume_ma,
            name='거래량 20일 평균',
            line=dict(color='blue', width=2)
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title=f'{symbol} 거래량 분석',
        height=600,
        showlegend=True,
        # 모바일 최적화
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 터치 드래그는 유지, 줌만 비활성화
        dragmode='pan'
    )
    
    # 서브플롯의 각 축에 대해 고정 범위 설정 (줌 비활성화)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    
    return fig

def create_market_agent_dashboard():
    """Market Agent 데이터 시각화 대시보드"""
    try:
        st.header("📈 Market Agent 주식 통계 시각화")
        
        # 메인 영역에서 설정
        st.subheader("🎯 분석 설정")
        
        # 설정을 3개 열로 배치
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            # 티커 입력 with validation
            ticker_input = st.text_input(
                "주식 티커 심볼", 
                value=DEFAULT_TICKER,
                help="예: AAPL, TSLA, GOOGL, SPY",
                key="market_ticker",
                max_chars=MAX_TICKER_LENGTH
            )
            
            # Sanitize and validate ticker
            ticker = sanitize_ticker(ticker_input)
            if ticker_input and not validate_ticker(ticker):
                st.error("⚠️ Invalid ticker symbol. Please use only letters and numbers.")
                ticker = DEFAULT_TICKER
        
        with col2:
            # 기간 선택
            period_options = {
                "1개월": "1mo",
                "3개월": "3mo", 
                "6개월": "6mo",
                "1년": "1y",
                "2년": "2y"
            }
            
            selected_period = st.selectbox(
                "분석 기간",
                options=list(period_options.keys()),
                index=2,  # 기본값: 6개월
                key="market_period"
            )
            
            period = period_options[selected_period]
        
        with col3:
            # 차트 선택을 더 컴팩트하게
            st.write("**📊 표시할 차트**")
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                show_price = st.checkbox("가격 & 이동평균", value=True, key="show_price")
                show_macd = st.checkbox("MACD", value=True, key="show_macd")
                show_rsi = st.checkbox("RSI", value=True, key="show_rsi")
            
            with chart_col2:
                show_atr = st.checkbox("ATR (변동성)", value=False, key="show_atr")
                show_volume = st.checkbox("거래량 분석", value=False, key="show_volume")
        
        st.markdown("---")
        
        if not ticker:
            st.warning("티커 심볼을 입력해주세요.")
            return
        
        # 상태 컨테이너 생성
        status_container = st.empty()
        
        # 1단계: 데이터 로드
        with status_container:
            show_step_status(1, 4, f"{ticker} 주식 데이터 다운로드 중...")
        
        stock_data = get_stock_data_for_viz(ticker, period)
        
        if stock_data is None or stock_data.empty:
            status_container.empty()
            st.error(f"❌ {ticker} 데이터를 불러올 수 없습니다. 다른 티커를 시도해보세요.")
            return
        
        # 2단계: 기술적 지표 계산
        with status_container:
            show_step_status(2, 4, "기술적 지표 계산 중...")
        
        technical_data = calculate_technical_indicators(stock_data)
        
        # 3단계: 차트 생성 준비
        with status_container:
            show_step_status(3, 4, "차트 생성 중...")
        
        time.sleep(0.2)  # 잠시 표시
        
        # 4단계: 완료
        with status_container:
            show_step_status(4, 4, "분석 완료!")
        
        time.sleep(0.5)  # 완료 메시지 표시
        
        # 상태 메시지 제거
        status_container.empty()
        
        # 기본 정보를 뱃지 스타일로 표시
        current_price = stock_data['Close'].iloc[-1]
        prev_price = stock_data['Close'].iloc[-2]
        price_change = current_price - prev_price
        price_change_pct = (price_change / prev_price) * 100
        
        volume = stock_data['Volume'].iloc[-1]
        avg_volume = stock_data['Volume'].tail(20).mean()
        volume_change = ((volume - avg_volume) / avg_volume) * 100
        
        high_52w = stock_data['High'].tail(252).max()  # 약 1년
        low_52w = stock_data['Low'].tail(252).min()
    
        # RSI 정보는 기술적 지표 요약에서 표시됨
    
        # 가격 변화 색상
        price_color = "#44ff44" if price_change >= 0 else "#ff4444"
        volume_color = "#44ff44" if volume_change >= 0 else "#ff4444"
        
        # 뱃지 스타일 메트릭 표시
        st.markdown(f"""
    <div style="display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0;">
        <div style="background: white; border: 2px solid #e0e0e0; border-radius: 12px; padding: 12px 16px; min-width: 160px;">
            <div style="font-size: 0.75em; color: #666; font-weight: 600; margin-bottom: 4px;">현재 가격</div>
            <div style="font-size: 1.5em; font-weight: bold; color: #333;">${current_price:.2f}</div>
            <div style="font-size: 0.8em; color: {price_color}; font-weight: 600;">{price_change:+.2f} ({price_change_pct:+.2f}%)</div>
        </div>
        <div style="background: white; border: 2px solid #e0e0e0; border-radius: 12px; padding: 12px 16px; min-width: 160px;">
            <div style="font-size: 0.75em; color: #666; font-weight: 600; margin-bottom: 4px;">거래량</div>
            <div style="font-size: 1.2em; font-weight: bold; color: #333;">{volume:,.0f}</div>
            <div style="font-size: 0.8em; color: {volume_color}; font-weight: 600;">20일 평균 대비 {volume_change:+.1f}%</div>
        </div>
        <div style="background: white; border: 2px solid #e0e0e0; border-radius: 12px; padding: 12px 16px; min-width: 140px;">
            <div style="font-size: 0.75em; color: #666; font-weight: 600; margin-bottom: 4px;">52주 최고/최저</div>
            <div style="font-size: 1.1em; font-weight: bold; color: #333;">${high_52w:.2f}</div>
            <div style="font-size: 0.9em; color: #666; font-weight: 600;">${low_52w:.2f}</div>
        </div>
    </div>
        """, unsafe_allow_html=True)
        
        # 차트 표시
        if show_price:
            st.subheader("📈 가격 차트 및 이동평균")
            price_chart = create_price_chart(technical_data, ticker)
            if price_chart:
                st.plotly_chart(price_chart, use_container_width=True, config={
                    'displayModeBar': False,
                    'scrollZoom': False,
                    'doubleClick': False,
                    'showTips': False,
                    'staticPlot': False,
                    'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
                })
        
        # 2개 열로 나누어 차트 배치
        col1, col2 = st.columns(2)
        
        with col1:
            if show_macd:
                st.subheader("📊 MACD")
                macd_chart = create_macd_chart(technical_data, ticker)
                if macd_chart:
                    st.plotly_chart(macd_chart, use_container_width=True, config={
                        'displayModeBar': False,
                        'scrollZoom': False,
                        'doubleClick': False,
                        'showTips': False,
                        'staticPlot': False,
                        'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
                    })
            
            if show_atr:
                st.subheader("📈 ATR (변동성)")
                atr_chart = create_atr_chart(technical_data, ticker)
                if atr_chart:
                    st.plotly_chart(atr_chart, use_container_width=True, config={
                        'displayModeBar': False,
                        'scrollZoom': False,
                        'doubleClick': False,
                        'showTips': False,
                        'staticPlot': False,
                        'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
                    })
        
        with col2:
            if show_rsi:
                st.subheader("⚡ RSI")
                rsi_chart = create_rsi_chart(technical_data, ticker)
                if rsi_chart:
                    st.plotly_chart(rsi_chart, use_container_width=True, config={
                        'displayModeBar': False,
                        'scrollZoom': False,
                        'doubleClick': False,
                        'showTips': False,
                        'staticPlot': False,
                        'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
                    })
            
            if show_volume:
                st.subheader("📊 거래량 분석")
                volume_chart = create_volume_analysis_chart(technical_data, ticker)
                if volume_chart:
                    st.plotly_chart(volume_chart, use_container_width=True, config={
                        'displayModeBar': False,
                        'scrollZoom': False,
                        'doubleClick': False,
                        'showTips': False,
                        'staticPlot': False,
                        'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
                    })
        
        # 기술적 지표 요약 테이블
        if technical_data is not None:
            st.subheader("📋 기술적 지표 요약")
            
            summary_data = []
            
            # 현재 가격과 이동평균 비교
            if 'sma_50' in technical_data.columns:
                sma_50 = technical_data['sma_50'].iloc[-1]
                if not pd.isna(sma_50):
                    sma_50_signal = "상승" if current_price > sma_50 else "하락"
                    summary_data.append(["SMA 50", f"${sma_50:.2f}", sma_50_signal])
            
            if 'sma_200' in technical_data.columns:
                sma_200 = technical_data['sma_200'].iloc[-1]
                if not pd.isna(sma_200):
                    sma_200_signal = "상승" if current_price > sma_200 else "하락"
                    summary_data.append(["SMA 200", f"${sma_200:.2f}", sma_200_signal])
            
            if 'ema_10' in technical_data.columns:
                ema_10 = technical_data['ema_10'].iloc[-1]
                if not pd.isna(ema_10):
                    ema_10_signal = "상승" if current_price > ema_10 else "하락"
                    summary_data.append(["EMA 10", f"${ema_10:.2f}", ema_10_signal])
            
            # RSI
            if 'rsi' in technical_data.columns:
                rsi = technical_data['rsi'].iloc[-1]
                if pd.isna(rsi):
                    summary_data.append(["RSI", "계산중", "데이터 부족"])
                else:
                    if rsi > 70:
                        rsi_signal = "과매수"
                    elif rsi < 30:
                        rsi_signal = "과매도"
                    else:
                        rsi_signal = "중립"
                    summary_data.append(["RSI", f"{rsi:.1f}", rsi_signal])
            
            # MACD
            if 'macd' in technical_data.columns and 'macd_signal' in technical_data.columns:
                macd = technical_data['macd'].iloc[-1]
                macd_signal = technical_data['macd_signal'].iloc[-1]
                if not pd.isna(macd) and not pd.isna(macd_signal):
                    macd_trend = "상승" if macd > macd_signal else "하락"
                    summary_data.append(["MACD", f"{macd:.3f}", macd_trend])
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data, columns=["지표", "현재 값", "신호"])
                st.table(summary_df)
    
    except Exception as e:
        st.error(f"Market Agent 대시보드 로딩 중 오류가 발생했습니다: {e}")
        st.info("다른 탭을 사용하거나 페이지를 새로고침 해보세요.")


# Load environment variables
load_dotenv()

# Import required modules from the trading system
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    from cli.models import AnalystType
except ImportError as e:
    st.error(f"Failed to import trading modules: {e}")
    st.stop()

# Set page config
st.set_page_config(
    page_title="TradingAgents Dashboard", 
    page_icon="💹",  # 예쁜 이모지로 변경
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced Custom CSS for modern, professional trading dashboard design
st.markdown("""
<style>
    /* CSS Variables for consistent theming */
    :root {
        /* Enhanced color palette */
        --primary-50: #f0f7ff;
        --primary-100: #e0efff;
        --primary-500: #0ea5e9;
        --primary-600: #0284c7;
        --primary-700: #0369a1;
        
        /* Semantic trading colors */
        --success-50: #ecfdf5;
        --success-500: #10b981;
        --success-600: #059669;
        
        --danger-50: #fef2f2;
        --danger-500: #ef4444;
        --danger-600: #dc2626;
        
        /* Enhanced neutral grays */
        --gray-50: #f8fafc;
        --gray-100: #f1f5f9;
        --gray-600: #475569;
        --gray-900: #0f172a;
    }

    /* Global app styling - Enhanced gradient background */
    .stApp {
        background: linear-gradient(135deg, #f0f7ff 0%, #f8fdff 30%, #ffffff 70%, #f8fafc 100%);
        min-height: 100vh;
    }
    
    /* Main content wrapper - Enhanced white container */
    .main .block-container {
        background: #ffffff;
        border-radius: 20px;
        padding: 2.5rem;
        margin: 1rem;
        box-shadow: 
            0 8px 32px rgba(14, 165, 233, 0.08),
            0 4px 16px rgba(14, 165, 233, 0.04);
        border: 1px solid rgba(14, 165, 233, 0.1);
        backdrop-filter: blur(8px);
    }
    
    /* Enhanced typography hierarchy */
    body, .stApp, .main, .stSidebar,
    h1, h2, h3, h4, h5, h6, p, span, div, label, 
    .stMarkdown, .stText, .streamlit-container {
        color: var(--gray-900) !important;
    }
    
    /* Modern heading styles with improved hierarchy */
    h1 {
        color: var(--primary-700) !important;
        font-size: clamp(1.875rem, 4vw, 2.5rem) !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
        line-height: 1.2 !important;
    }
    
    h2 {
        color: var(--primary-600) !important;
        font-size: clamp(1.5rem, 3vw, 1.875rem) !important;
        font-weight: 700 !important;
        letter-spacing: -0.015em !important;
    }
    
    h3 {
        color: var(--primary-600) !important;
        font-size: clamp(1.25rem, 2.5vw, 1.5rem) !important;
        font-weight: 600 !important;
    }
    
    /* Sidebar - Light blue accent */
    .css-1d391kg, .stSidebar {
        background: linear-gradient(180deg, #f5f9ff 0%, #ffffff 100%);
        border-right: 1px solid rgba(135, 206, 250, 0.2);
    }
    
    /* Sidebar content styling */
    .css-1d391kg *, .stSidebar * {
        color: #2c3e50 !important;
    }
    
    /* Clean form elements */
    .stTextInput input, .stSelectbox select, .stDateInput input {
        background: #ffffff !important;
        color: #2c3e50 !important;
        border: 2px solid #e3f2fd !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus, .stDateInput input:focus {
        border-color: #42a5f5 !important;
        box-shadow: 0 0 0 3px rgba(66, 165, 245, 0.1) !important;
        outline: none !important;
    }
    
    /* Clean checkboxes */
    .stCheckbox label {
        color: #2c3e50 !important;
        font-weight: 500 !important;
    }
    
    /* Enhanced modern metrics cards */
    .stMetric {
        background: linear-gradient(145deg, #ffffff 0%, var(--gray-50) 100%);
        border: 1px solid rgba(15, 23, 42, 0.05);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 
            0 1px 3px rgba(15, 23, 42, 0.04),
            0 1px 2px rgba(15, 23, 42, 0.06);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        min-height: 100px;
    }
    
    .stMetric::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--primary-500);
        transform: scaleX(0);
        transform-origin: left;
        transition: transform 0.3s ease;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 
            0 8px 25px rgba(15, 23, 42, 0.08),
            0 3px 10px rgba(15, 23, 42, 0.05);
    }
    
    .stMetric:hover::before {
        transform: scaleX(1);
    }
    
    .stMetric label {
        color: var(--gray-600) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.5rem !important;
    }
    
    .stMetric > div > div[data-testid="metric-value"] {
        color: var(--gray-900) !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        line-height: 1 !important;
        margin-bottom: 0.25rem !important;
    }
    
    .stMetric > div > div[data-testid="metric-delta"] {
        color: var(--success-600) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Enhanced agent status cards with modern flow design */
    .agent-status {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.875rem;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid transparent;
        min-width: 120px;
        justify-content: center;
        position: relative;
        overflow: hidden;
    }
    
    .agent-status::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s ease;
    }
    
    .agent-status:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    }
    
    .agent-status:hover::before {
        left: 100%;
    }
    
    .status-pending {
        background: linear-gradient(135deg, #fef3c7, #fbbf24);
        color: #92400e;
        border-color: #f59e0b;
    }
    
    .status-in-progress {
        background: linear-gradient(135deg, #dbeafe, #60a5fa);
        color: #1e40af;
        border-color: #3b82f6;
        animation: pulse-glow 2s infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { 
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
            transform: scale(1);
        }
        50% { 
            box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
            transform: scale(1.02);
        }
    }
    
    .status-completed {
        background: linear-gradient(135deg, #d1fae5, #34d399);
        color: #047857;
        border-color: #10b981;
    }
    
    .status-error {
        background: linear-gradient(135deg, #fee2e2, #f87171);
        color: #b91c1c;
        border-color: #ef4444;
    }
    
    /* Agent flow connector */
    .agent-connector {
        display: inline-block;
        width: 20px;
        height: 2px;
        background: linear-gradient(90deg, #e2e8f0, #cbd5e1);
        margin: 0 0.5rem;
        position: relative;
    }
    
    .agent-connector::after {
        content: '→';
        position: absolute;
        right: -8px;
        top: -8px;
        color: #64748b;
        font-size: 0.75rem;
    }
    
    /* Log container */
    .log-container {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
        max-height: 400px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.875rem;
        color: #374151;
    }
    
    /* Enhanced welcome header with modern design */
    .welcome-header {
        text-align: center;
        padding: 4rem 3rem;
        background: linear-gradient(135deg, var(--primary-50) 0%, #ffffff 40%, var(--gray-50) 70%, #ffffff 100%);
        color: var(--primary-700);
        border-radius: 24px;
        margin-bottom: 3rem;
        box-shadow: 
            0 8px 32px rgba(14, 165, 233, 0.08),
            0 4px 16px rgba(14, 165, 233, 0.04);
        border: 2px solid rgba(14, 165, 233, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .welcome-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary-500), var(--primary-600), var(--primary-500));
    }
    
    .welcome-header h1 {
        margin-bottom: 1rem;
        font-size: clamp(2rem, 5vw, 3rem) !important;
        font-weight: 800 !important;
        color: var(--primary-700) !important;
        letter-spacing: -0.02em !important;
        background: linear-gradient(135deg, var(--primary-600), var(--primary-700));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .welcome-header h3 {
        margin-bottom: 1.5rem;
        font-weight: 500 !important;
        color: var(--gray-600) !important;
        font-size: clamp(1.125rem, 2.5vw, 1.375rem) !important;
        line-height: 1.4 !important;
    }
    
    .welcome-header p {
        color: var(--gray-600) !important;
        font-size: clamp(0.875rem, 1.5vw, 1rem) !important;
        font-weight: 500 !important;
        line-height: 1.6 !important;
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Enhanced primary buttons with modern design */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-700) 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.875rem 2rem;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 1px 3px rgba(0, 0, 0, 0.1),
            0 1px 2px rgba(0, 0, 0, 0.06);
        position: relative;
        overflow: hidden;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.6s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 
            0 4px 15px rgba(3, 105, 161, 0.3),
            0 2px 4px rgba(0, 0, 0, 0.06);
        background: linear-gradient(135deg, var(--primary-700) 0%, var(--primary-600) 100%);
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:active {
        transform: translateY(0px);
        box-shadow: 0 2px 8px rgba(3, 105, 161, 0.2);
    }
    
    /* Secondary buttons (Stop button) */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.25);
    }
    
    .stButton > button[kind="secondary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.35);
        background: linear-gradient(135deg, #ee5a52 0%, #ff6b6b 100%);
    }
    
    /* Form inputs */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        border: 2px solid #e2e8f0;
        border-radius: 0.5rem;
        color: #1f2937;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .stSelectbox > div > div > div {
        background-color: #ffffff;
        border: 2px solid #e2e8f0;
        color: #1f2937;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        color: #1f2937 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background-color: #f8fafc;
        color: #6b7280;
        border-radius: 0.5rem 0.5rem 0 0;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f1f5f9;
        color: #374151;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
    }
    
    /* Clean secondary buttons */
    .stButton[data-baseweb="button"][kind="secondary"] button {
        background: #ffffff;
        color: #1976d2 !important;
        border: 2px solid #e3f2fd;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton[data-baseweb="button"][kind="secondary"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(66, 165, 245, 0.2);
        background: #f5f9ff;
        border-color: #42a5f5;
    }
    
    /* Clean alert messages */
    .stSuccess {
        background: #f1f8e9;
        border: 2px solid #c8e6c9;
        border-radius: 8px;
        color: #2e7d32 !important;
        box-shadow: 0 2px 8px rgba(76, 175, 80, 0.1);
        padding: 1rem;
    }
    
    .stInfo {
        background: #e3f2fd;
        border: 2px solid #bbdefb;
        border-radius: 8px;
        color: #1976d2 !important;
        box-shadow: 0 2px 8px rgba(66, 165, 245, 0.1);
        padding: 1rem;
    }
    
    .stWarning {
        background: #fff8e1;
        border: 2px solid #ffcc02;
        border-radius: 8px;
        color: #e65100 !important;
        box-shadow: 0 2px 8px rgba(255, 193, 7, 0.1);
        padding: 1rem;
    }
    
    .stError {
        background: #ffebee;
        border: 2px solid #ffcdd2;
        border-radius: 8px;
        color: #c62828 !important;
        box-shadow: 0 2px 8px rgba(244, 67, 54, 0.1);
        padding: 1rem;
    }
    
    /* Preserve text colors in messages */
    .stSuccess *, .stInfo *, .stWarning *, .stError * {
        color: inherit !important;
    }
    
    
    
    /* Header styling - consistent colors */
    .css-18e3th9, [data-testid="stHeader"] {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    
    /* App header */
    header[data-testid="stHeader"] {
        background-color: #ffffff !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }
    
    /* Toolbar buttons in header */
    .css-18e3th9 button, [data-testid="stHeader"] button {
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* All header elements */
    .css-18e3th9 *, [data-testid="stHeader"] * {
        color: #111827 !important;
    }
    
    /* Enhanced modern tab system */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--gray-50);
        border-radius: 12px;
        padding: 0.25rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #64748b !important;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(14, 165, 233, 0.05);
        color: var(--primary-600) !important;
        transform: translateY(-1px);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-600), var(--primary-700)) !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
    }
    
    /* Clean DataFrames */
    .stDataFrame {
        background: #ffffff;
        border: 2px solid #e3f2fd;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(66, 165, 245, 0.08);
        overflow: hidden;
    }
    
    .stDataFrame th {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
        color: #1976d2 !important;
        font-weight: 700 !important;
        padding: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stDataFrame td {
        color: #2c3e50 !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid #f5f9ff !important;
    }
    
    .stDataFrame tr:hover {
        background: #f5f9ff !important;
    }
    
    /* Enhanced mobile optimization */
    @media (max-width: 768px) {
        /* Main container mobile optimization */
        .main .block-container {
            padding: 1.5rem;
            margin: 0.5rem;
            border-radius: 16px;
        }
        
        /* Welcome header mobile */
        .welcome-header {
            padding: 2rem 1.5rem;
            margin-bottom: 2rem;
        }
        
        /* Chart container mobile optimization */
        .stPlotlyChart {
            width: 100% !important;
            overflow-x: auto;
            touch-action: auto;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        
        /* Enhanced mobile chart handling */
        .js-plotly-plot .plotly {
            touch-action: auto !important;
            user-select: none !important;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            pointer-events: none !important;
        }
        
        /* Improved mobile metrics */
        .stMetric {
            margin-bottom: 1rem !important;
            padding: 1rem !important;
        }
        
        /* Enhanced mobile tabs */
        .stTabs [data-baseweb="tab"] {
            min-width: auto !important;
            font-size: 0.875rem !important;
            padding: 0.75rem 1rem !important;
        }
        
        /* Agent status mobile optimization */
        .agent-status {
            width: 100%;
            margin: 0.75rem 0;
            justify-content: space-between;
            padding: 1rem;
            font-size: 0.875rem;
        }
        
        /* Enhanced mobile columns */
        .stColumns > div {
            padding: 0 0.5rem !important;
        }
        
        /* Mobile buttons */
        .stButton > button {
            width: 100%;
            padding: 1rem 1.5rem;
            font-size: 1rem;
        }
        
        /* Mobile badge styles */
        div[style*="display: flex; flex-wrap: wrap"] {
            gap: 12px !important;
            justify-content: center;
        }
        
        div[style*="min-width: 160px"] {
            min-width: 280px !important;
            font-size: 0.9rem !important;
            text-align: center;
        }
    }
    
    /* Enhanced very small screen optimization */
    @media (max-width: 480px) {
        /* Main container for very small screens */
        .main .block-container {
            padding: 1rem;
            margin: 0.25rem;
            border-radius: 12px;
        }
        
        /* Welcome header very small screens */
        .welcome-header {
            padding: 1.5rem 1rem;
            margin-bottom: 1.5rem;
        }
        
        /* Enhanced tab design for small screens */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem !important;
            padding: 0.6rem 0.8rem !important;
        }
        
        /* Metric cards for small screens */
        .stMetric {
            padding: 0.75rem !important;
            margin-bottom: 0.75rem !important;
        }
        
        .stMetric > div > div[data-testid="metric-value"] {
            font-size: 1.5rem !important;
        }
        
        .stMetric label {
            font-size: 0.75rem !important;
        }
        
        /* Agent status very small screens */
        .agent-status {
            font-size: 0.75rem;
            padding: 0.75rem;
            min-width: 100px;
            margin: 0.5rem 0;
        }
        
        /* Enhanced badges for small screens */
        div[style*="min-width: 160px"] {
            min-width: 250px !important;
            padding: 12px 16px !important;
            font-size: 0.85rem !important;
        }
        
        div[style*="font-size: 1.5em"] {
            font-size: 1.25em !important;
        }
        
        /* Improved buttons for small screens */
        .stButton > button {
            padding: 0.875rem 1.25rem;
            font-size: 0.9rem;
        }
    }
    
    /* Loading states and animations */
    .loading-skeleton {
        background: linear-gradient(90deg, var(--gray-100) 25%, #e2e8f0 50%, var(--gray-100) 75%);
        background-size: 200% 100%;
        animation: loading-shimmer 2s infinite;
        border-radius: 8px;
    }
    
    @keyframes loading-shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    /* Smooth transitions for data updates */
    .data-transition {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Enhanced accessibility */
    *:focus {
        outline: 2px solid var(--primary-500);
        outline-offset: 2px;
        border-radius: 4px;
    }
    
    /* Financial data color coding */
    .positive-change {
        color: var(--success-600);
        background: var(--success-50);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-weight: 600;
    }
    
    .negative-change {
        color: var(--danger-600);
        background: var(--danger-50);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-weight: 600;
    }
    
    .neutral-change {
        color: var(--gray-600);
        background: var(--gray-100);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-weight: 600;
    }
</style>

""", unsafe_allow_html=True)

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('streamlit_analysis.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Initialize Database Manager with error handling
@st.cache_resource
def get_db_manager() -> Optional[DatabaseManager]:
    """Initialize database manager with error handling"""
    try:
        db_manager = DatabaseManager()
        return db_manager
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.error(f"Failed to initialize database manager: {error_msg}")
        logger.error(f"[DATABASE] Initialization failed: {error_msg}")
        return None

# DB 매니저 인스턴스
db_manager = get_db_manager()

# Check if database is available
if db_manager is None:
    st.error("❌ Database is not available. Some features may not work correctly.")
    st.stop()

def get_session_file(username=None):
    """Get session file path for specific user"""
    if username:
        return f".session_{username}.json"
    return ".current_session.json"

def save_session():
    """세션 저장 - DB 기반으로 변경되어 더이상 필요 없음"""
    # DB 매니저가 세션을 자동으로 관리하므로 별도 저장 불필요
    pass

def load_session():
    """Load session from database - check both session_state and query params"""
    # 먼저 session_state에서 세션 ID 확인
    session_id = getattr(st.session_state, 'session_id', None)
    
    # session_state에 없으면 query params에서 확인 (새로고침 대응)
    if not session_id:
        query_params = st.query_params
        session_id = query_params.get('session_id')
        
    if session_id:
        try:
            # DB에서 세션 유효성 검사
            username = db_manager.validate_session(session_id)
            
            if username:
                # 유효한 세션 - 상태 복원
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.session_id = session_id
                st.session_state.login_time = get_kst_naive_now()  # 현재 시간으로 갱신
                st.session_state.session_duration = 3600  # 1시간
                
                # URL에 세션 ID 유지 (새로고침 대응)
                st.query_params['session_id'] = session_id
                
                logger.info(f"[SESSION] DB session restored for {username}")
                return True
            else:
                # 세션 만료 또는 무효 - URL에서도 제거
                st.session_state.session_id = None
                if 'session_id' in st.query_params:
                    del st.query_params['session_id']
                logger.info(f"[SESSION] DB session expired or invalid: {session_id[:8] if session_id else 'None'}")
                
        except Exception as e:
            logger.error(f"[SESSION] Failed to validate DB session {session_id[:8] if session_id else 'None'}: {e}")
            st.session_state.session_id = None
            if 'session_id' in st.query_params:
                del st.query_params['session_id']
    
    # 기존 파일 세션 정리 (한번만 실행)
    cleanup_old_file_sessions()
    
    return False

def cleanup_old_file_sessions():
    """기존 파일 기반 세션 정리 (DB 전환 완료 후)"""
    try:
        session_files = [f for f in os.listdir('.') if f.startswith('.session_') and f.endswith('.json')]
        
        for session_file in session_files:
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    logger.info(f"[SESSION] Cleaned up old file session: {session_file}")
                except Exception as e:
                    logger.error(f"[SESSION] Failed to remove old session file {session_file}: {e}")
    except Exception as e:
        logger.error(f"[SESSION] Error during file session cleanup: {e}")

def clear_session():
    """Clear current user session from database"""
    session_id = getattr(st.session_state, 'session_id', None)
    username = getattr(st.session_state, 'username', None)
    
    if session_id:
        try:
            # DB에서 세션 무효화
            db_manager.invalidate_session(session_id)
            logger.info(f"[SESSION] DB session invalidated for {username}: {session_id[:8]}")
        except Exception as e:
            logger.error(f"[SESSION] Failed to invalidate DB session {session_id[:8] if session_id else 'None'}: {e}")
    
    # URL에서 세션 ID 제거
    if 'session_id' in st.query_params:
        del st.query_params['session_id']
    
    # 기존 파일 세션도 정리 (호환성)
    cleanup_old_file_sessions()

# Authentication functions
def init_auth_session_state():
    """Initialize authentication session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'blocked_until' not in st.session_state:
        st.session_state.blocked_until = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    if 'session_duration' not in st.session_state:
        st.session_state.session_duration = SESSION_DURATION_SECONDS

def is_session_expired():
    """Check if user session has expired using database"""
    if not st.session_state.authenticated:
        return False
    
    session_id = getattr(st.session_state, 'session_id', None)
    
    if not session_id:
        # 세션 ID가 없으면 만료된 것으로 간주
        return True
    
    # DB에서 세션 유효성 재검증
    username = db_manager.validate_session(session_id)
    
    if not username:
        # 세션 만료 또는 무효 - 간단하게 로그아웃 처리
        expired_user = st.session_state.get('username', 'Unknown')
        
        # Clear session
        clear_session()
        
        # Stop any running analysis
        if st.session_state.get('analysis_running', False):
            st.session_state.analysis_running = False
            st.session_state.stream_processing = False
        
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.session_id = None
        st.session_state.login_time = None
        
        logger.info(f"[AUTH] Session expired for {expired_user}")
        return True
    
    # 세션이 유효하면 사용자 정보 동기화
    if username != st.session_state.username:
        st.session_state.username = username
    
    return False

def is_blocked():
    """Check if user is currently blocked from logging in"""
    if st.session_state.blocked_until is None:
        return False
    
    current_time = get_kst_naive_now()
    blocked_until = st.session_state.blocked_until
    
    # KST 시간으로 처리
    if current_time.tzinfo is not None:
        current_time = current_time.replace(tzinfo=None)
    if blocked_until.tzinfo is not None:
        blocked_until = blocked_until.replace(tzinfo=None)
    
    if current_time < blocked_until:
        return True
    else:
        # Unblock user and reset attempts
        st.session_state.blocked_until = None
        st.session_state.login_attempts = 0
        return False

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with username and password using database"""
    try:
        # Input validation
        if not username or not password:
            return False
        
        # Sanitize inputs to prevent injection
        username = sanitize_log_message(username.strip())
        
        # Basic validation
        if len(username) > 50 or len(password) < MIN_PASSWORD_LENGTH:
            return False
        
        if db_manager.verify_user(username, password):
            # 인증 성공 - 세션 생성
            session_id = db_manager.create_session(username, duration_hours=1)
            
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.session_id = session_id
            st.session_state.login_attempts = 0
            st.session_state.login_time = get_kst_naive_now()
            st.session_state.blocked_until = None
            
            # URL에 세션 ID 추가 (새로고침 대응)
            st.query_params['session_id'] = session_id
            
            logger.info(f"[AUTH] User {username} successfully authenticated at {to_kst_string(get_kst_now())} - session will last 1 hour")
            return True
        else:
            st.session_state.login_attempts += 1
            logger.warning(f"[AUTH] Failed login attempt for {username}: {st.session_state.login_attempts}/5")
            
            # 클라이언트 사이드 차단
            if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
                st.session_state.blocked_until = get_kst_naive_now() + datetime.timedelta(minutes=BLOCK_DURATION_MINUTES)
                logger.warning(f"[AUTH] User blocked for {MAX_LOGIN_ATTEMPTS} failed attempts ({BLOCK_DURATION_MINUTES} minutes)")
            
            return False
    except Exception as e:
        logger.error(f"[AUTH] Authentication error for {username}: {e}")
        st.session_state.login_attempts += 1
        return False

def render_login_page():
    """Render the login page"""
    st.markdown("""
    <div class="welcome-header">
        <h1>트레이딩 에이전트 대시보드</h1>
        <h3>보안 인증이 필요합니다</h3>
        <p>계속하려면 인증 키를 입력해주세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if user is blocked
    if is_blocked():
        current_time = get_kst_naive_now()
        blocked_until = st.session_state.blocked_until
        
        # KST 시간으로 처리
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)
        if blocked_until.tzinfo is not None:
            blocked_until = blocked_until.replace(tzinfo=None)
        
        time_left = blocked_until - current_time
        minutes_left = int(time_left.total_seconds() / 60) + 1
        st.error(f"🚫 너무 많은 실패한 시도로 인해 접근이 차단되었습니다. {minutes_left}분 후에 다시 시도해주세요.")
        st.stop()
    
    # Show remaining attempts
    remaining_attempts = 5 - st.session_state.login_attempts
    if st.session_state.login_attempts > 0:
        if remaining_attempts > 0:
            st.warning(f"⚠️ {remaining_attempts}번의 시도가 남았습니다")
        
    # Login form
    with st.form("login_form"):
        st.subheader("🔑 사용자 인증")
        
        username = st.text_input(
            "사용자 이름",
            placeholder="사용자 이름을 입력하세요",
            help="등록된 사용자 이름을 입력하세요"
        )
        
        password = st.text_input(
            "비밀번호 입력", 
            type="password",
            placeholder="비밀번호를 입력하세요...",
            help="비밀번호를 입력하세요"
        )
        
        submitted = st.form_submit_button("🚀 로그인", type="primary")
        
        if submitted:
            if not username or not password:
                st.error("❌ 사용자 이름과 비밀번호를 모두 입력해주세요")
            else:
                if authenticate_user(username, password):
                    st.success(f"✅ 환영합니다, {username}님! 리다이렉트 중...")
                    time.sleep(1)
                    st.rerun()
                else:
                    remaining = 5 - st.session_state.login_attempts
                    if remaining > 0:
                        st.error(f"❌ 잘못된 인증 정보입니다. {remaining}번의 시도가 남았습니다.")
                    else:
                        st.error("🚫 너무 많은 시도로 인해 30분간 접근이 차단되었습니다.")
    
    # Instructions
    st.markdown("---")
    st.markdown("""
    ### 📋 사용 안내
    - 드롭다운에서 사용자 이름을 선택하세요
    - 비밀번호를 입력하세요
    - 30분간 차단되기 전까지 **5번의 시도** 기회가 있습니다
    - 각 사용자는 1시간 지속되는 개별 세션을 가집니다 (KST)
    - 브라우저 새로고침 후에도 세션이 유지됩니다
    - 모든 시간은 **한국 표준시(KST)**로 표시됩니다
    
    """)

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False
    
    if 'message_buffer' not in st.session_state:
        st.session_state.message_buffer = {
            'messages': deque(maxlen=MAX_MESSAGE_BUFFER_SIZE),
            'tool_calls': deque(maxlen=MAX_MESSAGE_BUFFER_SIZE),
            'agent_status': {
                "Market Analyst": "pending",
                "Social Analyst": "pending", 
                "News Analyst": "pending",
                "Fundamentals Analyst": "pending",
                "Bull Researcher": "pending",
                "Bear Researcher": "pending", 
                "Research Manager": "pending",
                "Trader": "pending",
                "Risky Analyst": "pending",
                "Neutral Analyst": "pending",
                "Safe Analyst": "pending",
                "Portfolio Manager": "pending",
            },
            'current_agent': None,
            'report_sections': {
                "market_report": None,
                "sentiment_report": None,
                "news_report": None,
                "fundamentals_report": None,
                "investment_plan": None,
                "trader_investment_plan": None,
                "final_trade_decision": None,
            },
            'final_state': None,
            'llm_call_count': 0,
            'tool_call_count': 0,
            'analysis_start_time': None,
            'analysis_end_time': None
        }
    
    # Initialize empty config - user will set these
    if 'config' not in st.session_state:
        st.session_state.config = {}
    
    # Initialize configuration state
    if 'config_set' not in st.session_state:
        st.session_state.config_set = False

# Helper functions for configuration
def get_llm_options():
    """Get LLM model options based on provider"""
    return {
        "openai": {
            "shallow": [
                ("GPT-4o-mini - Fast and efficient", "gpt-4o-mini"),
                ("GPT-4.1-nano - Ultra-lightweight", "gpt-4.1-nano"),
                ("GPT-4.1-mini - Compact model", "gpt-4.1-mini"),
                ("GPT-4o - Standard model", "gpt-4o"),
            ],
            "deep": [
                ("GPT-4.1-nano - Ultra-lightweight", "gpt-4.1-nano"),
                ("GPT-4.1-mini - Compact model", "gpt-4.1-mini"),
                ("GPT-4o - Standard model", "gpt-4o"),
                ("o4-mini - Specialized reasoning", "o4-mini"),
                ("o3-mini - Advanced reasoning", "o3-mini"),
                ("o3 - Full advanced reasoning", "o3"),
                ("o1 - Premier reasoning", "o1"),
            ]
        },
        "anthropic": {
            "shallow": [
                ("Claude Haiku 3.5 - Fast inference", "claude-3-5-haiku-latest"),
                ("Claude Sonnet 3.5 - Highly capable", "claude-3-5-sonnet-latest"),
                ("Claude Sonnet 3.7 - Exceptional reasoning", "claude-3-7-sonnet-latest"),
                ("Claude Sonnet 4 - High performance", "claude-sonnet-4-0"),
            ],
            "deep": [
                ("Claude Haiku 3.5 - Fast inference", "claude-3-5-haiku-latest"),
                ("Claude Sonnet 3.5 - Highly capable", "claude-3-5-sonnet-latest"),
                ("Claude Sonnet 3.7 - Exceptional reasoning", "claude-3-7-sonnet-latest"),
                ("Claude Sonnet 4 - High performance", "claude-sonnet-4-0"),
                ("Claude Opus 4 - Most powerful", "claude-opus-4-0"),
            ]
        },
        "google": {
            "shallow": [
                ("Gemini 2.0 Flash-Lite - Cost efficient", "gemini-2.0-flash-lite"),
                ("Gemini 2.0 Flash - Next generation", "gemini-2.0-flash"),
                ("Gemini 2.5 Flash - Adaptive thinking", "gemini-2.5-flash"),
            ],
            "deep": [
                ("Gemini 2.0 Flash-Lite - Cost efficient", "gemini-2.0-flash-lite"),
                ("Gemini 2.0 Flash - Next generation", "gemini-2.0-flash"),
                ("Gemini 2.5 Flash - Adaptive thinking", "gemini-2.5-flash"),
                ("Gemini 2.5 Pro", "gemini-2.5-pro"),
            ]
        }
    }

def get_provider_urls():
    """Get provider URL mappings"""
    return {
        "OpenAI": "https://api.openai.com/v1",
        "Anthropic": "https://api.anthropic.com/",
        "Google": "https://generativelanguage.googleapis.com/v1",
        "Openrouter": "https://openrouter.ai/api/v1",
        "Ollama": "http://localhost:11434/v1",
    }

def render_welcome_header():
    """Render the welcome header"""
    current_kst_time = to_kst_string(get_kst_now())
    st.markdown(f"""
    <div class="welcome-header">
        <h1>트레이딩 에이전트 대시보드</h1>
        <h3>다중 AI 에이전트 금융 거래 프레임워크</h3>
        <p><strong>작업 흐름:</strong> 🧑‍💼 분석팀 ➡️ 🧑‍🔬 리서치팀 ➡️ 💼 트레이더 ➡️ 🛡️ 리스크 관리 ➡️ 📊 포트폴리오 관리</p>
        <p style="font-size: 0.9em; opacity: 0.8;">🕒 현재 시간: {current_kst_time}</p>
        <p style="font-size: 0.9em; opacity: 0.8;">
            🐝 <span style="background: #fffbe7; border-radius: 6px; padding: 2px 8px; color: #d48806; font-weight: 600;">꿀팁</span> : 
            <a href="https://futuresnow.gitbook.io/newstoday" target="_blank" style="color: #1976d2; text-decoration: underline;">
                오선의 미국증시
            </a>에서 다른 미국증시 요약도 볼 수 있어요!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add architecture diagram without header
    try:
        st.image("assets/schema.png", caption="트레이딩 에이전트 시스템 아키텍처", use_container_width=True)
    except Exception as e:
        st.warning(f"아키텍처 다이어그램을 로드할 수 없습니다: {e}")
        st.info("아키텍처 다이어그램이 assets/schema.png 경로에 있는지 확인해주세요.")

def render_configuration_section():
    """Render the configuration section in sidebar"""
    st.sidebar.markdown("### 🛠️ Configuration")
    
    # Configuration form
    with st.sidebar.form("config_form"):
        st.markdown("#### 📊 Analysis Settings")
        
        # Step 1: Ticker Symbol
        st.markdown("**1. 📈 Ticker Symbol**")
        ticker_input = st.text_input(
            "Enter ticker symbol", 
            value=st.session_state.config.get("ticker", DEFAULT_TICKER),
            help="Stock ticker symbol to analyze (e.g., SPY, TSLA, AAPL)",
            placeholder="Enter symbol...",
            max_chars=MAX_TICKER_LENGTH
        )
        
        # Sanitize and validate ticker input
        ticker = sanitize_ticker(ticker_input)
        if ticker_input and not validate_ticker(ticker):
            st.error("⚠️ Invalid ticker symbol. Use only letters and numbers (max 10 characters).")
        
        # Step 2: Analysis Date  
        st.markdown("**2. 📅 Analysis Date (KST)**")
        current_date = st.session_state.config.get("analysis_date")
        kst_today = get_kst_date()
        
        if current_date:
            try:
                default_date = datetime.datetime.strptime(current_date, "%Y-%m-%d").date()
                # 미래 날짜인 경우 오늘 날짜로 조정
                if default_date > kst_today:
                    default_date = kst_today
            except:
                default_date = kst_today
        else:
            default_date = kst_today
            
        analysis_date = st.date_input(
            "Select analysis date",
            value=default_date,
            max_value=kst_today,
            help=f"Date for the analysis (cannot be in future) - Current KST date: {kst_today.strftime('%Y-%m-%d')}"
        )
        
        # Step 3: Select Analysts
        st.markdown("**3. 👥 Analyst Team**")
        selected_analysts = []
        analyst_options = {
            "📈 Market Analyst": AnalystType.MARKET,
            "💬 Social Media Analyst": AnalystType.SOCIAL, 
            "📰 News Analyst": AnalystType.NEWS,
            "📊 Fundamentals Analyst": AnalystType.FUNDAMENTALS
        }
        
        current_analysts = st.session_state.config.get("analysts", [AnalystType.MARKET, AnalystType.SOCIAL, AnalystType.NEWS, AnalystType.FUNDAMENTALS])
        
        # Create two columns for better layout
        col1, col2 = st.columns(2)
        analyst_items = list(analyst_options.items())
        
        for i, (display_name, analyst_type) in enumerate(analyst_items):
            with col1 if i % 2 == 0 else col2:
                if st.checkbox(display_name, value=analyst_type in current_analysts, key=f"analyst_{analyst_type.value}"):
                    selected_analysts.append(analyst_type)
        
        # Step 4: Research Depth
        st.markdown("**4. 🔍 Research Depth**")
        depth_options = {
            "🌊 Shallow (1 round)": 1,
            "⛰️ Medium (3 rounds)": 3, 
            "🌋 Deep (5 rounds)": 5
        }
        current_depth = st.session_state.config.get("research_depth", DEFAULT_RESEARCH_DEPTH)
        depth_key = next((k for k, v in depth_options.items() if v == current_depth), "⛰️ Medium (3 rounds)")
        
        research_depth = st.selectbox(
            "Select research depth",
            options=list(depth_options.keys()),
            index=list(depth_options.keys()).index(depth_key),
            help="Number of debate rounds for research team"
        )
        
        # Step 5: LLM Provider
        st.write("**5. LLM Provider**")
        provider_urls = get_provider_urls()
        current_provider = st.session_state.config.get("llm_provider", "openai").title()
        if current_provider not in provider_urls:
            current_provider = "OpenAI"
            
        llm_provider = st.selectbox(
            "Select LLM provider",
            options=list(provider_urls.keys()),
            index=list(provider_urls.keys()).index(current_provider)
        )
        
        # Step 6: Thinking Agents
        st.write("**6. Thinking Agents**")
        llm_options = get_llm_options()
        provider_key = llm_provider.lower()
        
        if provider_key in llm_options:
            shallow_options = llm_options[provider_key]["shallow"]
            deep_options = llm_options[provider_key]["deep"]
            
            current_shallow = st.session_state.config.get("shallow_thinker", shallow_options[0][1])
            current_deep = st.session_state.config.get("deep_thinker", deep_options[0][1])
            
            # Ensure current values exist in options
            if not any(opt[1] == current_shallow for opt in shallow_options):
                current_shallow = shallow_options[0][1]
            if not any(opt[1] == current_deep for opt in deep_options):
                current_deep = deep_options[0][1]
            
            shallow_thinker = st.selectbox(
                "⚡ Quick-thinking LLM",
                options=[opt[1] for opt in shallow_options],
                format_func=lambda x: next(opt[0] for opt in shallow_options if opt[1] == x),
                index=[opt[1] for opt in shallow_options].index(current_shallow),
                help="Model for quick reasoning tasks"
            )
            
            deep_thinker = st.selectbox(
                "🧠 Deep-thinking LLM", 
                options=[opt[1] for opt in deep_options],
                format_func=lambda x: next(opt[0] for opt in deep_options if opt[1] == x),
                index=[opt[1] for opt in deep_options].index(current_deep),
                help="Model for complex reasoning tasks"
            )
        else:
            shallow_thinker = "gpt-4o-mini"
            deep_thinker = "gpt-4o"
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Configuration", type="primary")
        
        if submitted:
            # Validate inputs before saving
            validation_errors = []
            
            if not ticker or not validate_ticker(ticker):
                validation_errors.append("Invalid ticker symbol")
            
            if not validate_date_input(analysis_date):
                validation_errors.append("Invalid analysis date")
            
            if not selected_analysts:
                validation_errors.append("At least one analyst must be selected")
            
            if validation_errors:
                st.sidebar.error("❌ Configuration errors:\n" + "\n".join(f"• {error}" for error in validation_errors))
            else:
                # Store validated configuration
                st.session_state.config = {
                    "ticker": ticker,
                    "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                    "analysts": selected_analysts,
                    "research_depth": depth_options[research_depth],
                    "llm_provider": llm_provider.lower(),
                    "backend_url": provider_urls[llm_provider],
                    "shallow_thinker": shallow_thinker,
                    "deep_thinker": deep_thinker
                }
                st.session_state.config_set = True
                st.sidebar.success("✅ Configuration saved!")
    
    # Show current configuration status
    if st.session_state.config_set and st.session_state.config:
        st.sidebar.success("🎯 Configuration Ready")
        with st.sidebar.expander("📋 Current Settings", expanded=False):
            st.write(f"📊 **Ticker:** {st.session_state.config.get('ticker', 'N/A')}")
            config_date = st.session_state.config.get('analysis_date', 'N/A')
            if config_date != 'N/A':
                config_date = f"{config_date} (KST)"
            st.write(f"📅 **Date:** {config_date}")
            st.write(f"👥 **Analysts:** {len(st.session_state.config.get('analysts', []))}")
            st.write(f"🔍 **Depth:** {st.session_state.config.get('research_depth', 'N/A')} rounds")
            st.write(f"🤖 **Provider:** {st.session_state.config.get('llm_provider', 'N/A').title()}")
    else:
        st.sidebar.warning("⚠️ Please configure and save settings")
    
    return st.session_state.config_set and len(st.session_state.config.get("analysts", [])) > 0

def render_report_history():
    """리포트 히스토리 렌더링"""
    st.markdown("### 📚 분석 리포트 히스토리")
    
    try:
        # 현재 사용자 확인
        if not st.session_state.get('authenticated') or not st.session_state.get('username'):
            st.warning("로그인이 필요합니다.")
            return
        
        # 필터 옵션
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            start_date = st.date_input(
                "📅 시작 날짜",
                value=get_kst_date() - datetime.timedelta(days=30),  # 30일 전
                help="분석 시작 날짜 필터"
            )
        
        with col2:
            end_date = st.date_input(
                "📅 종료 날짜", 
                value=get_kst_date(),
                help="분석 종료 날짜 필터"
            )
        
        with col3:
            limit = st.selectbox("📄 표시 개수", options=[10, 25, 50, 100], index=1)
        
        # 분석 세션 조회 (사용자별 세션)
        current_username = st.session_state.username
        sessions = db_manager.get_user_analysis_sessions(current_username, limit=limit)
        
        # 날짜 필터 적용
        if start_date and end_date:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            sessions = [s for s in sessions if start_str <= s['analysis_date'][:10] <= end_str]

        if not sessions:
            st.info("📭 No analysis reports found. Start your first analysis!")
            return
        
        # 히스토리 테이블 표시
        st.markdown("#### 📋 Analysis History")
        
        # 데이터프레임으로 변환
        df_data = []
        for session in sessions:
            df_data.append({
                "Session ID": session['session_id'][:8] + "...",
                "Ticker": session['ticker'],
                "Analysis Date": session['analysis_date'][:16] if session['analysis_date'] else '',
                "Status": session['status'],
                "Decision": session['final_decision'] or '-',
                "Confidence": f"{session['confidence_score']}" if session['confidence_score'] else '-',
                "Completed": session['completed_at'][:16] if session['completed_at'] else '-'
            })
        
        df = pd.DataFrame(df_data)
        
        # 상태별 색상 코딩을 위한 스타일링
        def style_status(val):
            if val == 'completed':
                return 'background-color: #d4edda; color: #155724'
            elif val == 'running':
                return 'background-color: #fff3cd; color: #856404'
            elif val == 'failed':
                return 'background-color: #f8d7da; color: #721c24'
            return ''
        
        styled_df = df.style.applymap(style_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True)
        
        # 상세 리포트 보기
        st.markdown("#### 🔍 Detailed Report View")
        
        # 세션 선택
        session_options = {f"{s['ticker']} - {s['analysis_date'][:16]} ({s['session_id'][:8]})": s['session_id'] 
                          for s in sessions}
        
        if session_options:
            selected_display = st.selectbox(
                "📊 Select Report to View:",
                options=list(session_options.keys()),
                help="View detailed analysis report"
            )
            
            selected_session_id = session_options[selected_display]
            
            # 버튼들을 나란히 배치
            action_col1, action_col2 = st.columns([1, 1])
            
            with action_col1:
                load_report = st.button("📖 Load Report", type="primary")
            
            with action_col2:
                delete_report = st.button("🗑️ Delete Report", type="secondary", 
                                        help="⚠️ 이 작업은 되돌릴 수 없습니다!")
            
            # 삭제 상태 관리를 위한 session state 초기화
            if 'show_delete_confirm' not in st.session_state:
                st.session_state.show_delete_confirm = False
            if 'delete_target_session' not in st.session_state:
                st.session_state.delete_target_session = None
            
            # 삭제 확인 및 처리
            if delete_report:
                st.session_state.show_delete_confirm = True
                st.session_state.delete_target_session = selected_session_id
                st.session_state.delete_target_display = selected_display
                st.rerun()
            
            # 삭제 확인 창 표시
            if st.session_state.show_delete_confirm:
                st.warning("⚠️ **정말 이 리포트를 삭제하시겠습니까?**")
                st.write(f"**삭제 대상:** {st.session_state.delete_target_display}")
                
                confirm_col1, confirm_col2 = st.columns([1, 1])
                
                with confirm_col1:
                    if st.button("✅ 네, 삭제합니다", key="confirm_delete_final"):
                        try:
                            success = db_manager.delete_analysis_session(
                                st.session_state.delete_target_session, 
                                current_username
                            )
                            
                            if success:
                                st.success("✅ 리포트가 성공적으로 삭제되었습니다!")
                                st.balloons()
                                
                                # 상태 초기화
                                st.session_state.show_delete_confirm = False
                                st.session_state.delete_target_session = None
                                
                                # 바로 새로고침
                                st.rerun()
                            else:
                                st.error("❌ 리포트 삭제에 실패했습니다.")
                                st.session_state.show_delete_confirm = False
                        except Exception as e:
                            st.error(f"❌ 삭제 중 오류가 발생했습니다: {str(e)}")
                            st.session_state.show_delete_confirm = False
                
                with confirm_col2:
                    if st.button("❌ 취소", key="cancel_delete_final"):
                        st.session_state.show_delete_confirm = False
                        st.session_state.delete_target_session = None
                        st.info("🔄 삭제가 취소되었습니다.")
                        st.rerun()
            
            # 선택된 리포트 표시
            elif load_report:
                with st.spinner("Loading report..."):
                    report_data = db_manager.get_session_report(selected_session_id)
                    
                    # 세션 정보 표시
                    session_info = report_data['session_info']
                    
                    st.markdown("##### 📋 Session Information")
                    info_col1, info_col2, info_col3, info_col4 = st.columns(4)
                    
                    with info_col1:
                        st.metric("Ticker", session_info['ticker'])
                    with info_col2:
                        st.metric("Status", session_info['status'])
                    with info_col3:
                        if session_info['final_decision']:
                            st.metric("Decision", session_info['final_decision'])
                    with info_col4:
                        if session_info['confidence_score']:
                            st.metric("Confidence", f"{session_info['confidence_score']:.1%}")
                    
                    # 에이전트 실행 상태
                    if report_data['agent_executions']:
                        st.markdown("##### 🤖 Agent Execution Status")
                        agent_df_data = []
                        for agent in report_data['agent_executions']:
                            duration = ""
                            if agent['execution_time_seconds']:
                                duration = f"{agent['execution_time_seconds']:.1f}s"
                            
                            agent_df_data.append({
                                "Agent": agent['agent_name'],
                                "Status": agent['status'],
                                "Duration": duration,
                                "Error": agent['error_message'] or '-'
                            })
                        
                        agent_df = pd.DataFrame(agent_df_data)
                        st.dataframe(agent_df, use_container_width=True)
                    
                    # 리포트 섹션들
                    if report_data['report_sections']:
                        st.markdown("##### 📄 Analysis Reports")
                        
                        # 섹션별로 그룹화
                        sections_by_type = {}
                        for section in report_data['report_sections']:
                            section_type = section['section_type']
                            if section_type not in sections_by_type:
                                sections_by_type[section_type] = []
                            sections_by_type[section_type].append(section)
                        
                        # 섹션별 탭 생성
                        section_titles = {
                            "market_report": "📈 Market Analysis",
                            "sentiment_report": "🗣️ Social Sentiment", 
                            "news_report": "📰 News Analysis",
                            "fundamentals_report": "📊 Fundamentals",
                            "investment_plan": "🎯 Research Decision",
                            "trader_investment_plan": "💼 Trading Plan",
                            "final_trade_decision": "⚖️ Final Decision"
                        }
                        
                        available_sections = list(sections_by_type.keys())
                        if available_sections:
                            section_tabs = st.tabs([section_titles.get(s, s) for s in available_sections])
                            
                            for section_type, tab in zip(available_sections, section_tabs):
                                with tab:
                                    for section in sections_by_type[section_type]:
                                        st.markdown(f"**Agent:** {section['agent_name']}")
                                        st.markdown(f"**Created:** {section['created_at']}")
                                        st.markdown("---")
                                        st.markdown(section['content'])
                    
                    # 리포트 내보내기
                    st.markdown("##### ⬇️ Export Options")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # JSON 내보내기
                        json_data = db_manager.export_session_to_json(selected_session_id)
                        st.download_button(
                            label="📄 Download as JSON",
                            data=json_data,
                            file_name=f"report_{session_info['ticker']}_{selected_session_id[:8]}.json",
                            mime="application/json"
                        )
                    
                    with col2:
                        # Markdown 내보내기 (간단한 버전)
                        md_content = f"# Analysis Report - {session_info['ticker']}\n\n"
                        md_content += f"**Date:** {session_info['analysis_date']}\n"
                        md_content += f"**Decision:** {session_info['final_decision'] or 'N/A'}\n\n"
                        
                        for section in report_data['report_sections']:
                            title = section_titles.get(section['section_type'], section['section_type'])
                            md_content += f"## {title}\n\n{section['content']}\n\n"
                        
                        st.download_button(
                            label="📝 Download as Markdown",
                            data=md_content,
                            file_name=f"report_{session_info['ticker']}_{selected_session_id[:8]}.md",
                            mime="text/markdown"
                        )
        
        # 통계 정보
        if sessions:
            st.markdown("#### 📊 Statistics")
            
            # 기본 통계
            total_analyses = len(sessions)
            completed_analyses = len([s for s in sessions if s['status'] == 'completed'])
            
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            
            with stat_col1:
                st.metric("Total Analyses", total_analyses)
            
            with stat_col2:
                st.metric("Completed", completed_analyses)
            
            with stat_col3:
                completion_rate = (completed_analyses / total_analyses * 100) if total_analyses > 0 else 0
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
            
            # 결정 분포 차트
            decisions = [s['final_decision'] for s in sessions if s['final_decision']]
            if decisions:
                decision_counts = pd.Series(decisions).value_counts()
                
                fig = px.pie(
                    values=decision_counts.values,
                    names=decision_counts.index,
                    title="Decision Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error loading report history: {str(e)}")
        st.info("Make sure the database is properly initialized.")

def render_agent_status():
    """Render agent status monitoring in column format"""
    st.markdown("### 🧑‍💻 Agent Status")
    
    # Group agents by team with better icons in flow order
    teams = {
        "📈 분석팀": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
        "🔬 리서치팀": ["Bull Researcher", "Bear Researcher", "Research Manager"],  
        "💼 트레이딩팀": ["Trader"],
        "🛡️ 리스크관리": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
        "📊 포트폴리오": ["Portfolio Manager"]
    }
    
    # Create columns for teams
    cols = st.columns(len(teams))
    
    for col_idx, (team_name, agents) in enumerate(teams.items()):
        with cols[col_idx]:
            st.markdown(f"**{team_name}**")
            
            # Create a container for the flow within each column
            flow_html = ""
            
            for agent in agents:
                status = st.session_state.message_buffer['agent_status'].get(agent, "pending")
                
                if status == "pending":
                    status_class = "status-pending"
                    emoji = "⏳"
                elif status == "in_progress":
                    status_class = "status-in-progress" 
                    emoji = "🔄"
                elif status == "completed":
                    status_class = "status-completed"
                    emoji = "✅"
                else:
                    status_class = "status-error"
                    emoji = "❌"
                
                # Very short agent names for compact display
                agent_display = agent.replace(" Analyst", "").replace(" Researcher", "Res").replace(" Manager", "Mgr")
                
                flow_html += f"""
                <div style="margin-bottom: 0.3rem;">
                    <span class="agent-status {status_class}">
                        {emoji} {agent_display}
                    </span>
                </div>
                """
            
            st.markdown(flow_html, unsafe_allow_html=True)

def render_metrics():
    """Render key metrics with custom styling"""
    col1, col2, col3, col4 = st.columns(4)
    
    def custom_metric(label, value):
        return f"""
        <div style="
            background: linear-gradient(135deg, #f8faff 0%, #ffffff 100%);
            border: 1px solid rgba(66, 165, 245, 0.12);
            padding: 0.3rem 0.4rem;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(66, 165, 245, 0.05);
            margin-bottom: 0.5rem;
            min-height: 35px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="
                color: #5f6368;
                font-weight: 500;
                font-size: 0.65rem;
                margin-bottom: 0.05rem;
            ">{label}</div>
            <div style="
                color: #1a73e8;
                font-weight: 600;
                font-size: 0.7rem;
            ">{value}</div>
        </div>
        """
    
    with col1:
        st.markdown(custom_metric("🛠️ Tool Calls", st.session_state.message_buffer['tool_call_count']), unsafe_allow_html=True)
    
    with col2:
        st.markdown(custom_metric("🤖 LLM Calls", st.session_state.message_buffer['llm_call_count']), unsafe_allow_html=True)
    
    with col3:
        reports_count = sum(1 for content in st.session_state.message_buffer['report_sections'].values() if content is not None)
        st.markdown(custom_metric("📄 Generated Reports", reports_count), unsafe_allow_html=True)
    
    with col4:
        if st.session_state.message_buffer['analysis_start_time'] and st.session_state.message_buffer['analysis_end_time']:
            duration = st.session_state.message_buffer['analysis_end_time'] - st.session_state.message_buffer['analysis_start_time']
            duration_text = f"{duration:.1f}s"
        elif st.session_state.message_buffer['analysis_start_time']:
            current_duration = time.time() - st.session_state.message_buffer['analysis_start_time']
            duration_text = f"{current_duration:.1f}s"
        else:
            duration_text = "0s"
        
        st.markdown(custom_metric("⏱️ Duration", duration_text), unsafe_allow_html=True)

def render_logging_section():
    """Render collapsible logging section"""
    with st.expander("📝 Analysis Logs", expanded=False):
        
        # Create tabs for different log types
        tab1, tab2 = st.tabs(["Messages", "Tool Calls"])
        
        with tab1:
            st.subheader("Recent Messages")
            if st.session_state.message_buffer['messages']:
                log_container = st.container()
                with log_container:
                    messages_df = pd.DataFrame([
                        {
                            "Time": msg[0],
                            "Type": msg[1], 
                            "Content": msg[2][:200] + "..." if len(str(msg[2])) > 200 else str(msg[2])
                        }
                        for msg in list(st.session_state.message_buffer['messages'])[-MAX_LOG_DISPLAY_SIZE:]
                    ])
                    st.dataframe(messages_df, use_container_width=True, hide_index=True)
            else:
                st.info("No messages yet. Start analysis to see logs.")
        
        with tab2:
            st.subheader("Tool Calls")
            if st.session_state.message_buffer['tool_calls']:
                tool_calls_df = pd.DataFrame([
                    {
                        "Time": call[0],
                        "Tool": call[1],
                        "Arguments": str(call[2])[:100] + "..." if len(str(call[2])) > 100 else str(call[2])
                    }
                    for call in list(st.session_state.message_buffer['tool_calls'])[-MAX_LOG_DISPLAY_SIZE:]
                ])
                st.dataframe(tool_calls_df, use_container_width=True, hide_index=True)
            else:
                st.info("No tool calls yet. Start analysis to see tool usage.")

def render_reports_section():
    """Render reports section with export functionality"""
    st.subheader("📑 Analysis Reports")
    
    report_sections = st.session_state.message_buffer['report_sections']
    
    if any(content for content in report_sections.values()):
        
        # Create tabs for different reports
        tabs = []
        tab_names = []
        
        section_titles = {
            "market_report": "Market Analysis",
            "sentiment_report": "Social Sentiment", 
            "news_report": "News Analysis",
            "fundamentals_report": "Fundamentals Analysis",
            "investment_plan": "Research Team Decision",
            "trader_investment_plan": "Trading Team Plan",
            "final_trade_decision": "Portfolio Management Decision"
        }
        
        for section, content in report_sections.items():
            if content:
                tab_names.append(section_titles.get(section, section.title()))
                tabs.append(section)
        
        if tabs:
            selected_tabs = st.tabs(tab_names)
            
            for tab, section in zip(selected_tabs, tabs):
                with tab:
                    content = report_sections[section]
                    st.markdown(content)
        
        # Only show export buttons if analysis is not running
        if not st.session_state.analysis_running:
            st.subheader("⬇️ Export Reports")
            
            # Individual report downloads
            for section, content in report_sections.items():
                if content:
                    title = section_titles.get(section, section.title())
                    report_filename = f"{section}_{st.session_state.config['ticker']}_{st.session_state.config['analysis_date']}.md"
                    st.download_button(
                        label=f"📄 Download {title}",
                        data=content,
                        file_name=report_filename,
                        mime="text/markdown",
                        key=f"download_{section}"
                    )
            
            # Complete report download
            complete_report = f"# Complete Analysis Report - {st.session_state.config['ticker']}\n"
            complete_report += f"**Analysis Date:** {st.session_state.config['analysis_date']}\n\n"
            
            for section, content in report_sections.items():
                if content:
                    title = section_titles.get(section, section.title())
                    complete_report += f"## {title}\n\n{content}\n\n"
            
            complete_filename = f"complete_report_{st.session_state.config['ticker']}_{st.session_state.config['analysis_date']}.md"
            st.download_button(
                label="📋 Download Complete Report",
                data=complete_report,
                file_name=complete_filename,
                mime="text/markdown",
                key="download_complete"
            )
        else:
            st.info("📥 Export options will be available after analysis completes")
    else:
        st.info("No reports generated yet. Start analysis to see reports.")

def add_message(msg_type: str, content: str):
    """Add message to buffer"""
    timestamp = get_kst_naive_now().strftime("%H:%M:%S KST")
    
    # Sanitize content for security
    safe_content = sanitize_log_message(str(content))
    safe_msg_type = sanitize_log_message(str(msg_type))
    
    st.session_state.message_buffer['messages'].append((timestamp, safe_msg_type, safe_content))
    if msg_type == "Reasoning":
        st.session_state.message_buffer['llm_call_count'] += 1
    
    # Log the message with sanitized content
    log_content = safe_content[:200] + "..." if len(safe_content) > 200 else safe_content
    logger.info(f"[{safe_msg_type}] {log_content}")

def add_tool_call(tool_name: str, args: dict):
    """Add tool call to buffer"""
    timestamp = get_kst_naive_now().strftime("%H:%M:%S KST")
    
    # Sanitize inputs
    safe_tool_name = sanitize_log_message(str(tool_name))
    safe_args = {sanitize_log_message(str(k)): sanitize_log_message(str(v)) for k, v in (args or {}).items()}
    
    st.session_state.message_buffer['tool_calls'].append((timestamp, safe_tool_name, safe_args))
    st.session_state.message_buffer['tool_call_count'] += 1
    
    # Log the tool call with sanitized content
    args_str = str(safe_args)[:100] + "..." if len(str(safe_args)) > 100 else str(safe_args)
    logger.info(f"[TOOL] {safe_tool_name} called with args: {args_str}")

def update_agent_status(agent: str, status: str):
    """Update agent status"""
    if agent in st.session_state.message_buffer['agent_status']:
        st.session_state.message_buffer['agent_status'][agent] = status
        st.session_state.message_buffer['current_agent'] = agent
        
        # Log agent status change
        logger.info(f"[AGENT] {agent} status changed to: {status}")

def update_report_section(section_name: str, content: str):
    """Update report section"""
    if section_name in st.session_state.message_buffer['report_sections']:
        st.session_state.message_buffer['report_sections'][section_name] = content
        
        # Log report section update
        logger.info(f"[REPORT] {section_name} report updated ({len(content)} chars)")

def extract_content_string(content):
    """Extract string content from various message formats"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
                elif item.get('type') == 'tool_use':
                    text_parts.append(f"[Tool: {item.get('name', 'unknown')}]")
            else:
                text_parts.append(str(item))
        return ' '.join(text_parts)
    else:
        return str(content)

def run_analysis():
    """Run analysis directly without threading"""
    try:
        config = st.session_state.config.copy()
        
        # Create config with selected research depth
        full_config = DEFAULT_CONFIG.copy()
        full_config["max_debate_rounds"] = config["research_depth"]
        full_config["max_risk_discuss_rounds"] = config["research_depth"]
        full_config["quick_think_llm"] = config["shallow_thinker"]
        full_config["deep_think_llm"] = config["deep_thinker"]
        full_config["backend_url"] = config["backend_url"]
        full_config["llm_provider"] = config["llm_provider"]
        
        # Initialize the graph and store in session state
        graph = TradingAgentsGraph(
            [analyst.value for analyst in config["analysts"]], 
            config=full_config, 
            debug=True
        )
        st.session_state.graph = graph
        
        # Reset message buffer
        st.session_state.message_buffer['analysis_start_time'] = time.time()
        
        # Reset agent statuses
        for agent in st.session_state.message_buffer['agent_status']:
            update_agent_status(agent, "pending")
        
        # Reset report sections
        for section in st.session_state.message_buffer['report_sections']:
            st.session_state.message_buffer['report_sections'][section] = None
        
        # Add initial messages
        add_message("System", f"Selected ticker: {config['ticker']}")
        add_message("System", f"Analysis date: {config['analysis_date']}")
        add_message("System", f"Selected analysts: {', '.join(analyst.value for analyst in config['analysts'])}")
        
        # Update first analyst to in_progress
        first_analyst = f"{config['analysts'][0].value.capitalize()} Analyst"
        update_agent_status(first_analyst, "in_progress")
        
        # Initialize state and get graph args
        init_agent_state = graph.propagator.create_initial_state(
            config["ticker"], config["analysis_date"]
        )
        args = graph.propagator.get_graph_args()
        
        # Stream the analysis
        trace = []
        
        for chunk in graph.graph.stream(init_agent_state, **args):
            if len(chunk.get("messages", [])) > 0:
                # Get the last message from the chunk
                last_message = chunk["messages"][-1]
                
                # Extract message content and type
                if hasattr(last_message, "content"):
                    content = extract_content_string(last_message.content)
                    msg_type = "Reasoning"
                else:
                    content = str(last_message)
                    msg_type = "System"
                
                # Add message to buffer
                add_message(msg_type, content)
                
                # If it's a tool call, add it to tool calls
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        if isinstance(tool_call, dict):
                            add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            add_tool_call(tool_call.name, tool_call.args)
                
                # Update reports and agent status based on chunk content
                # Analyst Team Reports
                if "market_report" in chunk and chunk["market_report"]:
                    update_report_section("market_report", chunk["market_report"])
                    update_agent_status("Market Analyst", "completed")
                
                if "sentiment_report" in chunk and chunk["sentiment_report"]:
                    update_report_section("sentiment_report", chunk["sentiment_report"])
                    update_agent_status("Social Analyst", "completed")
                
                if "news_report" in chunk and chunk["news_report"]:
                    update_report_section("news_report", chunk["news_report"])
                    update_agent_status("News Analyst", "completed")
                
                if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
                    update_report_section("fundamentals_report", chunk["fundamentals_report"])
                    update_agent_status("Fundamentals Analyst", "completed")
                
                # Research Team
                if "investment_debate_state" in chunk and chunk["investment_debate_state"]:
                    debate_state = chunk["investment_debate_state"]
                    
                    if "judge_decision" in debate_state and debate_state["judge_decision"]:
                        update_report_section("investment_plan", debate_state["judge_decision"])
                        update_agent_status("Bull Researcher", "completed")
                        update_agent_status("Bear Researcher", "completed")
                        update_agent_status("Research Manager", "completed")
                
                # Trading Team
                if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
                    update_report_section("trader_investment_plan", chunk["trader_investment_plan"])
                    update_agent_status("Trader", "completed")
                
                # Risk Management Team
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk_state = chunk["risk_debate_state"]
                    
                    if "judge_decision" in risk_state and risk_state["judge_decision"]:
                        update_report_section("final_trade_decision", risk_state["judge_decision"])
                        update_agent_status("Risky Analyst", "completed")
                        update_agent_status("Safe Analyst", "completed")
                        update_agent_status("Neutral Analyst", "completed")
                        update_agent_status("Portfolio Manager", "completed")
                
                # Force UI update after each chunk
                st.rerun()
            
            trace.append(chunk)
        
        # Get final state
        final_state = trace[-1] if trace else {}
        st.session_state.message_buffer['final_state'] = final_state
        st.session_state.message_buffer['analysis_end_time'] = time.time()
        
        # Update all agent statuses to completed
        for agent in st.session_state.message_buffer['agent_status']:
            update_agent_status(agent, "completed")
        
        add_message("Analysis", f"Completed analysis for {config['analysis_date']}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        add_message("Error", f"Analysis failed: {str(e)}")
        # Update all agent statuses to error
        for agent in st.session_state.message_buffer['agent_status']:
            update_agent_status(agent, "error")
        return False
    finally:
        st.session_state.analysis_running = False

def get_session_info():
    """Get current session information"""
    if not st.session_state.authenticated or st.session_state.login_time is None:
        return None
    
    current_time = get_kst_naive_now()
    login_time = st.session_state.login_time
    
    # KST 시간으로 처리
    if current_time.tzinfo is not None:
        current_time = current_time.replace(tzinfo=None)
    if login_time.tzinfo is not None:
        login_time = login_time.replace(tzinfo=None)
    
    elapsed_time = (current_time - login_time).total_seconds()
    remaining_time = st.session_state.session_duration - elapsed_time
    
    return {
        'elapsed': elapsed_time,
        'remaining': max(0, remaining_time),
        'total': st.session_state.session_duration
    }

def main() -> None:
    """Main Streamlit application with enhanced security and error handling"""
    try:
        # Environment validation first
        if not validate_environment():
            st.error("❌ Environment validation failed. Please check configuration.")
            st.stop()
        
        # Initialize authentication first
        init_auth_session_state()
        
        # Try to restore session from database
        if not st.session_state.authenticated:
            load_session()
        
        # Check if session expired
        if is_session_expired():
            clear_session()
            st.error("🔒 Your session has expired. Please log in again.")
            render_login_page()
            return
        
        # Check authentication
        if not st.session_state.authenticated:
            render_login_page()
            return
            
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.error(f"❌ Application initialization failed: {error_msg}")
        logger.error(f"[MAIN] Initialization error: {error_msg}")
        st.stop()
    
    # Initialize main session state
    init_session_state()
    
    # Add session info and logout button in sidebar
    with st.sidebar:
        # Session information
        session_info = get_session_info()
        if session_info:
            st.markdown("---")
            st.markdown("### 🔐 Session Status")
            
            # Show current user
            current_user = st.session_state.get('username', 'Unknown')
            st.info(f"👤 Logged in as: **{current_user}**")
            
            remaining_minutes = int(session_info['remaining'] / 60)
            remaining_seconds = int(session_info['remaining'] % 60)
            
            if session_info['remaining'] > 300:  # More than 5 minutes
                st.success(f"⏱️ Time remaining: {remaining_minutes}m {remaining_seconds}s (KST)")
            elif session_info['remaining'] > 60:  # 1-5 minutes
                st.warning(f"⚠️ Time remaining: {remaining_minutes}m {remaining_seconds}s (KST)")
            else:  # Less than 1 minute
                st.error(f"🚨 Time remaining: {remaining_seconds}s (KST)")
            
            # Progress bar for session time
            progress = 1 - (session_info['remaining'] / session_info['total'])
            st.progress(progress)
        
        st.markdown("---")
        logout_label = f"🚪 Logout ({current_user})" if session_info else "🚪 Logout"
        if st.button(logout_label, type="secondary"):
            logged_out_user = st.session_state.get('username', 'Unknown')
            
            # Clear session file BEFORE clearing username
            clear_session()
            
            # Stop any running analysis
            if st.session_state.get('analysis_running', False):
                st.session_state.analysis_running = False
                st.session_state.stream_processing = False
                if hasattr(st.session_state, 'analysis_stream'):
                    delattr(st.session_state, 'analysis_stream')
                if hasattr(st.session_state, 'graph'):
                    delattr(st.session_state, 'graph')
            
            # Clear all session state variables
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.session_id = None
            st.session_state.login_attempts = 0
            st.session_state.login_time = None
            
            # Clear analysis-related session state
            keys_to_clear = [
                'analysis_running', 'stream_processing', 'analysis_stream', 
                'graph', 'init_agent_state', 'graph_args', 'trace',
                'message_buffer', 'config', 'config_set'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    delattr(st.session_state, key)
            
            # Re-initialize auth session state for clean start
            init_auth_session_state()
            
            logger.info(f"[AUTH] User {logged_out_user} logged out manually - all session data cleared")
            st.success(f"✅ {logged_out_user} logged out successfully!")
            time.sleep(1)  # Brief pause to show message
            st.rerun()
    
    # Welcome header
    render_welcome_header()
    # Configuration section (sidebar)
    config_valid = render_configuration_section()
    
    # Mobile-optimized tabs CSS
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        overflow-x: auto;
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 12px;
        font-size: 14px;
        min-width: fit-content;
        white-space: nowrap;
    }
    @media (max-width: 640px) {
        .stTabs [data-baseweb="tab"] {
            font-size: 12px;
            padding: 0px 8px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["🧠 AI분석", "📚 히스토리", "📈 주식분석", "📊 거시경제"])
    
    with tab1:
        # Main content area for AI Analysis
        col1, col2 = st.columns([2, 1])
    
    with col1:
        # Start Analysis Button
        st.subheader("🚦 Analysis Control")
        
        if not st.session_state.analysis_running:
            if st.button("▶️ Start Analysis", disabled=not config_valid, type="primary"):
                if config_valid:
                    st.session_state.analysis_running = True
                    st.session_state.stream_processing = False  # Initialize stream processing flag
                    # Initialize analysis state
                    config = st.session_state.config.copy()
                    
                    # Log analysis start
                    logger.info(f"[ANALYSIS] Starting analysis for {config['ticker']} on {config['analysis_date']}")
                    
                    # Create config with selected research depth
                    full_config = DEFAULT_CONFIG.copy()
                    full_config["max_debate_rounds"] = config["research_depth"]
                    full_config["max_risk_discuss_rounds"] = config["research_depth"]
                    full_config["quick_think_llm"] = config["shallow_thinker"]
                    full_config["deep_think_llm"] = config["deep_thinker"]
                    full_config["backend_url"] = config["backend_url"]
                    full_config["llm_provider"] = config["llm_provider"]
                    
                    # Generate unique collection names for each run
                    import uuid
                    session_id = str(uuid.uuid4())[:8]  # Short unique ID
                    
                    # Add unique session ID to config for collection naming
                    full_config["session_id"] = session_id
                    
                    # Initialize the graph with unique collection names
                    try:
                        st.session_state.graph = TradingAgentsGraph(
                            [analyst.value for analyst in config["analysts"]], 
                            config=full_config, 
                            debug=True
                        )
                        logger.info(f"[ANALYSIS] Graph initialized with session ID: {session_id}")
                    except Exception as e:
                        st.error(f"❌ Failed to initialize analysis graph: {str(e)}")
                        logger.error(f"[ANALYSIS] Graph initialization failed: {str(e)}")
                        return
                    
                    # Reset message buffer
                    st.session_state.message_buffer['analysis_start_time'] = time.time()
                    
                    # Reset agent statuses
                    for agent in st.session_state.message_buffer['agent_status']:
                        update_agent_status(agent, "pending")
                    
                    # Reset report sections
                    for section in st.session_state.message_buffer['report_sections']:
                        st.session_state.message_buffer['report_sections'][section] = None
                    
                    # Add initial messages
                    add_message("System", f"Selected ticker: {config['ticker']}")
                    add_message("System", f"Analysis date: {config['analysis_date']}")
                    add_message("System", f"Selected analysts: {', '.join(analyst.value for analyst in config['analysts'])}")
                    
                    # Initialize state and get graph args
                    st.session_state.init_agent_state = st.session_state.graph.propagator.create_initial_state(
                        config["ticker"], config["analysis_date"]
                    )
                    st.session_state.graph_args = st.session_state.graph.propagator.get_graph_args()
                    st.session_state.analysis_stream = st.session_state.graph.graph.stream(st.session_state.init_agent_state, **st.session_state.graph_args)
                    st.session_state.trace = []
                    
                    # Update first analyst to in_progress
                    first_analyst = f"{config['analysts'][0].value.capitalize()} Analyst"
                    update_agent_status(first_analyst, "in_progress")
                    
                    st.rerun()
                else:
                    st.error("Please select at least one analyst before starting analysis.")
        else:
            st.info("Analysis is currently running...")
            if st.button("⏹️ Stop Analysis", type="secondary"):
                st.session_state.analysis_running = False
                st.session_state.stream_processing = False  # Reset stream processing flag
                st.rerun()
        
        # Metrics
        render_metrics()
        
        # Configuration Summary
        st.subheader("⚙️ Current Configuration")
        if st.session_state.config:
            config_date = st.session_state.config.get("analysis_date", "N/A")
            if config_date != "N/A":
                config_date = f"{config_date} (KST)"
            
            # Create compact configuration display with custom metrics
            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            
            def custom_metric(label, value):
                return f"""
                <div style="
                    background: linear-gradient(135deg, #f8faff 0%, #ffffff 100%);
                    border: 1px solid rgba(66, 165, 245, 0.12);
                    padding: 0.3rem 0.4rem;
                    border-radius: 10px;
                    box-shadow: 0 1px 3px rgba(66, 165, 245, 0.05);
                    margin-bottom: 0.5rem;
                    min-height: 35px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                ">
                    <div style="
                        color: #5f6368;
                        font-weight: 500;
                        font-size: 0.65rem;
                        margin-bottom: 0.05rem;
                    ">{label}</div>
                    <div style="
                        color: #1a73e8;
                        font-weight: 600;
                        font-size: 0.7rem;
                    ">{value}</div>
                </div>
                """
            
            with col_cfg1:
                st.markdown(custom_metric("📊 Ticker", st.session_state.config.get("ticker", "N/A")), unsafe_allow_html=True)
                st.markdown(custom_metric("👥 Analysts", len(st.session_state.config.get("analysts", []))), unsafe_allow_html=True)
            with col_cfg2:
                st.markdown(custom_metric("📅 Date", config_date), unsafe_allow_html=True)
                st.markdown(custom_metric("🔍 Research Depth", f"{st.session_state.config.get('research_depth', 'N/A')} rounds"), unsafe_allow_html=True)
            with col_cfg3:
                st.markdown(custom_metric("🤖 Provider", st.session_state.config.get("llm_provider", "N/A").title()), unsafe_allow_html=True)
        else:
            st.info("No configuration set yet. Please configure in the sidebar.")
        
        # Agent Status
        render_agent_status()
        
        # Reports Section
        render_reports_section()
    
    with col2:
        # Logging Section
        render_logging_section()
    
    with tab2:
        # Report History Tab
        render_report_history()
        
    
    with tab3:
        # Market Agent Stock Analysis Tab
        create_market_agent_dashboard()
    
    with tab4:
        # Financial Indicators Visualization Tab
        create_financial_indicators_charts()
        
    
    # Process analysis stream if running
    if st.session_state.analysis_running and hasattr(st.session_state, 'analysis_stream'):
        # Prevent re-entrant generator calls
        if 'stream_processing' not in st.session_state:
            st.session_state.stream_processing = False
        
        if st.session_state.stream_processing:
            return  # Skip if already processing
        
        st.session_state.stream_processing = True
        try:
            chunk = next(st.session_state.analysis_stream)
            
            if len(chunk.get("messages", [])) > 0:
                # Get the last message from the chunk
                last_message = chunk["messages"][-1]
                
                # Extract message content and type
                if hasattr(last_message, "content"):
                    content = extract_content_string(last_message.content)
                    msg_type = "Reasoning"
                else:
                    content = str(last_message)
                    msg_type = "System"
                
                # Add message to buffer
                add_message(msg_type, content)
                
                # If it's a tool call, add it to tool calls
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        if isinstance(tool_call, dict):
                            add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            add_tool_call(tool_call.name, tool_call.args)
                
                # Update reports and agent status based on chunk content
                # Analyst Team Reports
                if "market_report" in chunk and chunk["market_report"]:
                    update_report_section("market_report", chunk["market_report"])
                    update_agent_status("Market Analyst", "completed")
                
                if "sentiment_report" in chunk and chunk["sentiment_report"]:
                    update_report_section("sentiment_report", chunk["sentiment_report"])
                    update_agent_status("Social Analyst", "completed")
                
                if "news_report" in chunk and chunk["news_report"]:
                    update_report_section("news_report", chunk["news_report"])
                    update_agent_status("News Analyst", "completed")
                
                if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
                    update_report_section("fundamentals_report", chunk["fundamentals_report"])
                    update_agent_status("Fundamentals Analyst", "completed")
                
                # Research Team
                if "investment_debate_state" in chunk and chunk["investment_debate_state"]:
                    debate_state = chunk["investment_debate_state"]
                    
                    if "judge_decision" in debate_state and debate_state["judge_decision"]:
                        update_report_section("investment_plan", debate_state["judge_decision"])
                        update_agent_status("Bull Researcher", "completed")
                        update_agent_status("Bear Researcher", "completed")
                        update_agent_status("Research Manager", "completed")
                
                # Trading Team
                if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
                    update_report_section("trader_investment_plan", chunk["trader_investment_plan"])
                    update_agent_status("Trader", "completed")
                
                # Risk Management Team
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk_state = chunk["risk_debate_state"]
                    
                    if "judge_decision" in risk_state and risk_state["judge_decision"]:
                        update_report_section("final_trade_decision", risk_state["judge_decision"])
                        update_agent_status("Risky Analyst", "completed")
                        update_agent_status("Safe Analyst", "completed")
                        update_agent_status("Neutral Analyst", "completed")
                        update_agent_status("Portfolio Manager", "completed")
            
            st.session_state.trace.append(chunk)
            
            # Continue processing
            time.sleep(0.1)  # Small delay to prevent overwhelming
            st.session_state.stream_processing = False  # Reset flag before rerun
            st.rerun()
            
        except StopIteration:
            # Analysis completed
            st.session_state.analysis_running = False
            st.session_state.stream_processing = False  # Reset flag
            st.session_state.message_buffer['analysis_end_time'] = time.time()
            
            # Calculate duration
            duration = st.session_state.message_buffer['analysis_end_time'] - st.session_state.message_buffer['analysis_start_time']
            
            # Update all agent statuses to completed
            for agent in st.session_state.message_buffer['agent_status']:
                update_agent_status(agent, "completed")
            
            config = st.session_state.config
            add_message("Analysis", f"Completed analysis for {config['analysis_date']}")
            
            # Get final state
            if st.session_state.trace:
                st.session_state.message_buffer['final_state'] = st.session_state.trace[-1]
            
            # Save analysis to database
            try:
                # Extract final decision using graph's process_signal method
                final_decision = None
                confidence_score = None
                
                final_trade_decision = st.session_state.message_buffer['report_sections'].get('final_trade_decision')
                if final_trade_decision and hasattr(st.session_state, 'graph') and st.session_state.graph:
                    try:
                        # Use graph's process_signal method to extract clean decision
                        final_decision = st.session_state.graph.process_signal(final_trade_decision)
                        
                        # Use graph's extract_confidence method to extract confidence score
                        confidence_score = st.session_state.graph.extract_confidence_score(final_trade_decision)
                    except Exception as e:
                        error_msg = sanitize_log_message(str(e))
                        logger.warning(f"[ANALYSIS] Failed to process signal using graph method: {error_msg}")
                        # Fallback to None if process_signal fails
                        final_decision = "-"
                        confidence_score = "-"
                
                # Create analysis session in DB
                session_id = db_manager.create_analysis_session(
                    username=st.session_state.username,
                    ticker=config['ticker'],
                    analysis_date=config['analysis_date'],
                    config=config
                )
                
                # Save report sections
                for section_type, content in st.session_state.message_buffer['report_sections'].items():
                    if content:
                        db_manager.save_report_section(
                            session_id=session_id,
                            section_type=section_type,
                            agent_name=f"{section_type.replace('_', ' ').title()}",
                            content=content
                        )
                
                # Update session with final results
                db_manager.complete_analysis_session(
                    session_id=session_id,
                    final_decision=final_decision,
                    confidence_score=confidence_score,
                    execution_time_seconds=duration
                )
                
                logger.info(f"[DATABASE] Analysis saved to DB with session_id: {session_id}")
                
            except Exception as db_error:
                logger.error(f"[DATABASE] Failed to save analysis to DB: {db_error}")
                st.warning(f"⚠️ 분석 완료되었으나 DB 저장 실패: {db_error}")
            
            # Log analysis completion
            logger.info(f"[ANALYSIS] Analysis completed for {config['ticker']} in {duration:.2f} seconds")
            logger.info(f"[ANALYSIS] Final stats - LLM calls: {st.session_state.message_buffer['llm_call_count']}, Tool calls: {st.session_state.message_buffer['tool_call_count']}")
            
            st.success("✅ Analysis completed successfully!")
            st.rerun()
            
        except Exception as e:
            st.session_state.analysis_running = False
            st.session_state.stream_processing = False  # Reset flag on error
            error_msg = f"Analysis failed: {str(e)}"
            st.error(f"❌ {error_msg}")
            add_message("Error", error_msg)
            
            # Log the error
            logger.error(f"[ANALYSIS] {error_msg}", exc_info=True)
            
            # Update all agent statuses to error
            for agent in st.session_state.message_buffer['agent_status']:
                update_agent_status(agent, "error")
            st.rerun()
    
    # Auto-refresh when analysis is running
    elif st.session_state.analysis_running:
        time.sleep(0.5)
        st.rerun()
    
    # 자동 새로고침 최소화 - 사용자 경험 개선
    # 세션 만료는 사용자 액션 시에만 체크하도록 변경

if __name__ == "__main__":
    main()