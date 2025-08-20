"""
Report Viewer UI Component
"""
import streamlit as st


class ReportViewer:
    """Handles the display of analysis reports with export functionality"""
    
    def __init__(self):
        pass
    
    def render(self):
        """Render reports section with export functionality"""
        st.subheader("📑 Analysis Reports")
        
        report_sections = st.session_state.message_buffer['report_sections']
        
        if any(content for content in report_sections.values()):
            
            # Create tabs for different reports
            tabs = []
            tab_names = []
            
            section_titles = {
                "market_report": "Market Analysis",
                "sentiment_report": "Social Sentiment", 
                "news_report": "News Analysis",
                "fundamentals_report": "Fundamentals Analysis",
                "investment_plan": "Research Team Decision",
                "trader_investment_plan": "Trading Team Plan",
                "final_trade_decision": "Portfolio Management Decision"
            }
            
            for section, content in report_sections.items():
                if content:
                    tab_names.append(section_titles.get(section, section.title()))
                    tabs.append(section)
            
            if tabs:
                selected_tabs = st.tabs(tab_names)
                
                for tab, section in zip(selected_tabs, tabs):
                    with tab:
                        content = report_sections[section]
                        st.markdown(content)
            
            # Only show export buttons if analysis is not running
            if not st.session_state.analysis_running:
                st.subheader("⬇️ Export Reports")
                
                # Individual report downloads
                for section, content in report_sections.items():
                    if content:
                        title = section_titles.get(section, section.title())
                        report_filename = f"{section}_{st.session_state.config['ticker']}_{st.session_state.config['analysis_date']}.md"
                        st.download_button(
                            label=f"📄 Download {title}",
                            data=content,
                            file_name=report_filename,
                            mime="text/markdown",
                            key=f"download_{section}"
                        )
                
                # Complete report download
                complete_report = f"# Complete Analysis Report - {st.session_state.config['ticker']}\n"
                complete_report += f"**Analysis Date:** {st.session_state.config['analysis_date']}\n\n"
                
                for section, content in report_sections.items():
                    if content:
                        title = section_titles.get(section, section.title())
                        complete_report += f"## {title}\n\n{content}\n\n"
                
                complete_filename = f"complete_report_{st.session_state.config['ticker']}_{st.session_state.config['analysis_date']}.md"
                st.download_button(
                    label="📋 Download Complete Report",
                    data=complete_report,
                    file_name=complete_filename,
                    mime="text/markdown",
                    key="download_complete"
                )
            else:
                st.info("📥 Export options will be available after analysis completes")
        else:
            st.info("No reports generated yet. Start analysis to see reports.")