"""
History Manager UI Component
"""
import streamlit as st
import pandas as pd


class HistoryManager:
    """Handles the display of analysis history and logging"""
    
    def __init__(self):
        pass
    
    def render(self):
        """Render collapsible logging section"""
        from streamlit_app import MAX_LOG_DISPLAY_SIZE
        
        with st.expander("📝 Analysis Logs", expanded=False):
            
            # Create tabs for different log types
            tab1, tab2 = st.tabs(["Messages", "Tool Calls"])
            
            with tab1:
                st.subheader("Recent Messages")
                if st.session_state.message_buffer['messages']:
                    log_container = st.container()
                    with log_container:
                        messages_df = pd.DataFrame([
                            {
                                "Time": msg[0],
                                "Type": msg[1], 
                                "Content": msg[2][:200] + "..." if len(str(msg[2])) > 200 else str(msg[2])
                            }
                            for msg in list(st.session_state.message_buffer['messages'])[-MAX_LOG_DISPLAY_SIZE:]
                        ])
                        st.dataframe(messages_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No messages yet. Start analysis to see logs.")
            
            with tab2:
                st.subheader("Tool Calls")
                if st.session_state.message_buffer['tool_calls']:
                    tool_calls_df = pd.DataFrame([
                        {
                            "Time": call[0],
                            "Tool": call[1],
                            "Arguments": str(call[2])[:100] + "..." if len(str(call[2])) > 100 else str(call[2])
                        }
                        for call in list(st.session_state.message_buffer['tool_calls'])[-MAX_LOG_DISPLAY_SIZE:]
                    ])
                    st.dataframe(tool_calls_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No tool calls yet. Start analysis to see tool usage.")