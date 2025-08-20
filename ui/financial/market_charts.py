"""
Market Charts UI Component
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
import numpy as np
import time
from typing import Optional
import logging



class MarketCharts:
    """Handles market analysis dashboard with interactive charts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
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



    def render_dashboard(self):
        """Market Agent 데이터 시각화 대시보드"""
        try:
            st.header("📈 Market Agent 주식 통계 시각화")
            
            # 메인 영역에서 설정
            st.subheader("🎯 분석 설정")
            
            # 설정을 3개 열로 배치
            col1, col2, col3 = st.columns([2, 2, 3])
            
            ticker, period = self._render_input_controls(col1, col2)
            show_charts = self._render_chart_options(col3)
            
            st.markdown("---")
            
            if not ticker:
                st.warning("티커 심볼을 입력해주세요.")
                return
            
            # 상태 컨테이너 생성
            status_container = st.empty()
            
            # 데이터 로드 및 분석
            stock_data, technical_data = self._load_and_process_data(ticker, period, status_container)
            
            if stock_data is None or stock_data.empty:
                status_container.empty()
                st.error(f"❌ {ticker} 데이터를 불러올 수 없습니다. 다른 티커를 시도해보세요.")
                return
            
            # 상태 메시지 제거
            status_container.empty()
            
            # 기본 정보 표시
            self._render_stock_info(stock_data, ticker)
            
            # 차트 표시
            self._render_charts(technical_data, ticker, show_charts)
            
            # 기술적 지표 요약 테이블
            if technical_data is not None:
                self._render_technical_summary(technical_data, stock_data)
        
        except Exception as e:
            st.error(f"Market Agent 대시보드 로딩 중 오류가 발생했습니다: {e}")
            st.info("다른 탭을 사용하거나 페이지를 새로고침 해보세요.")
    
    def _render_input_controls(self, col1, col2):
        """Render input controls for ticker and period"""
        from streamlit_app import (
            DEFAULT_TICKER, MAX_TICKER_LENGTH, sanitize_ticker, 
            validate_ticker
        )
        
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
        
        return ticker, period
    
    def _render_chart_options(self, col3):
        """Render chart selection options"""
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
        
        return {
            'price': show_price,
            'macd': show_macd, 
            'rsi': show_rsi,
            'atr': show_atr,
            'volume': show_volume
        }
    
    def _load_and_process_data(self, ticker, period, status_container):
        """Load and process stock data"""
        # 1단계: 데이터 로드
        with status_container:
            self.show_step_status(1, 4, f"{ticker} 주식 데이터 다운로드 중...")
        
        stock_data = self._get_stock_data(ticker, period)
        
        if stock_data is None or stock_data.empty:
            return None, None
        
        # 2단계: 기술적 지표 계산
        with status_container:
            self.show_step_status(2, 4, "기술적 지표 계산 중...")
        
        technical_data = self._calculate_technical_indicators(stock_data)
        
        # 3단계: 차트 생성 준비
        with status_container:
            self.show_step_status(3, 4, "차트 생성 중...")
        
        time.sleep(0.2)  # 잠시 표시
        
        # 4단계: 완료
        with status_container:
            self.show_step_status(4, 4, "분석 완료!")
        
        time.sleep(0.5)  # 완료 메시지 표시
        
        return stock_data, technical_data
    
    def _render_stock_info(self, stock_data, ticker):
        """Render stock information badges"""
        current_price = stock_data['Close'].iloc[-1]
        prev_price = stock_data['Close'].iloc[-2]
        price_change = current_price - prev_price
        price_change_pct = (price_change / prev_price) * 100
        
        volume = stock_data['Volume'].iloc[-1]
        avg_volume = stock_data['Volume'].tail(20).mean()
        volume_change = ((volume - avg_volume) / avg_volume) * 100
        
        high_52w = stock_data['High'].tail(252).max()  # 약 1년
        low_52w = stock_data['Low'].tail(252).min()
        
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
    
    def _render_charts(self, technical_data, ticker, show_charts):
        """Render the selected charts"""
        from ..utils.chart_utils import ChartUtils
        
        config = ChartUtils.get_mobile_chart_config()
        
        # 차트 표시
        if show_charts['price']:
            st.subheader("📈 가격 차트 및 이동평균")
            price_chart = self._create_price_chart(technical_data, ticker)
            if price_chart:
                st.plotly_chart(price_chart, use_container_width=True, config=config)
        
        # 2개 열로 나누어 차트 배치
        col1, col2 = st.columns(2)
        
        with col1:
            if show_charts['macd']:
                st.subheader("📊 MACD")
                macd_chart = self._create_macd_chart(technical_data, ticker)
                if macd_chart:
                    st.plotly_chart(macd_chart, use_container_width=True, config=config)
            
            if show_charts['atr']:
                st.subheader("📈 ATR (변동성)")
                atr_chart = self._create_atr_chart(technical_data, ticker)
                if atr_chart:
                    st.plotly_chart(atr_chart, use_container_width=True, config=config)
        
        with col2:
            if show_charts['rsi']:
                st.subheader("⚡ RSI")
                rsi_chart = self._create_rsi_chart(technical_data, ticker)
                if rsi_chart:
                    st.plotly_chart(rsi_chart, use_container_width=True, config=config)
            
            if show_charts['volume']:
                st.subheader("📊 거래량 분석")
                volume_chart = self._create_volume_analysis_chart(technical_data, ticker)
                if volume_chart:
                    st.plotly_chart(volume_chart, use_container_width=True, config=config)
    
    def _render_technical_summary(self, technical_data, stock_data):
        """Render technical indicators summary table"""
        st.subheader("📋 기술적 지표 요약")
        
        current_price = stock_data['Close'].iloc[-1]
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
    
    def _get_stock_data(self, symbol: str, period: str = "6mo") -> Optional[pd.DataFrame]:
        """주식 데이터 가져오기 with enhanced error handling and validation"""
        try:
            from streamlit_app import (
                sanitize_ticker, validate_ticker, sanitize_log_message
            )
            
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
            from streamlit_app import sanitize_log_message
            error_msg = sanitize_log_message(str(e))
            st.error(f"Data loading failed for {symbol}: {error_msg}")
            self.logger.error(f"[STOCK_DATA] Failed to load data for {symbol}: {error_msg}")
            return None

    def _calculate_technical_indicators(self, data: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
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
                self.logger.warning(f"[INDICATORS] SMA calculation error: {e}")
            
            # 지수이동평균
            try:
                df['ema_10'] = df['Close'].ewm(span=10).mean()
                df['ema_20'] = df['Close'].ewm(span=20).mean()
            except Exception as e:
                self.logger.warning(f"[INDICATORS] EMA calculation error: {e}")
            
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
                self.logger.warning(f"[INDICATORS] RSI calculation error: {e}")
            
            # MACD 계산
            try:
                ema_12 = df['Close'].ewm(span=12).mean()
                ema_26 = df['Close'].ewm(span=26).mean()
                df['macd'] = ema_12 - ema_26
                df['macd_signal'] = df['macd'].ewm(span=9).mean()
                df['macd_histogram'] = df['macd'] - df['macd_signal']
            except Exception as e:
                self.logger.warning(f"[INDICATORS] MACD calculation error: {e}")
            
            # 볼린저 밴드 (with validation)
            try:
                df['bb_middle'] = df['Close'].rolling(window=20).mean()
                bb_std = df['Close'].rolling(window=20).std()
                
                # Ensure standard deviation is valid
                bb_std = bb_std.fillna(0)
                df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
                df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            except Exception as e:
                self.logger.warning(f"[INDICATORS] Bollinger Bands calculation error: {e}")
            
            # ATR 계산 (with validation)
            try:
                high_low = df['High'] - df['Low']
                high_close = abs(df['High'] - df['Close'].shift())
                low_close = abs(df['Low'] - df['Close'].shift())
                true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                df['atr'] = true_range.rolling(window=14).mean()
            except Exception as e:
                self.logger.warning(f"[INDICATORS] ATR calculation error: {e}")
            
            # VWMA 계산 (with zero volume protection)
            try:
                def vwma(price: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
                    volume_safe = volume.replace(0, 1)  # Prevent division by zero
                    return (price * volume_safe).rolling(window=window).sum() / volume_safe.rolling(window=window).sum()
                
                df['vwma'] = vwma(df['Close'], df['Volume'], 20)
            except Exception as e:
                self.logger.warning(f"[INDICATORS] VWMA calculation error: {e}")
            
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
                self.logger.warning(f"[INDICATORS] Stochastic calculation error: {e}")
            
            return df
            
        except Exception as e:
            from streamlit_app import sanitize_log_message
            error_msg = sanitize_log_message(str(e))
            st.error(f"Technical indicators calculation failed: {error_msg}")
            self.logger.error(f"[INDICATORS] Calculation failed: {error_msg}")
            return data  # Return original data if calculation fails

    def _create_price_chart(self, data, symbol):
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
        
        from ..utils.chart_utils import ChartUtils
        layout_config = ChartUtils.get_standard_layout_config()
        layout_config.update({
            'title': f'{symbol} 주가 및 기술적 지표',
            'xaxis_rangeslider_visible': False,
            'height': 800,
            'showlegend': True,
        })
        
        fig.update_layout(**layout_config)
        
        return fig

    def _create_macd_chart(self, data, symbol):
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
        
        from ..utils.chart_utils import ChartUtils
        layout_config = ChartUtils.get_standard_layout_config()
        layout_config.update({
            'title': f'{symbol} MACD 지표',
            'xaxis_title': '날짜',
            'yaxis_title': '값',
            'height': 400,
        })
        
        fig.update_layout(**layout_config)
        
        return fig

    def _create_rsi_chart(self, data, symbol):
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
        
        from ..utils.chart_utils import ChartUtils
        layout_config = ChartUtils.get_standard_layout_config()
        layout_config.update({
            'title': f'{symbol} RSI 지표',
            'xaxis_title': '날짜',
            'yaxis_title': 'RSI',
            'yaxis': dict(range=[0, 100], fixedrange=True),
            'height': 400,
        })
        
        fig.update_layout(**layout_config)
        
        return fig

    def _create_atr_chart(self, data, symbol):
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
        
        from ..utils.chart_utils import ChartUtils
        layout_config = ChartUtils.get_standard_layout_config()
        layout_config.update({
            'title': f'{symbol} ATR (Average True Range) 변동성 지표',
            'xaxis_title': '날짜',
            'yaxis_title': 'ATR',
            'height': 400,
        })
        
        fig.update_layout(**layout_config)
        
        return fig

    def _create_volume_analysis_chart(self, data, symbol):
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
        
        from ..utils.chart_utils import ChartUtils
        layout_config = ChartUtils.get_standard_layout_config()
        layout_config.update({
            'title': f'{symbol} 거래량 분석',
            'height': 600,
            'showlegend': True,
        })
        
        fig.update_layout(**layout_config)
        
        # 서브플롯의 각 축에 대해 고정 범위 설정 (줌 비활성화)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        
        return fig