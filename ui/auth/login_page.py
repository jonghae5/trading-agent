"""
Login Page UI Component
"""
import streamlit as st
import datetime
import time
import logging


class LoginPage:
    """Handles login page rendering and user authentication"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def render(self):
        """Render the login page"""
        st.markdown("""
        <div class="welcome-header">
            <h1>트레이딩 에이전트 대시보드</h1>
            <h3>보안 인증이 필요합니다</h3>
            <p>계속하려면 인증 키를 입력해주세요</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check if user is blocked
        if self._is_blocked():
            self._show_blocked_message()
            return
        
        # Show remaining attempts
        self._show_remaining_attempts()
        
        # Login form
        self._render_login_form()
        
        # Instructions
        self._render_instructions()
    
    def _is_blocked(self):
        """Check if user is currently blocked from logging in"""
        if st.session_state.blocked_until is None:
            return False
        
        from streamlit_app import get_kst_naive_now
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
    
    def _show_blocked_message(self):
        """Show blocked message with remaining time"""
        from streamlit_app import get_kst_naive_now
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
    
    def _show_remaining_attempts(self):
        """Show remaining login attempts"""
        remaining_attempts = 5 - st.session_state.login_attempts
        if st.session_state.login_attempts > 0:
            if remaining_attempts > 0:
                st.warning(f"⚠️ {remaining_attempts}번의 시도가 남았습니다")
    
    def _render_login_form(self):
        """Render the login form"""
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
                    if self.authenticate_user(username, password):
                        st.success(f"✅ 환영합니다, {username}님! 리다이렉트 중...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        remaining = 5 - st.session_state.login_attempts
                        if remaining > 0:
                            st.error(f"❌ 잘못된 인증 정보입니다. {remaining}번의 시도가 남았습니다.")
                        else:
                            st.error("🚫 너무 많은 시도로 인해 30분간 접근이 차단되었습니다.")
    
    def _render_instructions(self):
        """Render usage instructions"""
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
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user with username and password using database"""
        try:
            from streamlit_app import (
                sanitize_log_message, get_kst_naive_now, 
                to_kst_string, get_kst_now, MIN_PASSWORD_LENGTH,
                MAX_LOGIN_ATTEMPTS, BLOCK_DURATION_MINUTES
            )
            
            # Input validation
            if not username or not password:
                return False
            
            # Sanitize inputs to prevent injection
            username = sanitize_log_message(username.strip())
            
            # Basic validation
            if len(username) > 50 or len(password) < MIN_PASSWORD_LENGTH:
                return False
            
            if self.db_manager.verify_user(username, password):
                # 인증 성공 - 세션 생성
                session_id = self.db_manager.create_session(username, duration_hours=1)
                
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.session_id = session_id
                st.session_state.login_attempts = 0
                st.session_state.login_time = get_kst_naive_now()
                st.session_state.blocked_until = None
                
                # URL에 세션 ID 추가 (새로고침 대응)
                st.query_params['session_id'] = session_id
                
                self.logger.info(f"[AUTH] User {username} successfully authenticated at {to_kst_string(get_kst_now())} - session will last 1 hour")
                return True
            else:
                st.session_state.login_attempts += 1
                self.logger.warning(f"[AUTH] Failed login attempt for {username}: {st.session_state.login_attempts}/5")
                
                # 클라이언트 사이드 차단
                if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
                    st.session_state.blocked_until = get_kst_naive_now() + datetime.timedelta(minutes=BLOCK_DURATION_MINUTES)
                    self.logger.warning(f"[AUTH] User blocked for {MAX_LOGIN_ATTEMPTS} failed attempts ({BLOCK_DURATION_MINUTES} minutes)")
                
                return False
        except Exception as e:
            self.logger.error(f"[AUTH] Authentication error for {username}: {e}")
            st.session_state.login_attempts += 1
            return False