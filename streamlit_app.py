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
from typing import Dict, List, Optional, Tuple, Any, Union
from db_manager import DatabaseManager

# Security and Configuration Constants
SESSION_DURATION_SECONDS = 3600  # 1 hour
MAX_LOGIN_ATTEMPTS = 5
BLOCK_DURATION_MINUTES = 15
CACHE_TTL_SECONDS = 300  # 5 minutes
MAX_MESSAGE_BUFFER_SIZE = 200
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

# Financial Indicators Functions
@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_high_yield_spread() -> Optional[pd.DataFrame]:
    """미국 하이일드 스프레드 인덱스 데이터 가져오기 with improved error handling"""
    try:
        with st.spinner("Loading high yield spread data..."):
            # Download with timeout and progress tracking
            hyg_data = yf.download('HYG', period='5y', interval='1d', timeout=10)
            treasury_data = yf.download('^TNX', period='5y', interval='1d', timeout=10)
        
        # Validate data
        if hyg_data.empty or treasury_data.empty:
            st.warning("Failed to fetch high yield spread data - market may be closed")
            return None
        
        # Check for required columns
        if 'Close' not in hyg_data.columns or 'Close' not in treasury_data.columns:
            st.error("Missing price data in high yield spread indicators")
            return None
        
        # Close 컬럼만 선택하고 인덱스를 reset
        hyg_df = hyg_data[['Close']].reset_index()
        treasury_df = treasury_data[['Close']].reset_index()
        
        # 컬럼명 변경
        hyg_df.columns = ['Date', 'HYG_Price'] 
        treasury_df.columns = ['Date', 'Treasury_10Y']
        
        # 날짜로 병합
        spread_data = pd.merge(hyg_df, treasury_df, on='Date', how='inner')
        
        # Validate merged data
        if spread_data.empty:
            st.warning("No overlapping data for high yield spread calculation")
            return None
        
        # Remove invalid values
        spread_data = spread_data.dropna()
        
        # Basic sanity checks
        if len(spread_data) < 10:
            st.warning("Insufficient data points for high yield spread analysis")
            return None
        
        return spread_data
        
    except TimeoutError:
        st.error("Timeout loading high yield spread data")
        return None
    except ConnectionError:
        st.error("Network connection error loading high yield spread data")
        return None
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.error(f"하이일드 스프레드 데이터 로딩 실패: {error_msg}")
        logger.error(f"[INDICATORS] High yield spread loading failed: {error_msg}")
        return None

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
def get_fred_data():
    """FRED 데이터 가져오기 (API 키 없이 공개 데이터 사용)"""
    try:
        # Case-Shiller Home Price Index 대용으로 부동산 ETF 사용
        real_estate_data = yf.download('VNQ', period='5y', interval='1d')
        
        # Close 컬럼만 선택하고 인덱스를 reset
        fred_df = real_estate_data[['Close']].reset_index()
        fred_df.columns = ['Date', 'Real_Estate_Index']
        
        return fred_df.dropna()
    except Exception as e:
        st.error(f"FRED 부동산 지수 데이터 로딩 실패: {e}")
        return None

