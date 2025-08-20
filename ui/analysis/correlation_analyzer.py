"""
Correlation Analysis Module
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, List, Optional, Tuple
import logging


class CorrelationAnalyzer:
    """상관관계 분석을 전담하는 클래스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def prepare_correlation_data(self, 
                               fred_macro: Optional[Dict] = None,
                               fred_additional: Optional[Dict] = None,
                               fg_data: Optional[pd.DataFrame] = None,
                               pc_data: Optional[pd.DataFrame] = None,
                               additional_data: Optional[Dict] = None) -> Tuple[Dict, Dict]:
        """상관관계 분석을 위한 데이터 준비"""
        
        correlation_data_dict = {}
        data_sources = {}
        
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
                if data is not None and len(data) > 10:
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
        
        # Yahoo Finance 데이터
        if fg_data is not None and len(fg_data) > 10:
            correlation_data_dict['공포탐욕지수'] = fg_data['Fear_Greed']
            data_sources['공포탐욕지수'] = 'Yahoo Finance'
        
        if pc_data is not None and len(pc_data) > 10:
            correlation_data_dict['풋콜레이쇼'] = pc_data['Put_Call_Ratio']
            data_sources['풋콜레이쇼'] = 'Yahoo Finance'
        
        if additional_data and additional_data.get('gold') is not None and len(additional_data['gold']) > 10:
            correlation_data_dict['금가격'] = additional_data['gold']['Gold']
            data_sources['금가격'] = 'Yahoo Finance'
        
        return correlation_data_dict, data_sources
    
    def validate_and_clean_data(self, correlation_data_dict: Dict) -> Dict:
        """데이터 검증 및 정제"""
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
    
    def create_correlation_matrix(self, valid_data: Dict) -> pd.DataFrame:
        """상관관계 매트릭스 생성"""
        if len(valid_data) < 3:
            return None
            
        # 모든 데이터를 같은 길이로 맞추기
        min_len = min([len(v) for v in valid_data.values()])
        
        # DataFrame 생성 (최신 데이터 기준으로)
        correlation_df = pd.DataFrame({
            k: v.tail(min_len).values for k, v in valid_data.items()
        })
        
        return correlation_df.corr()
    
    def render_data_status(self, valid_data: Dict) -> None:
        """데이터 현황 표시"""
        min_len = min([len(v) for v in valid_data.values()])
        max_len = max([len(v) for v in valid_data.values()])
        
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
    
    def create_correlation_heatmap(self, corr_matrix: pd.DataFrame):
        """상관관계 히트맵 생성"""
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
        
        return fig
    
    def analyze_top_correlations(self, corr_matrix: pd.DataFrame) -> List[Tuple]:
        """강한 상관관계 TOP 5 분석"""
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        corr_pairs = corr_matrix.mask(mask).stack().abs().sort_values(ascending=False)
        
        top_correlations = []
        
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
                
                top_correlations.append({
                    'index': i + 1,
                    'pair': pair,
                    'correlation': original_corr,
                    'strength': strength,
                    'strength_color': strength_color,
                    'direction': direction,
                    'direction_color': direction_color
                })
        
        return top_correlations
    
    def render_top_correlations(self, top_correlations: List[Dict]) -> None:
        """상위 상관관계 결과 표시"""
        st.markdown("**🔥 강한 상관관계 TOP 5:**")
        
        for corr_info in top_correlations:
            pair = corr_info['pair']
            st.markdown(f"""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 8px 0;">
                <div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 4px;">
                    {corr_info['index']}. {pair[0][:15]}{'...' if len(pair[0]) > 15 else ''} ↔ {pair[1][:15]}{'...' if len(pair[1]) > 15 else ''}
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: {corr_info['strength_color']}; font-weight: 600; font-size: 0.85rem;">
                        {corr_info['strength']} ({corr_info['correlation']:.3f})
                    </span>
                    <span style="color: {corr_info['direction_color']}; font-size: 0.8rem;">
                        {corr_info['direction']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def render_data_sources(self, data_sources: Dict, valid_data: Dict) -> None:
        """데이터 출처 정보 표시"""
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
    
    def generate_market_insights(self, corr_matrix: pd.DataFrame) -> List[str]:
        """시장 인사이트 생성"""
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
        
        return insights
    
    def render_market_insights(self, insights: List[str]) -> None:
        """시장 인사이트 표시"""
        st.markdown("### 💡 시장 인사이트")
        
        if insights:
            for insight in insights:
                st.markdown(f"• {insight}")
        else:
            st.markdown("• 📈 현재 데이터로는 명확한 패턴 식별 어려움")
            st.markdown("• 🔄 더 많은 데이터 수집 후 재분석 권장")
    
    def render_insufficient_data_warning(self, valid_data_count: int) -> None:
        """데이터 부족 경고 표시"""
        st.markdown(f"""
        <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 12px; padding: 20px; text-align: center;">
            <h3 style="color: #92400e; margin: 0 0 12px 0;">📊 상관관계 분석 준비 중</h3>
            <p style="color: #92400e; margin: 0;">
                현재 <strong>{valid_data_count}개</strong> 지표만 사용 가능합니다.<br>
                최소 3개 이상의 지표가 필요하며, FRED API 설정을 확인해보세요.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_correlation_analysis(self, 
                                  fred_macro: Optional[Dict] = None,
                                  fred_additional: Optional[Dict] = None,
                                  fg_data: Optional[pd.DataFrame] = None,
                                  pc_data: Optional[pd.DataFrame] = None,
                                  additional_data: Optional[Dict] = None) -> None:
        """통합 상관관계 분석 렌더링"""
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, var(--primary-600), var(--primary-700)); padding: 20px 24px; border-radius: 20px; margin: 24px 0; box-shadow: 0 8px 32px rgba(14, 165, 233, 0.15);">
            <span style="color: white; font-weight: bold; font-size: 18px;">🔗 지표간 상관관계 분석</span>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">다양한 경제지표들의 상호관계를 분석하여 시장 동향을 파악합니다</p>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            # 데이터 준비
            correlation_data_dict, data_sources = self.prepare_correlation_data(
                fred_macro, fred_additional, fg_data, pc_data, additional_data
            )
            
            # 데이터 검증 및 정제
            valid_data = self.validate_and_clean_data(correlation_data_dict)
            
            if len(valid_data) >= 3:
                # 데이터 현황 표시
                self.render_data_status(valid_data)
                
                # 상관관계 매트릭스 생성
                corr_matrix = self.create_correlation_matrix(valid_data)
                
                # 두 열로 나누어 표시
                corr_col1, corr_col2 = st.columns([1.2, 0.8])
                
                with corr_col1:
                    st.markdown("### 📈 상관관계 히트맵")
                    heatmap_fig = self.create_correlation_heatmap(corr_matrix)
                    st.plotly_chart(heatmap_fig, use_container_width=True)
                
                with corr_col2:
                    st.markdown("### 🔍 주요 분석 결과")
                    
                    # 강한 상관관계 TOP 5
                    top_correlations = self.analyze_top_correlations(corr_matrix)
                    self.render_top_correlations(top_correlations)
                    
                    # 데이터 출처 정보
                    self.render_data_sources(data_sources, valid_data)
                    
                    # 시장 인사이트
                    insights = self.generate_market_insights(corr_matrix)
                    self.render_market_insights(insights)
            
            else:
                self.render_insufficient_data_warning(len(valid_data))
                
        except Exception as e:
            st.error(f"상관관계 분석 중 오류 발생: {str(e)}")
            self.logger.error(f"Correlation analysis error: {str(e)}")