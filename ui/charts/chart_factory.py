"""
Chart Factory Module for creating various financial charts
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Optional, Dict, List
import logging
from ..utils.chart_utils import ChartUtils


class ChartFactory:
    """차트 생성을 전담하는 팩토리 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chart_utils = ChartUtils()
    
    def create_price_chart(self, data: pd.DataFrame, symbol: str):
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
        x_axis = data['Date'] if 'Date' in data.columns else data.index
        
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
            margin=dict(l=20, r=20, t=60, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            dragmode='pan',
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True)
        )
        
        return fig

    def create_macd_chart(self, data: pd.DataFrame, symbol: str):
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
        x_axis = valid_data['Date'] if 'Date' in valid_data.columns else valid_data.index
        
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
            margin=dict(l=20, r=20, t=60, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            dragmode='pan',
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True)
        )
        
        return fig

    def create_rsi_chart(self, data: pd.DataFrame, symbol: str):
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
        x_axis = valid_data['Date'] if 'Date' in valid_data.columns else valid_data.index
        
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
            margin=dict(l=20, r=20, t=60, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            dragmode='pan',
            xaxis=dict(fixedrange=True)
        )
        
        return fig

    def create_atr_chart(self, data: pd.DataFrame, symbol: str):
        """ATR 차트 생성"""
        if data is None or 'atr' not in data.columns:
            return None
        
        fig = go.Figure()
        
        # X축 데이터 결정
        x_axis = data['Date'] if 'Date' in data.columns else data.index
        
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
            margin=dict(l=20, r=20, t=60, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            dragmode='pan',
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True)
        )
        
        return fig

    def create_volume_analysis_chart(self, data: pd.DataFrame, symbol: str):
        """거래량 분석 차트"""
        if data is None or 'Volume' not in data.columns or 'Close' not in data.columns:
            return None
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.4],
            subplot_titles=[f'{symbol} 거래량 vs 가격', '거래량 이동평균']
        )
        
        # X축 데이터 결정
        x_axis = data['Date'] if 'Date' in data.columns else data.index
        
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
            margin=dict(l=20, r=20, t=60, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            dragmode='pan'
        )
        
        # 서브플롯의 각 축에 대해 고정 범위 설정 (줌 비활성화)
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        
        return fig
    
    def create_economic_indicator_chart(self, 
                                     data: pd.Series, 
                                     title: str, 
                                     chart_type: str = 'line',
                                     color: str = 'blue',
                                     fill: bool = False,
                                     add_crisis_markers: bool = True) -> go.Figure:
        """경제 지표 차트 생성 (범용)"""
        
        fig = go.Figure()
        
        if chart_type == 'line':
            trace = go.Scatter(
                x=data.index,
                y=data.values,
                mode='lines',
                name=title,
                line=dict(color=color, width=2)
            )
            
            if fill:
                trace.update(
                    fill='tozeroy',
                    fillcolor=f'rgba({int(color[1:3], 16) if color.startswith("#") else 0}, '
                             f'{int(color[3:5], 16) if color.startswith("#") else 0}, '
                             f'{int(color[5:7], 16) if color.startswith("#") else 255}, 0.1)'
                )
        
        elif chart_type == 'bar':
            colors = ['green' if x >= 0 else 'red' for x in data.values]
            trace = go.Bar(
                x=data.index,
                y=data.values,
                name=title,
                marker_color=colors
            )
        
        fig.add_trace(trace)
        
        # 경제 위기 시점 마커 추가
        if add_crisis_markers:
            fig = ChartUtils.add_crisis_markers_to_chart(fig, data)
        
        fig.update_layout(
            title=title,
            height=300,
            showlegend=True,
            **ChartUtils.get_standard_layout_config()
        )
        
        return fig
    
    def create_metric_badge(self, label: str, value: str, change: str = "", color: str = "blue") -> str:
        """지표 뱃지 HTML 생성"""
        return f"""
        <div style="background: linear-gradient(90deg, {color}, #64748b); padding: 8px 12px; border-radius: 20px; margin: 8px 0;">
            <span style="color: white; font-weight: bold; font-size: 14px;">{label}</span>
            <span style="color: white; font-size: 12px; margin-left: 10px;">{value} {change}</span>
        </div>
        """
    
    def get_mobile_chart_config(self) -> Dict:
        """모바일 최적화 차트 설정"""
        return ChartUtils.get_mobile_chart_config()