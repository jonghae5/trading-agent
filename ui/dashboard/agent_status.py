"""
Agent Status Display UI Component
"""
import streamlit as st


class AgentStatusDisplay:
    """Handles the display of agent status monitoring"""
    
    @staticmethod
    def render():
        """Render agent status monitoring in column format"""
        st.markdown("### 🧑‍💻 Agent Status")
        
        # Group agents by team with better icons in flow order
        teams = {
            "📈 분석팀": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
            "🔬 리서치팀": ["Bull Researcher", "Bear Researcher", "Research Manager"],  
            "💼 트레이딩팀": ["Trader"],
            "🛡️ 리스크관리": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
            "📊 포트폴리오": ["Portfolio Manager"]
        }
        
        # Create columns for teams
        cols = st.columns(len(teams))
        
        for col_idx, (team_name, agents) in enumerate(teams.items()):
            with cols[col_idx]:
                st.markdown(f"**{team_name}**")
                
                # Create a container for the flow within each column
                flow_html = ""
                
                for agent in agents:
                    status = st.session_state.message_buffer['agent_status'].get(agent, "pending")
                    
                    if status == "pending":
                        status_class = "status-pending"
                        emoji = "⏳"
                    elif status == "in_progress":
                        status_class = "status-in-progress" 
                        emoji = "🔄"
                    elif status == "completed":
                        status_class = "status-completed"
                        emoji = "✅"
                    else:
                        status_class = "status-error"
                        emoji = "❌"
                    
                    # Very short agent names for compact display
                    agent_display = agent.replace(" Analyst", "").replace(" Researcher", "Res").replace(" Manager", "Mgr")
                    
                    flow_html += f"""
                    <div style="margin-bottom: 0.3rem;">
                        <span class="agent-status {status_class}">
                            {emoji} {agent_display}
                        </span>
                    </div>
                    """
                
                st.markdown(flow_html, unsafe_allow_html=True)