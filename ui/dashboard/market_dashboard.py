"""
Market Dashboard Module for Market Agent data visualization
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
import logging
from typing import Optional
from ..charts.chart_factory import ChartFactory
from ..utils.chart_utils import ChartUtils


class MarketDashboard:
    """Market Agent 주식 통계 시각화 대시보드"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chart_factory = ChartFactory()
        self.chart_utils = ChartUtils()
    
    def render_configuration_section(self) -> tuple:
        """분석 설정 섹션 렌더링"""
        st.subheader("🎯 분석 설정")
        
        # 설정을 3개 열로 배치
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            # 티커 입력 with validation
            ticker_input = st.text_input(
                "주식 티커 심볼", 
                value="SPY",
                help="예: AAPL, TSLA, GOOGL, SPY",
                key="market_ticker",
                max_chars=10
            )
            
            # Sanitize and validate ticker
            ticker = self._sanitize_ticker(ticker_input)
            if ticker_input and not self._validate_ticker(ticker):
                st.error("⚠️ Invalid ticker symbol. Please use only letters and numbers.")
                ticker = "SPY"
        
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
        
        return ticker, period, show_price, show_macd, show_rsi, show_atr, show_volume
    
    def _sanitize_ticker(self, ticker: str) -> str:
        """티커 심볼 정리"""
        if not ticker:
            return ""
        
        # 위험한 문자 제거 및 길이 제한
        sanitized = ''.join(c for c in ticker.upper() if c.isalnum())
        return sanitized[:10]
    
    def _validate_ticker(self, ticker: str) -> bool:
        """티커 심볼 유효성 검증"""
        if not ticker:
            return False
        
        # 기본 검증: 영숫자만, 합리적인 길이
        return (ticker.isalnum() and 
                1 <= len(ticker) <= 10 and
                ticker.isascii())
    
    def show_step_status(self, step_number: int, total_steps: int, current_step: str):
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
    
    def render_stock_metrics(self, stock_data: pd.DataFrame) -> None:
        """주식 기본 정보 메트릭 표시"""
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
    
    def render_technical_summary(self, technical_data: pd.DataFrame, current_price: float) -> None:
        """기술적 지표 요약 테이블"""
        if technical_data is None:
            return
            
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
    
    def render(self) -> None:
        """Market Agent 데이터 시각화 대시보드 메인 렌더링"""
        try:
            st.header("📈 Market Agent 주식 통계 시각화")
            
            # 설정 섹션
            ticker, period, show_price, show_macd, show_rsi, show_atr, show_volume = self.render_configuration_section()
            
            st.markdown("---")
            
            if not ticker:
                st.warning("티커 심볼을 입력해주세요.")
                return
            
            # 상태 컨테이너 생성
            status_container = st.empty()
            
            # 1단계: 데이터 로드
            with status_container:
                self.show_step_status(1, 4, f"{ticker} 주식 데이터 다운로드 중...")
            
            from ..utils.chart_utils import get_stock_data_for_viz, calculate_technical_indicators
            stock_data = get_stock_data_for_viz(ticker, period)
            
            if stock_data is None or stock_data.empty:
                status_container.empty()
                st.error(f"❌ {ticker} 데이터를 불러올 수 없습니다. 다른 티커를 시도해보세요.")
                return
            
            # 2단계: 기술적 지표 계산
            with status_container:
                self.show_step_status(2, 4, "기술적 지표 계산 중...")
            
            technical_data = calculate_technical_indicators(stock_data)
            
            # 3단계: 차트 생성 준비
            with status_container:
                self.show_step_status(3, 4, "차트 생성 중...")
            
            time.sleep(0.2)  # 잠시 표시
            
            # 4단계: 완료
            with status_container:
                self.show_step_status(4, 4, "분석 완료!")
            
            time.sleep(0.5)  # 완료 메시지 표시
            
            # 상태 메시지 제거
            status_container.empty()
            
            # 기본 정보 메트릭 표시
            self.render_stock_metrics(stock_data)
            
            # 차트 표시
            if show_price:
                st.subheader("📈 가격 차트 및 이동평균")
                price_chart = self.chart_factory.create_price_chart(technical_data, ticker)
                if price_chart:
                    st.plotly_chart(price_chart, use_container_width=True, 
                                  config=self.chart_factory.get_mobile_chart_config())
            
            # 2개 열로 나누어 차트 배치
            col1, col2 = st.columns(2)
            
            with col1:
                if show_macd:
                    st.subheader("📊 MACD")
                    macd_chart = self.chart_factory.create_macd_chart(technical_data, ticker)
                    if macd_chart:
                        st.plotly_chart(macd_chart, use_container_width=True, 
                                      config=self.chart_factory.get_mobile_chart_config())
                
                if show_atr:
                    st.subheader("📈 ATR (변동성)")
                    atr_chart = self.chart_factory.create_atr_chart(technical_data, ticker)
                    if atr_chart:
                        st.plotly_chart(atr_chart, use_container_width=True, 
                                      config=self.chart_factory.get_mobile_chart_config())
            
            with col2:
                if show_rsi:
                    st.subheader("⚡ RSI")
                    rsi_chart = self.chart_factory.create_rsi_chart(technical_data, ticker)
                    if rsi_chart:
                        st.plotly_chart(rsi_chart, use_container_width=True, 
                                      config=self.chart_factory.get_mobile_chart_config())
                
                if show_volume:
                    st.subheader("📊 거래량 분석")
                    volume_chart = self.chart_factory.create_volume_analysis_chart(technical_data, ticker)
                    if volume_chart:
                        st.plotly_chart(volume_chart, use_container_width=True, 
                                      config=self.chart_factory.get_mobile_chart_config())
            
            # 기술적 지표 요약 테이블
            current_price = stock_data['Close'].iloc[-1]
            self.render_technical_summary(technical_data, current_price)
        
        except Exception as e:
            st.error(f"Market Agent 대시보드 로딩 중 오류가 발생했습니다: {e}")
            st.info("다른 탭을 사용하거나 페이지를 새로고침 해보세요.")
            self.logger.error(f"Market dashboard error: {str(e)}")