@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_additional_indicators():
    """추가 필수 지표들 로드"""
    indicators = {}
    
    # 달러 인덱스
    try:
        dxy_data = yf.download('DX-Y.NYB', period='5y', interval='1d')
        if not dxy_data.empty:
            dxy_df = dxy_data[['Close']].reset_index()
            dxy_df.columns = ['Date', 'DXY']
            indicators['dxy'] = dxy_df
    except:
        indicators['dxy'] = None
    
    # 수익률 곡선 (10Y-2Y)
    try:
        ten_year = yf.download('^TNX', period='5y', interval='1d')
        two_year = yf.download('^IRX', period='5y', interval='1d')
        if not ten_year.empty and not two_year.empty:
            ten_y_df = ten_year[['Close']].reset_index()
            two_y_df = two_year[['Close']].reset_index()
            ten_y_df.columns = ['Date', '10Y']
            two_y_df.columns = ['Date', '2Y']
            yield_spread = pd.merge(ten_y_df, two_y_df, on='Date', how='inner')
            yield_spread['Yield_Spread'] = yield_spread['10Y'] - (yield_spread['2Y'] / 4)
            indicators['yield_curve'] = yield_spread
    except:
        indicators['yield_curve'] = None
    
    # 금 가격
    try:
        gold_data = yf.download('GC=F', period='5y', interval='1d')
        if not gold_data.empty:
            gold_df = gold_data[['Close']].reset_index()
            gold_df.columns = ['Date', 'Gold']
            indicators['gold'] = gold_df
    except:
        indicators['gold'] = None
    
    # 원유 가격
    try:
        oil_data = yf.download('CL=F', period='5y', interval='1d')
        if not oil_data.empty:
            oil_df = oil_data[['Close']].reset_index()
            oil_df.columns = ['Date', 'Oil']
            indicators['oil'] = oil_df
    except:
        indicators['oil'] = None
    
    return indicators

