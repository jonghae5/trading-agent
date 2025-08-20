"""
Chart utilities and common configuration for Plotly charts
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import yfinance as yf
import os
from typing import Dict, Optional
import logging


class ChartUtils:
    """Utility class for common chart configurations and mobile optimization"""
    
    @staticmethod
    def get_mobile_chart_config():
        """Get optimized chart configuration for mobile devices"""
        return {
            'displayModeBar': False,
            'scrollZoom': False,
            'doubleClick': False,
            'showTips': False,
            'staticPlot': False,
            'modeBarButtonsToRemove': [
                'zoom2d', 'pan2d', 'select2d', 'lasso2d', 
                'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d'
            ]
        }
    
    @staticmethod
    def get_standard_layout_config():
        """Get standard layout configuration for charts"""
        return {
            'margin': dict(l=20, r=20, t=40, b=20),
            'legend': dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            'dragmode': 'pan',
            'xaxis': dict(fixedrange=True),
            'yaxis': dict(fixedrange=True)
        }
    
    @staticmethod
    def apply_mobile_optimization(fig):
        """Apply mobile optimization to a plotly figure"""
        config = ChartUtils.get_standard_layout_config()
        fig.update_layout(**config)
        return fig
    
    @staticmethod
    def create_financial_color_scale():
        """Create standard financial color scale"""
        return {
            'positive': '#10b981',  # Green
            'negative': '#ef4444',  # Red
            'neutral': '#6b7280',   # Gray
            'primary': '#0ea5e9',   # Blue
            'warning': '#f59e0b',   # Orange
        }
    
    @staticmethod
    def add_crisis_markers_to_chart(fig, data_series, crisis_dates=None, date_column=None):
        """차트에 경제 위기 시점 마커 추가하는 공통 함수"""
        if crisis_dates is None:
            crisis_dates = ChartUtils.get_economic_crisis_dates()
        
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

    @staticmethod
    def get_economic_crisis_dates():
        """경제 위기 및 주식시장 타격 시점 정의 - 공통 함수"""
        return [
            ('2000-03-01', '닷컴 버블 붕괴'),
            ('2001-09-01', '9·11 테러'),
            ('2006-01-01', '부동산 버블 정점'),
            ('2008-09-01', '리먼 브라더스'),
            ('2012-01-01', '주택시장 회복'),
            ('2018-12-01', '미국 증시 19% 조정'),
            ('2020-03-01', 'COVID-19 팬데믹'),
            ('2022-02-01', '러-우 침공 및 러시아 증시 붕괴'),
            ('2022-03-01', 'Fed 긴축 시작'),
            ('2024-02-01', '중국 주식 시장 붕괴'),
            ('2024-08-01', '도쿄 증시 붕괴'),
            ('2025-04-01', '미·중 무역갈등 악화'),
        ]


# Global cached functions for economic data
@st.cache_data(ttl=300)
def get_fear_greed_index():
    """CNN 공포탐욕지수 가져오기 (대체 지표로 VIX 사용)"""
    try:
        vix_data = yf.download('^VIX', period='5y', interval='1d')
        
        vix_df = vix_data[['Close']].reset_index()
        vix_df.columns = ['Date', 'VIX']
        
        vix_df['Fear_Greed'] = 100 - np.clip((vix_df['VIX'] - 10) / 70 * 100, 0, 100)
        
        return vix_df.dropna()
    except Exception as e:
        st.error(f"공포탐욕지수(VIX) 데이터 로딩 실패: {e}")
        return None


@st.cache_data(ttl=300)
def get_put_call_ratio():
    """풋콜레이쇼 데이터 가져오기"""
    try:
        spx_data = yf.download('^SPX', period='5y', interval='1d')
        vix_data = yf.download('^VIX', period='5y', interval='1d')
        
        spx_df = spx_data[['Close']].reset_index()
        vix_df = vix_data[['Close']].reset_index()
        
        spx_df.columns = ['Date', 'SPX']
        vix_df.columns = ['Date', 'VIX']
        
        put_call_data = pd.merge(spx_df, vix_df, on='Date', how='inner')
        put_call_data['Put_Call_Ratio'] = (put_call_data['VIX'] / 20) * 1.2
        
        return put_call_data.dropna()
    except Exception as e:
        st.error(f"풋콜레이쇼 데이터 로딩 실패: {e}")
        return None


@st.cache_data(ttl=300)
def get_additional_indicators():
    """추가 필수 지표들 로드"""
    indicators = {}    
    try:
        gold_data = yf.download('GC=F', period='5y', interval='1mo')
        if not gold_data.empty:
            gold_df = gold_data[['Close']].reset_index()
            gold_df.columns = ['Date', 'Gold']
            indicators['gold'] = gold_df
    except:
        indicators['gold'] = None
    
    return indicators


@st.cache_data(ttl=300)
def get_fred_macro_indicators() -> Optional[Dict]:
    """FRED API를 사용하여 주요 거시경제 지표들을 가져오는 함수"""
    try:
        from fredapi import Fred
        FRED_AVAILABLE = True
    except ImportError:
        FRED_AVAILABLE = False
    
    if not FRED_AVAILABLE:
        return None
    
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        st.warning("FRED_API_KEY 환경 변수를 설정해주세요.")
        return None
    
    try:
        fred = Fred(api_key=fred_api_key)
        indicators = {}
        
        fred_series = {
            'federal_rate': 'FEDFUNDS',
            'gdp': 'GDP', 
            'pmi': 'MANEMP',
            'm2': 'M2SL',
            'retail_sales': 'RSAFS',
            'housing_market': 'USAUCSFRCONDOSMSAMID',
            'high_yield_spread': 'BAMLH0A0HYM2',
            'unemployment': 'UNRATE',
            'cpi': 'CPIAUCSL',
            'total_debt': 'GFDEBTN'
        }
        
        for key, series_id in fred_series.items():
            try:
                data = fred.get_series(series_id, observation_start='1/1/1990')
                if data is not None and len(data) > 0:
                    indicators[key] = data.dropna()
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"[FRED] Failed to fetch {key}: {str(e)}")
        
        return indicators if indicators else None
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"[FRED] Failed to initialize FRED client: {str(e)}")
        return None


@st.cache_data(ttl=300)
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
        
        additional_series = {
            'vix': 'VIXCLS',
            'dollar_index': 'DTWEXBGS',
            'oil_price': 'DCOILWTICO'
        }
        
        for key, series_id in additional_series.items():
            try:
                data = fred.get_series(series_id, observation_start='1/1/1990')
                if data is not None and len(data) > 0:
                    indicators[key] = data.dropna()
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"[FRED] Failed to fetch {key}: {str(e)}")
        
        # Special handling for yield spread
        try:
            ten_year_yield = fred.get_series('DGS10', observation_start='1/1/1990')
            two_year_yield = fred.get_series('DGS2', observation_start='1/1/1990')
            if ten_year_yield is not None and two_year_yield is not None:
                yield_spread = ten_year_yield - two_year_yield
                indicators['yield_spread'] = yield_spread.dropna()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"[FRED] Failed to fetch Yield Spread: {str(e)}")
        
        return indicators if indicators else None
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"[FRED] Failed to fetch additional FRED indicators: {str(e)}")
        return None


@st.cache_data(ttl=300)  
def get_stock_data_for_viz(symbol: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """주식 데이터 가져오기 with enhanced error handling and validation"""
    try:
        import yfinance as yf
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Input validation
        if not symbol:
            return None
            
        # Sanitize and validate the symbol
        clean_symbol = ''.join(c for c in symbol.upper() if c.isalnum())[:10]
        if not (clean_symbol.isalnum() and 1 <= len(clean_symbol) <= 10):
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
        st.error(f"Data loading failed for {symbol}: {str(e)}")
        logger.error(f"[STOCK_DATA] Failed to load data for {symbol}: {str(e)}")
        return None


@st.cache_data(ttl=300)
def calculate_technical_indicators(data: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    """기술적 지표 계산 with improved error handling and validation"""
    if data is None or data.empty:
        return None
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        
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
            logger.warning(f"[INDICATORS] SMA calculation error: {str(e)}")
        
        # 지수이동평균
        try:
            df['ema_10'] = df['Close'].ewm(span=10).mean()
            df['ema_20'] = df['Close'].ewm(span=20).mean()
        except Exception as e:
            logger.warning(f"[INDICATORS] EMA calculation error: {str(e)}")
        
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
            logger.warning(f"[INDICATORS] RSI calculation error: {str(e)}")
        
        # MACD 계산
        try:
            ema_12 = df['Close'].ewm(span=12).mean()
            ema_26 = df['Close'].ewm(span=26).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
        except Exception as e:
            logger.warning(f"[INDICATORS] MACD calculation error: {str(e)}")
        
        # 볼린저 밴드 (with validation)
        try:
            df['bb_middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            
            # Ensure standard deviation is valid
            bb_std = bb_std.fillna(0)
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        except Exception as e:
            logger.warning(f"[INDICATORS] Bollinger Bands calculation error: {str(e)}")
        
        # ATR 계산 (with validation)
        try:
            high_low = df['High'] - df['Low']
            high_close = abs(df['High'] - df['Close'].shift())
            low_close = abs(df['Low'] - df['Close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = true_range.rolling(window=14).mean()
        except Exception as e:
            logger.warning(f"[INDICATORS] ATR calculation error: {str(e)}")
        
        # VWMA 계산 (with zero volume protection)
        try:
            def vwma(price: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
                volume_safe = volume.replace(0, 1)  # Prevent division by zero
                return (price * volume_safe).rolling(window=window).sum() / volume_safe.rolling(window=window).sum()
            
            df['vwma'] = vwma(df['Close'], df['Volume'], 20)
        except Exception as e:
            logger.warning(f"[INDICATORS] VWMA calculation error: {str(e)}")
        
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
            logger.warning(f"[INDICATORS] Stochastic calculation error: {str(e)}")
        
        return df
        
    except Exception as e:
        st.error(f"Technical indicators calculation failed: {str(e)}")
        logger.error(f"[INDICATORS] Calculation failed: {str(e)}")
        return data  # Return original data if calculation fails