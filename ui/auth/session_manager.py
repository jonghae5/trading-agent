"""
Session Management UI Component
"""
import streamlit as st
import logging


class SessionManager:
    """Handles session status display and management"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def render_session_info(self):
        """Render session information in sidebar"""
        session_info = self._get_session_info()
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
            
            return current_user, session_info
        
        return None, None
    
    def render_logout_button(self, current_user):
        """Render logout button and handle logout process"""
        logout_label = f"🚪 Logout ({current_user})" if current_user else "🚪 Logout"
        
        if st.button(logout_label, type="secondary"):
            self._handle_logout(current_user)
    
    def _get_session_info(self):
        """Get current session information"""
        if not st.session_state.authenticated or st.session_state.login_time is None:
            return None
        
        from streamlit_app import get_kst_naive_now
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
    
    def _handle_logout(self, current_user):
        """Handle user logout process"""
        from streamlit_app import clear_session, init_auth_session_state
        import time
        
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
        
        self.logger.info(f"[AUTH] User {logged_out_user} logged out manually - all session data cleared")
        st.success(f"✅ {logged_out_user} logged out successfully!")
        time.sleep(1)  # Brief pause to show message
        st.rerun()