def create_financial_indicators_charts():
    """통합 금융 지표 대시보드 - 모든 지표 + 상관관계 분석"""
    st.header("📊 거시 경제 대시보드")
    
    # 모든 데이터 로드
    spread_data = get_high_yield_spread()
    fg_data = get_fear_greed_index()
    pc_data = get_put_call_ratio()
    fred_data = get_fred_data()
    additional_data = get_additional_indicators()
    
    # 데이터 로딩 상태 간단히 표시
    with st.expander("🔍 데이터 로딩 상태", expanded=False):
        indicators_status = [
            ("하이일드 스프레드", spread_data),
            ("공포탐욕지수", fg_data),
            ("풋콜레이쇼", pc_data),
            ("부동산지수", fred_data),
            ("달러인덱스", additional_data.get('dxy')),
            ("수익률곡선", additional_data.get('yield_curve')),
            ("금가격", additional_data.get('gold')),
            ("원유가격", additional_data.get('oil'))
        ]
        
        for name, data in indicators_status:
            status = "✅ 성공" if data is not None and len(data) > 0 else "❌ 실패"
            st.write(f"- {name}: {status}")
    
    # 2x4 그리드로 지표들 배치
    col1, col2 = st.columns(2)
    
    with col1:
        # 하이일드 스프레드
        current_hyg = spread_data['HYG_Price'].iloc[-1] if spread_data is not None and len(spread_data) > 0 else 0
        current_treasury = spread_data['Treasury_10Y'].iloc[-1] if spread_data is not None and len(spread_data) > 0 else 0
        current_spread = current_hyg / current_treasury if current_treasury != 0 else 0
        
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #FF6B6B, #4ECDC4); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
            <span style="color: white; font-weight: bold; font-size: 14px;">🏢 하이일드 스프레드</span>
            <span style="color: white; font-size: 12px; margin-left: 10px;">HYG ${current_hyg:.2f} | 10Y {current_treasury:.2f}% | 비율 {current_spread:.2f}</span>
        </div>
        """, unsafe_allow_html=True)
        
        if spread_data is not None and len(spread_data) > 0:
            spread_normalized = spread_data.copy()
            spread_normalized.set_index('Date', inplace=True)
            
            hyg_min, hyg_max = spread_normalized['HYG_Price'].min(), spread_normalized['HYG_Price'].max()
            treasury_min, treasury_max = spread_normalized['Treasury_10Y'].min(), spread_normalized['Treasury_10Y'].max()
            
            spread_normalized['HYG_Normalized'] = ((spread_normalized['HYG_Price'] - hyg_min) / (hyg_max - hyg_min)) * 100
            spread_normalized['Treasury_Normalized'] = ((spread_normalized['Treasury_10Y'] - treasury_min) / (treasury_max - treasury_min)) * 100
            
            comparison_chart = spread_normalized[['HYG_Normalized', 'Treasury_Normalized']]
            comparison_chart.columns = ['HYG ETF', '10Y Treasury']
            st.line_chart(comparison_chart, height=200)
            
            spread_normalized['Spread'] = spread_normalized['HYG_Price'] / spread_normalized['Treasury_10Y']
            spread_chart = spread_normalized[['Spread']]
            st.line_chart(spread_chart, color="#9B59B6", height=150)
                
            st.caption("💡 스프레드 상승 = 리스크 오프 신호, 하이일드 채권 vs 국채 상대 매력도")
        else:
            st.warning("하이일드 스프레드 데이터 없음")
        
        # 풋콜레이쇼
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
        else:
            st.warning("풋콜레이쇼 데이터 없음")
        
        # 달러 인덱스
        dxy_data = additional_data.get('dxy')
        if dxy_data is not None and len(dxy_data) > 0:
            current_dxy = dxy_data['DXY'].iloc[-1]
            prev_dxy = dxy_data['DXY'].iloc[-30] if len(dxy_data) > 30 else dxy_data['DXY'].iloc[0]
            dxy_change = ((current_dxy - prev_dxy) / prev_dxy) * 100
            
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #FFD700, #FFA000); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                <span style="color: white; font-weight: bold; font-size: 14px;">💵 달러 인덱스</span>
                <span style="color: white; font-size: 12px; margin-left: 10px;">{current_dxy:.2f} | 30일 {dxy_change:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            dxy_chart = dxy_data.set_index('Date')[['DXY']]
            st.line_chart(dxy_chart, color="#FFD700", height=200)
            st.caption("💡 달러 강세 → 신흥국/금 약세, 달러 약세 → 원자재/신흥국 강세")
        else:
            st.warning("달러 인덱스 데이터 없음")
        
        # 금 가격
        gold_data = additional_data.get('gold')
        if gold_data is not None and len(gold_data) > 0:
            current_gold = gold_data['Gold'].iloc[-1]
            prev_gold = gold_data['Gold'].iloc[-30] if len(gold_data) > 30 else gold_data['Gold'].iloc[0]
            gold_change = ((current_gold - prev_gold) / prev_gold) * 100
            
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #FFD700, #FF6B35); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                <span style="color: white; font-weight: bold; font-size: 14px;">🥇 금 가격</span>
                <span style="color: white; font-size: 12px; margin-left: 10px;">${current_gold:.2f} | 30일 {gold_change:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            gold_chart = gold_data.set_index('Date')[['Gold']]
            st.area_chart(gold_chart, color="#FFD700", height=200)
            st.caption("💡 인플레이션 헤지 자산, 달러 약세/지정학적 리스크 시 상승")
        else:
            st.warning("금 가격 데이터 없음")
    
    with col2:
        # 공포탐욕지수 (VIX 기반)
        current_vix = fg_data['VIX'].iloc[-1] if fg_data is not None and len(fg_data) > 0 else 0
        current_fg = fg_data['Fear_Greed'].iloc[-1] if fg_data is not None and len(fg_data) > 0 else 0
        
        if current_fg < 25:
            mood = "😱 극도공포"
            mood_color = "#FF4757"
        elif current_fg < 50:
            mood = "😰 공포"
            mood_color = "#FF6B35"
        elif current_fg < 75:
            mood = "😐 중립"
            mood_color = "#FFA502"
        else:
            mood = "🤑 탐욕"
            mood_color = "#26C6DA"
            
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #E74C3C, {mood_color}); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
            <span style="color: white; font-weight: bold; font-size: 14px;">😱 공포탐욕지수</span>
            <span style="color: white; font-size: 12px; margin-left: 10px;">VIX {current_vix:.2f} | 지수 {current_fg:.1f} ({mood})</span>
        </div>
        """, unsafe_allow_html=True)
        
        if fg_data is not None and len(fg_data) > 0:
            vix_chart = fg_data.set_index('Date')[['VIX']]
            st.line_chart(vix_chart, color="#E74C3C", height=200)
            
            fg_chart = fg_data.set_index('Date')[['Fear_Greed']]
            st.area_chart(fg_chart, color="#FF9F43", height=150)
            
            st.caption("💡 VIX는 변동성 지수, 높을수록 시장 불안정. 지수는 VIX 역산 (0=극도공포, 100=극도탐욕)")
        else:
            st.warning("공포탐욕지수 데이터 없음")
        
        # 부동산 지수
        current_price = fred_data['Real_Estate_Index'].iloc[-1] if fred_data is not None and len(fred_data) > 0 else 0
        change_pct = 0
        if fred_data is not None and len(fred_data) > 20:
            prev_price = fred_data['Real_Estate_Index'].iloc[-21]
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, #2ECC71, #00D2D3); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
            <span style="color: white; font-weight: bold; font-size: 14px;">🏠 부동산 지수</span>
            <span style="color: white; font-size: 12px; margin-left: 10px;">${current_price:.2f} | 20일 {change_pct:+.2f}%</span>
        </div>
        """, unsafe_allow_html=True)
        
        if fred_data is not None and len(fred_data) > 0:
            real_estate_chart = fred_data.set_index('Date')[['Real_Estate_Index']]
            st.area_chart(real_estate_chart, color="#2ECC71", height=200)
            st.caption("💡 VNQ REIT ETF로 부동산 시장 추적. 금리와 역상관, 인플레이션 헤지")
        else:
            st.warning("부동산 지수 데이터 없음")
        
        # 수익률 곡선
        yield_data = additional_data.get('yield_curve')
        if yield_data is not None and len(yield_data) > 0:
            current_spread = yield_data['Yield_Spread'].iloc[-1]
            
            if current_spread < 0:
                curve_status = "⚠️ 역전"
                curve_color = "#FF4757"
            else:
                curve_status = "✅ 정상"
                curve_color = "#26C6DA"
                
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #8E44AD, {curve_color}); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                <span style="color: white; font-weight: bold; font-size: 14px;">📊 수익률 곡선</span>
                <span style="color: white; font-size: 12px; margin-left: 10px;">{current_spread:.2f}bp ({curve_status})</span>
            </div>
            """, unsafe_allow_html=True)
            
            spread_chart = yield_data.set_index('Date')[['Yield_Spread']]
            st.line_chart(spread_chart, color="#8E44AD", height=200)
            st.caption("💡 양수=정상(장기>단기금리), 음수=역전(경기침체 신호)")
        else:
            st.warning("수익률 곡선 데이터 없음")
        
        # 원유 가격
        oil_data = additional_data.get('oil')
        if oil_data is not None and len(oil_data) > 0:
            current_oil = oil_data['Oil'].iloc[-1]
            prev_oil = oil_data['Oil'].iloc[-30] if len(oil_data) > 30 else oil_data['Oil'].iloc[0]
            oil_change = ((current_oil - prev_oil) / prev_oil) * 100
            
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #CD5C5C, #FF6B6B); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
                <span style="color: white; font-weight: bold; font-size: 14px;">🛢️ 원유 가격</span>
                <span style="color: white; font-size: 12px; margin-left: 10px;">${current_oil:.2f} | 30일 {oil_change:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)
            
            oil_chart = oil_data.set_index('Date')[['Oil']]
            st.line_chart(oil_chart, color="#CD5C5C", height=200)
            st.caption("💡 인플레이션 선행지표, 상승 시 에너지/운송비용 증가로 물가 압력")
        else:
            st.warning("원유 가격 데이터 없음")
    
    # 통합 상관관계 분석 섹션
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(90deg, #667eea, #764ba2); padding: 12px 16px; border-radius: 15px; margin: 16px 0;">
        <span style="color: white; font-weight: bold; font-size: 16px;">📈 전체 지표 상관관계 분석</span>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # 모든 지표 데이터 수집
        correlation_data_dict = {}
        
        if spread_data is not None and len(spread_data) > 0:
            correlation_data_dict['HYG가격'] = spread_data['HYG_Price']
            correlation_data_dict['국채10Y'] = spread_data['Treasury_10Y']
        
        if fg_data is not None and len(fg_data) > 0:
            correlation_data_dict['VIX'] = fg_data['VIX']
            correlation_data_dict['공포탐욕지수'] = fg_data['Fear_Greed']
        
        if pc_data is not None and len(pc_data) > 0:
            correlation_data_dict['풋콜레이쇼'] = pc_data['Put_Call_Ratio']
            correlation_data_dict['SPX'] = pc_data['SPX']
        
        if fred_data is not None and len(fred_data) > 0:
            correlation_data_dict['부동산지수'] = fred_data['Real_Estate_Index']
        
        # 추가 지표들
        if additional_data.get('dxy') is not None:
            correlation_data_dict['달러인덱스'] = additional_data['dxy']['DXY']
        
        if additional_data.get('yield_curve') is not None:
            correlation_data_dict['수익률곡선'] = additional_data['yield_curve']['Yield_Spread']
        
        if additional_data.get('gold') is not None:
            correlation_data_dict['금가격'] = additional_data['gold']['Gold']
        
        if additional_data.get('oil') is not None:
            correlation_data_dict['원유가격'] = additional_data['oil']['Oil']
        
        if len(correlation_data_dict) >= 3:
            # 최소 길이로 데이터 맞추기
            min_len = min([len(v) for v in correlation_data_dict.values()])
            
            correlation_df = pd.DataFrame({
                k: v[:min_len] for k, v in correlation_data_dict.items()
            })
            
            # 상관관계 매트릭스 계산
            corr_matrix = correlation_df.corr()
            
            # 상관관계 매트릭스를 DataFrame으로 표시
            st.write("**🔥 모든 지표간 상관관계 매트릭스:**")
            styled_corr = corr_matrix.style.background_gradient(cmap='RdBu_r', vmin=-1, vmax=1).format("{:.3f}")
            st.dataframe(styled_corr, use_container_width=True)
            
            # 주요 상관관계 하이라이트
            st.markdown("**🔍 강한 상관관계 TOP 5:**")
            
            # 대각선 제외하고 상관관계 추출
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
            corr_pairs = corr_matrix.mask(mask).stack().abs().sort_values(ascending=False)
            
            correlation_insights = []
            for i, (pair, abs_corr_val) in enumerate(corr_pairs.head(5).items()):
                original_corr = corr_matrix.loc[pair[0], pair[1]]
                direction = "양의 상관" if original_corr > 0 else "음의 상관"
                strength = "매우 강한" if abs_corr_val > 0.7 else "강한" if abs_corr_val > 0.5 else "보통"
                
                correlation_insights.append(f"**{i+1}.** {pair[0]} ↔ {pair[1]}: **{original_corr:.3f}** ({strength} {direction})")
            
            for insight in correlation_insights:
                st.markdown(insight)
            
            # 시장 인사이트
            st.markdown("**💡 주요 시장 인사이트:**")
            insight_text = "• **리스크 온/오프**: VIX와 다른 지표들의 역상관 관계 확인\n"
            insight_text += "• **달러 강세 영향**: 달러인덱스와 금/원자재의 역상관 관계\n"
            insight_text += "• **금리 환경**: 수익률곡선과 부동산/주식시장의 관계\n"
            insight_text += "• **인플레이션 압력**: 원유가격과 다른 자산군의 상관관계"
            
            st.markdown(insight_text)
        
        else:
            st.info("충분한 데이터가 로드되면 상관관계 분석이 표시됩니다.")
            
    except Exception as e:
        st.error(f"상관관계 분석 중 오류 발생: {e}")
    
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
    
        # RSI 계산 (removed unused rsi_badge variable)
        rsi_info = ""
        if technical_data is not None and 'rsi' in technical_data.columns:
            current_rsi = technical_data['rsi'].iloc[-1]
            if not pd.isna(current_rsi):
                if current_rsi > 70:
                    rsi_status = "과매수"
                    rsi_color = "#ff4444"
                elif current_rsi < 30:
                    rsi_status = "과매도"
                    rsi_color = "#44ff44"
                else:
                    rsi_status = "중립"
                    rsi_color = "#4488ff"
                rsi_info = f'<span style="background-color: {rsi_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold;">{rsi_status}</span>'
    
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

# Custom CSS for clean sky-blue and white design
st.markdown("""
<style>
    /* Global app styling - Clean sky background */
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #f8fdff 50%, #ffffff 100%);
        min-height: 100vh;
    }
    
    /* Main content wrapper - Pure white */
    .main .block-container {
        background: #ffffff;
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem;
        box-shadow: 0 4px 20px rgba(0, 122, 255, 0.08);
        border: 1px solid rgba(135, 206, 250, 0.15);
    }
    
    /* All text elements - clean typography */
    body, .stApp, .main, .stSidebar,
    h1, h2, h3, h4, h5, h6, p, span, div, label, 
    .stMarkdown, .stText, .streamlit-container {
        color: #2c3e50 !important;
    }
    
    /* Headings with soft blue accent */
    h1, h2, h3 {
        color: #1976d2 !important;
        font-weight: 700 !important;
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
    
    /* Modern compact metrics cards */
    .stMetric {
        background: linear-gradient(135deg, #f8faff 0%, #ffffff 100%);
        border: 1px solid rgba(66, 165, 245, 0.12);
        padding: 0.3rem 0.4rem;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(66, 165, 245, 0.05);
        transition: all 0.25s ease;
        min-height: 35px;
        position: relative;
        overflow: hidden;
    }
    
    .stMetric::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #42a5f5, #64b5f6, #90caf9);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .stMetric:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(66, 165, 245, 0.12);
        border-color: rgba(66, 165, 245, 0.25);
    }
    
    .stMetric:hover::before {
        opacity: 1;
    }
    
    .stMetric label {
        color: #5f6368 !important;
        font-weight: 500 !important;
        font-size: 0.5rem !important;
        text-transform: none;
        letter-spacing: 0.02em;
        margin-bottom: 0.05rem !important;
    }
    
    .stMetric > div > div[data-testid="metric-value"] {
        color: #1a73e8 !important;
        font-weight: 600 !important;
        font-size: 0.65rem !important;
        line-height: 1 !important;
    }
    
    .stMetric > div > div[data-testid="metric-delta"] {
        color: #34a853 !important;
        font-weight: 500 !important;
        font-size: 0.6rem !important;
    }
    
    /* Clean agent status cards - mini flow version */
    .agent-status {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 20px;
        font-weight: 500;
        text-align: center;
        margin: 0.2rem 0.3rem 0.2rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
        border: 1px solid transparent;
        font-size: 0.7rem;
        min-width: 60px;
    }
    
    .agent-status:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .status-pending {
        background: #fff8e1;
        color: #e65100;
        border-color: #ffcc02;
    }
    
    .status-in-progress {
        background: #e3f2fd;
        color: #1565c0;
        border-color: #42a5f5;
        animation: softPulse 2s ease-in-out infinite;
    }
    
    @keyframes softPulse {
        0%, 100% { 
            background: #e3f2fd;
            transform: scale(1);
        }
        50% { 
            background: #bbdefb;
            transform: scale(1.02);
        }
    }
    
    .status-completed {
        background: #e8f5e8;
        color: #2e7d32;
        border-color: #66bb6a;
    }
    
    .status-error {
        background: #ffebee;
        color: #c62828;
        border-color: #ef5350;
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
    
    /* Clean welcome header */
    .welcome-header {
        text-align: center;
        padding: 3rem;
        background: linear-gradient(135deg, #e3f2fd 0%, #ffffff 50%, #f5f9ff 100%);
        color: #1976d2;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(66, 165, 245, 0.12);
        border: 2px solid rgba(135, 206, 250, 0.2);
    }
    
    .welcome-header h1 {
        margin-bottom: 0.5rem;
        font-size: 2.5rem;
        font-weight: 800;
        color: #1976d2 !important;
    }
    
    .welcome-header h3 {
        margin-bottom: 1rem;
        font-weight: 500;
        color: #546e7a !important;
        font-size: 1.2rem;
    }
    
    .welcome-header p {
        color: #37474f !important;
        font-size: 1rem;
        font-weight: 500;
    }
    
    /* Modern primary buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.25);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.35);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:active {
        transform: translateY(0px);
        box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3);
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
    
    /* Clean tabs */
    .stTabs [data-baseweb="tab"] {
        background: #f5f9ff;
        color: #546e7a !important;
        border-radius: 8px 8px 0 0;
        border: 1px solid #e3f2fd;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #e3f2fd;
        color: #1976d2 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: #42a5f5 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(66, 165, 245, 0.3);
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
    
    /* 모바일 최적화 */
    @media (max-width: 768px) {
        /* 차트 컨테이너 모바일 최적화 */
        .stPlotlyChart {
            width: 100% !important;
            overflow-x: auto;
            /* 페이지 스크롤 우선, 차트 상호작용 최소화 */
            touch-action: auto;
        }
        
        /* Plotly 차트에서 페이지 스크롤 허용 */
        .js-plotly-plot .plotly {
            touch-action: auto !important;
            user-select: none !important;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            /* 차트 상호작용보다 페이지 스크롤 우선 */
            pointer-events: none !important;
        }
        
        /* 차트 오버레이 요소들도 터치 이벤트 통과 */
        .js-plotly-plot .plotly .nsewdrag,
        .js-plotly-plot .plotly .drag,
        .js-plotly-plot .plotly .cursor-crosshair {
            touch-action: auto !important;
            pointer-events: none !important;
        }
        
        /* 차트 배경도 터치 이벤트 통과 */
        .js-plotly-plot .plotly .bg {
            pointer-events: none !important;
        }
        
        /* 모바일에서 차트 마진 조정 */
        .js-plotly-plot .plotly .modebar {
            left: 10px !important;
            top: 10px !important;
        }
        
        /* 탭 텍스트 모바일에서 줄바꿈 방지 */
        .stTabs [data-baseweb="tab"] {
            min-width: auto !important;
            font-size: 0.85rem !important;
            padding: 0.5rem 0.75rem !important;
        }
        
        /* 메트릭 카드 모바일 최적화 */
        .stMetric {
            margin-bottom: 0.5rem !important;
        }
        
        /* 모바일에서 컬럼 간격 줄이기 */
        .stColumns > div {
            padding: 0 0.25rem !important;
        }
        
        /* 뱃지 스타일 모바일 최적화 */
        div[style*="display: flex; flex-wrap: wrap"] {
            gap: 8px !important;
        }
        
        div[style*="min-width: 160px"] {
            min-width: 140px !important;
            font-size: 0.9rem !important;
        }
    }
    
    /* 아주 작은 화면 (스마트폰) */
    @media (max-width: 480px) {
        .stTabs [data-baseweb="tab"] {
            font-size: 0.75rem !important;
            padding: 0.4rem 0.5rem !important;
        }
        
        /* 헤더 텍스트 크기 조정 */
        .welcome-header h1 {
            font-size: 1.8rem !important;
        }
        
        .welcome-header h3 {
            font-size: 1rem !important;
        }
        
        /* 뱃지 더 작게 */
        div[style*="min-width: 160px"] {
            min-width: 120px !important;
            padding: 8px 12px !important;
        }
        
        div[style*="font-size: 1.5em"] {
            font-size: 1.2em !important;
        }
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
        <h1>🔐 트레이딩 에이전트 대시보드</h1>
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
        <h1>💹 트레이딩 에이전트 대시보드</h1>
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
                "Confidence": f"{session['confidence_score']:.1%}" if session['confidence_score'] else '-',
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
            
            # 선택된 리포트 표시
            if st.button("📖 Load Report", type="primary"):
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
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["🧠 AI 분석", "📚 분석 히스토리", "📈 Market Agent 주식 분석","📊 거시경제 지표",])
    
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