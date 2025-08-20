"""
Welcome Header UI Component
"""
import streamlit as st


class WelcomeHeader:
    """Renders the welcome header with system architecture"""
    
    @staticmethod
    def render():
        """Render the welcome header"""
        from streamlit_app import to_kst_string, get_kst_now
        
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
        WelcomeHeader._render_architecture_diagram()
    
    @staticmethod
    def _render_architecture_diagram():
        """Render the architecture diagram"""
        try:
            st.image("assets/schema.png", caption="트레이딩 에이전트 시스템 아키텍처", use_container_width=True)
        except Exception as e:
            st.warning(f"아키텍처 다이어그램을 로드할 수 없습니다: {e}")
            st.info("아키텍처 다이어그램이 assets/schema.png 경로에 있는지 확인해주세요.")