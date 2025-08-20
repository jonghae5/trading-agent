"""
Metrics Display UI Component
"""
import streamlit as st
import time


class MetricsDisplay:
    """Handles the display of analysis metrics"""
    
    @staticmethod
    def render():
        """Render key metrics with custom styling"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(
                MetricsDisplay._create_custom_metric(
                    "🛠️ Tool Calls", 
                    st.session_state.message_buffer['tool_call_count']
                ), 
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                MetricsDisplay._create_custom_metric(
                    "🤖 LLM Calls", 
                    st.session_state.message_buffer['llm_call_count']
                ), 
                unsafe_allow_html=True
            )
        
        with col3:
            reports_count = sum(1 for content in st.session_state.message_buffer['report_sections'].values() if content is not None)
            st.markdown(
                MetricsDisplay._create_custom_metric(
                    "📄 Generated Reports", 
                    reports_count
                ), 
                unsafe_allow_html=True
            )
        
        with col4:
            duration_text = MetricsDisplay._get_duration_text()
            st.markdown(
                MetricsDisplay._create_custom_metric(
                    "⏱️ Duration", 
                    duration_text
                ), 
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _create_custom_metric(label: str, value) -> str:
        """Create custom styled metric"""
        return f"""
        <div style="
            background: linear-gradient(135deg, #f8faff 0%, #ffffff 100%);
            border: 1px solid rgba(66, 165, 245, 0.12);
            padding: 0.3rem 0.4rem;
            border-radius: 10px;
            box-shadow: 0 1px 3px rgba(66, 165, 245, 0.05);
            margin-bottom: 0.5rem;
            min-height: 35px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="
                color: #5f6368;
                font-weight: 500;
                font-size: 0.65rem;
                margin-bottom: 0.05rem;
            ">{label}</div>
            <div style="
                color: #1a73e8;
                font-weight: 600;
                font-size: 0.7rem;
            ">{value}</div>
        </div>
        """
    
    @staticmethod
    def _get_duration_text() -> str:
        """Get duration text for analysis"""
        if st.session_state.message_buffer['analysis_start_time'] and st.session_state.message_buffer['analysis_end_time']:
            duration = st.session_state.message_buffer['analysis_end_time'] - st.session_state.message_buffer['analysis_start_time']
            duration_text = f"{duration:.1f}s"
        elif st.session_state.message_buffer['analysis_start_time']:
            current_duration = time.time() - st.session_state.message_buffer['analysis_start_time']
            duration_text = f"{current_duration:.1f}s"
        else:
            duration_text = "0s"
        
        return duration_text