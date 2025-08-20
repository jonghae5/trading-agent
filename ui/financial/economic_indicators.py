"""
Economic Indicators UI Component
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import logging


class EconomicIndicators:
    """Handles the economic indicators dashboard"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def render(self):
        """통합 금융 지표 대시보드 - 모든 지표 + 상관관계 분석"""
        st.header("📊 거시 경제 대시보드")
        
        # 모든 데이터 로드 (기존 + 새로운 FRED 지표)
        from ..utils.chart_utils import (
            get_fear_greed_index, get_put_call_ratio, get_additional_indicators,
            get_fred_macro_indicators, get_additional_fred_indicators
        )
        
        fg_data = get_fear_greed_index()
        pc_data = get_put_call_ratio()
        additional_data = get_additional_indicators()
        
        # 새로운 FRED 지표들 로드
        fred_macro = get_fred_macro_indicators()
        fred_additional = get_additional_fred_indicators()
        
        # 데이터 로딩 상태 간단히 표시 (확장된 지표 포함)
        self._render_data_status(fg_data, pc_data, additional_data, fred_macro, fred_additional)
        
        # FRED 지표들 섹션 추가
        if fred_macro or fred_additional:
            self._render_fred_indicators(
                fred_macro, fred_additional, fg_data, pc_data, additional_data
            )
        
        # 개선된 통합 상관관계 분석 섹션
        self._render_correlation_analysis(
            fg_data, pc_data, additional_data, fred_macro, fred_additional
        )
        
        # 업데이트 시간 표시
        self._render_update_time()
    
    def _render_data_status(self, fg_data, pc_data, additional_data, fred_macro, fred_additional):
        """Render data loading status"""
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
    
    def _render_fred_indicators(self, fred_macro, fred_additional, fg_data, pc_data, additional_data):
        """Render FRED economic indicators section"""
        st.markdown("---")
        st.subheader("🏦 FRED 거시경제 지표")
        
        # FRED 지표들을 위한 3열 레이아웃
        fred_col1, fred_col2, fred_col3 = st.columns(3)
        
        # Column 1: GDP, Manufacturing, CPI, Unemployment, Yield Curve
        self._render_fred_column1(fred_col1, fred_macro, fred_additional)
        
        # Column 2: Federal Rate, Debt, M2, High Yield Spread
        self._render_fred_column2(fred_col2, fred_macro)
        
        # Column 3: Put/Call Ratio, Fear/Greed Index, Gold, Oil, Dollar Index
        self._render_fred_column3(fred_col3, pc_data, fg_data, additional_data, fred_additional)
        
        # Additional indicators sections
        self._render_additional_indicators(fred_macro)
    
    def _render_fred_column1(self, col, fred_macro, fred_additional):
        """Render first column of FRED indicators"""
        with col:
            # GDP
            if fred_macro and 'gdp' in fred_macro:
                self._render_gdp_indicator(fred_macro['gdp'])
            
            # 제조업 지수
            if fred_macro and 'pmi' in fred_macro:
                self._render_manufacturing_indicator(fred_macro['pmi'])
            
            # CPI (인플레이션)
            if fred_macro and 'cpi' in fred_macro:
                self._render_cpi_indicator(fred_macro['cpi'])
            
            # 실업률
            if fred_macro and 'unemployment' in fred_macro:
                self._render_unemployment_indicator(fred_macro['unemployment'])
            
            # 수익률 곡선 (FRED)
            if fred_additional and 'yield_spread' in fred_additional:
                self._render_yield_curve_indicator(fred_additional['yield_spread'])
    
    def _render_fred_column2(self, col, fred_macro):
        """Render second column of FRED indicators"""
        with col:
            # 기준금리
            if fred_macro and 'federal_rate' in fred_macro:
                self._render_federal_rate_indicator(fred_macro['federal_rate'])
            
            # 절대 부채
            if fred_macro and 'total_debt' in fred_macro:
                self._render_debt_indicators(fred_macro)
            
            # M2 통화량
            if fred_macro and 'm2' in fred_macro:
                self._render_m2_indicator(fred_macro['m2'])
            
            # 하이일드 스프레드
            if fred_macro and 'high_yield_spread' in fred_macro:
                self._render_high_yield_spread_indicator(fred_macro['high_yield_spread'])
    
    def _render_fred_column3(self, col, pc_data, fg_data, additional_data, fred_additional):
        """Render third column of indicators"""
        with col:
            # 풋콜레이쇼
            self._render_put_call_ratio_indicator(pc_data)
            
            # VIX/공포탐욕지수
            if fg_data is not None and len(fg_data) > 0:
                self._render_fear_greed_indicator(fg_data)
            
            # 금 가격
            if additional_data.get('gold') is not None and len(additional_data['gold']) > 0:
                self._render_gold_indicator(additional_data['gold'])
            
            # 원유가격
            if fred_additional and 'oil_price' in fred_additional:
                self._render_oil_indicator(fred_additional['oil_price'])
            
            # 달러인덱스
            if fred_additional and 'dollar_index' in fred_additional:
                self._render_dollar_index_indicator(fred_additional['dollar_index'])
    
    def _render_additional_indicators(self, fred_macro):
        """Render additional indicators like retail sales and housing market"""
        # 소매판매 지수 추가
        if fred_macro and 'retail_sales' in fred_macro:
            self._render_retail_sales_indicator(fred_macro['retail_sales'])
        
        # 주택시장 지수
        if fred_macro and 'housing_market' in fred_macro:
            self._render_housing_market_indicator(fred_macro['housing_market'])
    
    def _render_correlation_analysis(self, fg_data, pc_data, additional_data, fred_macro, fred_additional):
        """Render correlation analysis section"""
        from streamlit_app import sanitize_log_message
        
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
            
            # Collect data from various sources
            self._collect_correlation_data(
                correlation_data_dict, data_sources, fred_macro, fred_additional, 
                fg_data, pc_data, additional_data
            )
            
            # 데이터 검증 및 정제
            valid_data = self._validate_correlation_data(correlation_data_dict)
            
            if len(valid_data) >= 3:
                self._render_correlation_results(valid_data, data_sources)
            else:
                self._render_insufficient_data_message(valid_data)
                
        except Exception as e:
            error_msg = sanitize_log_message(str(e))
            self._render_correlation_error(error_msg)
    
    def _render_update_time(self):
        """Render last update time"""
        from streamlit_app import get_kst_now
        
        st.markdown("---")
        st.markdown(f"**📅 마지막 업데이트:** {get_kst_now().strftime('%Y-%m-%d %H:%M:%S KST')}")
        st.markdown("**💡 참고:** 실제 거래 전 공식 데이터를 확인하시기 바랍니다.")
    
    # Individual indicator rendering methods
    def _render_gdp_indicator(self, gdp_data):
        """Render GDP indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, gdp_growth_rate)
            
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
    
    def _render_manufacturing_indicator(self, manufacturing_data):
        """Render manufacturing indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, manufacturing_growth)
            
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
    
    def _render_cpi_indicator(self, cpi_data):
        """Render CPI inflation indicator"""
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
                from ..utils.chart_utils import ChartUtils
                fig = ChartUtils.add_crisis_markers_to_chart(fig, inflation_rate)
                
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
    
    # Additional rendering methods would continue here...
    # For brevity, I'll include the core data fetching methods
    
    def _render_unemployment_indicator(self, unemployment_data):
        """Render unemployment indicator"""
        if not unemployment_data.empty:
            current_unemployment = unemployment_data.iloc[-1]
            prev_unemployment = unemployment_data.iloc[-2] if len(unemployment_data) > 1 else current_unemployment
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
                x=unemployment_data.index,
                y=unemployment_data.values,
                mode='lines+markers',
                name='Unemployment Rate',
                line=dict(color=unemployment_color, width=2),
                marker=dict(size=4)
            ))
            
            # 주요 경제 위기 시점 표시
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, unemployment_data)
            
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
    
    def _render_yield_curve_indicator(self, yield_data):
        """Render yield curve indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, yield_data)
            
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
    
    def _render_federal_rate_indicator(self, fed_rate):
        """Render federal rate indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, fed_rate)
            
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
    
    def _render_debt_indicators(self, fred_macro):
        """Render debt indicators"""
        debt_data = fred_macro['total_debt']
        gdp_data = fred_macro.get('gdp')
        
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
            
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, debt_in_trillions)
            
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
    
    def _render_m2_indicator(self, m2_data):
        """Render M2 money supply indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, m2_growth)
            
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
    
    def _render_high_yield_spread_indicator(self, high_yield_data):
        """Render high yield spread indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, high_yield_data)
            
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
    
    def _render_put_call_ratio_indicator(self, pc_data):
        """Render Put/Call ratio indicator"""
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
    
    def _render_fear_greed_indicator(self, fg_data):
        """Render Fear & Greed index indicator"""
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
        from ..utils.chart_utils import ChartUtils
        fig = ChartUtils.add_crisis_markers_to_chart(fig, fg_data['Fear_Greed'], date_column=fg_data['Date'])
        
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
    
    def _render_gold_indicator(self, gold_data):
        """Render gold price indicator"""
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
    
    def _render_oil_indicator(self, oil_data):
        """Render oil price indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, oil_data)
            
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
    
    def _render_dollar_index_indicator(self, dollar_data):
        """Render dollar index indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, dollar_data)
            
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
    
    def _render_retail_sales_indicator(self, retail_data):
        """Render retail sales indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, retail_growth)
            
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
    
    def _render_housing_market_indicator(self, housing_data):
        """Render housing market indicator"""
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
            from ..utils.chart_utils import ChartUtils
            fig = ChartUtils.add_crisis_markers_to_chart(fig, housing_data)
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
            st.caption("💡 2000년부터 장기 데이터. 15% 초과 시 과열, -10% 미만 시 급락 위험")
    
    def _collect_correlation_data(self, correlation_data_dict, data_sources, fred_macro, fred_additional, fg_data, pc_data, additional_data):
        """Collect correlation data from all sources"""
        # FRED 매크로 데이터 (최우선)
        if fred_macro:
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
            for key, data in fred_macro.items():
                if data is not None and len(data) > 10:  # 최소 10개 데이터 포인트
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
        
        if additional_data.get('gold') is not None and len(additional_data['gold']) > 10:
            correlation_data_dict['금가격'] = additional_data['gold']['Gold']
            data_sources['금가격'] = 'Yahoo Finance'
    
    def _validate_correlation_data(self, correlation_data_dict):
        """Validate and clean correlation data"""
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
        
        return valid_data
    
    def _render_correlation_results(self, valid_data, data_sources):
        """Render correlation analysis results"""
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
            self._render_correlation_insights(corr_matrix, data_sources)
    
    def _render_correlation_insights(self, corr_matrix, data_sources):
        """Render correlation analysis insights"""
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
            if source not in source_info:
                source_info[source] = []
            source_info[source].append(name)
        
        for source, indicators in source_info.items():
            st.markdown(f"**{source}:** {len(indicators)}개 지표")
            with st.expander(f"{source} 상세", expanded=False):
                for indicator in indicators:
                    st.write(f"• {indicator}")
        
        # 시장 인사이트
        self._render_market_insights(corr_matrix)
    
    def _render_market_insights(self, corr_matrix):
        """Render market insights based on correlation analysis"""
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
    
    def _render_insufficient_data_message(self, valid_data):
        """Render message when insufficient data for correlation analysis"""
        st.markdown(f"""
        <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 12px; padding: 20px; text-align: center;">
            <h3 style="color: #92400e; margin: 0 0 12px 0;">📊 상관관계 분석 준비 중</h3>
            <p style="color: #92400e; margin: 0;">
                현재 <strong>{len(valid_data)}개</strong> 지표만 사용 가능합니다.<br>
                최소 3개 이상의 지표가 필요하며, FRED API 설정을 확인해보세요.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def _render_correlation_error(self, error_msg):
        """Render correlation analysis error message"""
        st.markdown(f"""
        <div style="background: #fee2e2; border: 1px solid #ef4444; border-radius: 12px; padding: 20px;">
            <h4 style="color: #b91c1c; margin: 0 0 8px 0;">⚠️ 상관관계 분석 오류</h4>
            <p style="color: #b91c1c; margin: 0; font-family: monospace; font-size: 0.9rem;">
                {error_msg}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Additional indicator rendering methods would be implemented here
    # Following the same pattern as the methods above