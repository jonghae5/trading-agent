"""
Report History Module for managing and displaying analysis report history
"""
import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import pytz
from typing import Optional, Dict, Any
import logging


class ReportHistory:
    """Report history management and visualization class"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # Time zone settings
        self.KST = pytz.timezone('Asia/Seoul')
    
    def get_kst_now(self) -> datetime.datetime:
        """현재 KST 시간을 반환 (timezone-aware)"""
        return datetime.datetime.now(self.KST)

    def get_kst_date(self):
        """현재 KST 날짜를 date 객체로 반환"""
        return self.get_kst_now().date()
    
    def render_filter_controls(self) -> tuple:
        """필터 컨트롤 렌더링"""
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            start_date = st.date_input(
                "📅 시작 날짜",
                value=self.get_kst_date() - datetime.timedelta(days=30),  # 30일 전
                help="분석 시작 날짜 필터"
            )
        
        with col2:
            end_date = st.date_input(
                "📅 종료 날짜", 
                value=self.get_kst_date(),
                help="분석 종료 날짜 필터"
            )
        
        with col3:
            limit = st.selectbox("📄 표시 개수", options=[10, 25, 50, 100], index=1)
        
        return start_date, end_date, limit
    
    def get_filtered_sessions(self, username: str, start_date: datetime.date, 
                            end_date: datetime.date, limit: int) -> list:
        """필터된 분석 세션 목록 반환"""
        sessions = self.db_manager.get_user_analysis_sessions(username, limit=limit)
        
        # 날짜 필터 적용
        if start_date and end_date:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            sessions = [s for s in sessions if start_str <= s['analysis_date'][:10] <= end_str]
        
        return sessions
    
    def render_sessions_table(self, sessions: list) -> None:
        """세션 히스토리 테이블 렌더링"""
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
    
    def render_session_selector(self, sessions: list) -> Optional[str]:
        """세션 선택기 렌더링"""
        st.markdown("#### 🔍 Detailed Report View")
        
        # 세션 선택
        session_options = {f"{s['ticker']} - {s['analysis_date'][:16]} ({s['session_id'][:8]})": s['session_id'] 
                          for s in sessions}
        
        if not session_options:
            return None
            
        selected_display = st.selectbox(
            "📊 Select Report to View:",
            options=list(session_options.keys()),
            help="View detailed analysis report"
        )
        
        return session_options[selected_display]
    
    def render_action_buttons(self) -> tuple:
        """액션 버튼들 렌더링"""
        action_col1, action_col2 = st.columns([1, 1])
        
        with action_col1:
            load_report = st.button("📖 Load Report", type="primary")
        
        with action_col2:
            delete_report = st.button("🗑️ Delete Report", type="secondary", 
                                    help="⚠️ 이 작업은 되돌릴 수 없습니다!")
        
        return load_report, delete_report
    
    def handle_delete_confirmation(self, selected_session_id: str, selected_display: str, 
                                 current_username: str) -> bool:
        """삭제 확인 처리"""
        # 삭제 상태 관리를 위한 session state 초기화
        if 'show_delete_confirm' not in st.session_state:
            st.session_state.show_delete_confirm = False
        if 'delete_target_session' not in st.session_state:
            st.session_state.delete_target_session = None
        
        # 삭제 확인 창 표시
        if st.session_state.show_delete_confirm:
            st.warning("⚠️ **정말 이 리포트를 삭제하시겠습니까?**")
            st.write(f"**삭제 대상:** {st.session_state.delete_target_display}")
            
            confirm_col1, confirm_col2 = st.columns([1, 1])
            
            with confirm_col1:
                if st.button("✅ 네, 삭제합니다", key="confirm_delete_final"):
                    try:
                        success = self.db_manager.delete_analysis_session(
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
            
            return False  # 삭제 확인 중이므로 다른 작업 차단
        
        return True  # 정상 진행
    
    def render_session_info(self, session_info: Dict) -> None:
        """세션 정보 렌더링"""
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
    
    def render_agent_executions(self, agent_executions: list) -> None:
        """에이전트 실행 상태 렌더링"""
        if not agent_executions:
            return
            
        st.markdown("##### 🤖 Agent Execution Status")
        agent_df_data = []
        for agent in agent_executions:
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
    
    def render_report_sections(self, report_sections: list) -> None:
        """리포트 섹션들 렌더링"""
        if not report_sections:
            return
            
        st.markdown("##### 📄 Analysis Reports")
        
        # 섹션별로 그룹화
        sections_by_type = {}
        for section in report_sections:
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
    
    def render_export_options(self, selected_session_id: str, session_info: Dict, 
                            report_sections: list, section_titles: Dict) -> None:
        """리포트 내보내기 옵션 렌더링"""
        st.markdown("##### ⬇️ Export Options")
        col1, col2 = st.columns(2)
        
        with col1:
            # JSON 내보내기
            json_data = self.db_manager.export_session_to_json(selected_session_id)
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
            
            for section in report_sections:
                title = section_titles.get(section['section_type'], section['section_type'])
                md_content += f"## {title}\n\n{section['content']}\n\n"
            
            st.download_button(
                label="📝 Download as Markdown",
                data=md_content,
                file_name=f"report_{session_info['ticker']}_{selected_session_id[:8]}.md",
                mime="text/markdown"
            )
    
    def render_statistics(self, sessions: list) -> None:
        """통계 정보 렌더링"""
        if not sessions:
            return
            
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
    
    def render(self) -> None:
        """리포트 히스토리 메인 렌더링 함수"""
        st.markdown("### 📚 분석 리포트 히스토리")
        
        try:
            # 현재 사용자 확인
            if not st.session_state.get('authenticated') or not st.session_state.get('username'):
                st.warning("로그인이 필요합니다.")
                return
            
            current_username = st.session_state.username
            
            # 필터 옵션
            start_date, end_date, limit = self.render_filter_controls()
            
            # 분석 세션 조회 (사용자별 세션)
            sessions = self.get_filtered_sessions(current_username, start_date, end_date, limit)
            
            if not sessions:
                st.info("📭 No analysis reports found. Start your first analysis!")
                return
            
            # 히스토리 테이블 표시
            self.render_sessions_table(sessions)
            
            # 상세 리포트 보기
            selected_session_id = self.render_session_selector(sessions)
            
            if selected_session_id:
                # 액션 버튼들
                load_report, delete_report = self.render_action_buttons()
                
                # 삭제 확인 및 처리
                if delete_report:
                    st.session_state.show_delete_confirm = True
                    st.session_state.delete_target_session = selected_session_id
                    selected_display = next(key for key, value in 
                                          {f"{s['ticker']} - {s['analysis_date'][:16]} ({s['session_id'][:8]})": s['session_id'] 
                                           for s in sessions}.items() if value == selected_session_id)
                    st.session_state.delete_target_display = selected_display
                    st.rerun()
                
                # 삭제 확인 처리
                can_proceed = self.handle_delete_confirmation(
                    selected_session_id, 
                    st.session_state.get('delete_target_display', ''), 
                    current_username
                )
                
                # 선택된 리포트 표시
                if load_report and can_proceed:
                    with st.spinner("Loading report..."):
                        report_data = self.db_manager.get_session_report(selected_session_id)
                        
                        # 세션 정보 표시
                        session_info = report_data['session_info']
                        self.render_session_info(session_info)
                        
                        # 에이전트 실행 상태
                        self.render_agent_executions(report_data['agent_executions'])
                        
                        # 리포트 섹션들
                        self.render_report_sections(report_data['report_sections'])
                        
                        # 리포트 내보내기
                        section_titles = {
                            "market_report": "📈 Market Analysis",
                            "sentiment_report": "🗣️ Social Sentiment", 
                            "news_report": "📰 News Analysis",
                            "fundamentals_report": "📊 Fundamentals",
                            "investment_plan": "🎯 Research Decision",
                            "trader_investment_plan": "💼 Trading Plan",
                            "final_trade_decision": "⚖️ Final Decision"
                        }
                        
                        self.render_export_options(
                            selected_session_id, session_info, 
                            report_data['report_sections'], section_titles
                        )
            
            # 통계 정보
            self.render_statistics(sessions)
        
        except Exception as e:
            st.error(f"Error loading report history: {str(e)}")
            st.info("Make sure the database is properly initialized.")
            self.logger.error(f"Report history error: {str(e)}")