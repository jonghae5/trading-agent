import streamlit as st
import datetime
from enum import Enum
from collections import deque
import json
import time
import logging
import sys
import os

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
# .env 파일 로드
load_dotenv()

# ============================================
# 🔒 인증 시스템
# ============================================

# 환경변수에서 AUTH KEY 읽기
AUTH_KEY = os.getenv("STREAMLIT_AUTH_KEY")

if AUTH_KEY is None:
    st.error("🚫 서버에 STREAMLIT_AUTH_KEY 환경변수가 설정되지 않았습니다.")
    st.info("💡 관리자에게 문의하여 인증 키를 설정해달라고 요청하세요.")
    st.stop()

# 세션 상태 초기화
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "fail_count" not in st.session_state:
    st.session_state.fail_count = 0
if "locked" not in st.session_state:
    st.session_state.locked = False

# 잠금 상태 확인
if st.session_state.locked:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; margin: 2rem 0;">
        <h1 style="margin: 0; color: white;">🚫 접근 차단</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">로그인 시도가 5회 초과되어 차단되었습니다.</p>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">브라우저를 재시작하거나 관리자에게 문의하세요.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 인증되지 않은 경우 로그인 화면 표시
if not st.session_state.authenticated:
    st.set_page_config(
        page_title="TradingAgents - Secure Login",
        page_icon="🔒",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # 로그인 화면 스타일
    st.markdown("""
    <style>
    .main > div {
        padding: 2rem 1rem;
        max-width: 500px;
        margin: 0 auto;
    }
    
    .login-container {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 로그인 헤더
    st.markdown("""
    <div class="hero-section">
        <h1 style="margin: 0; font-size: 2.5rem;">🔒 TradingAgents</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">Secure Access Required</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 로그인 폼
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("### 🗝️ Access Key Required")
        st.markdown("인증된 사용자만 TradingAgents 시스템에 접근할 수 있습니다.")
        
        # 실패 횟수 표시
        if st.session_state.fail_count > 0:
            remaining = 5 - st.session_state.fail_count
            st.warning(f"⚠️ 잘못된 키입니다. {remaining}번의 시도가 남았습니다.")
        
        key_input = st.text_input(
            "Access Key", 
            type="password",
            placeholder="인증 키를 입력하세요...",
            help="관리자로부터 받은 인증 키를 입력하세요"
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_button = st.button("🚀 Login", type="primary", use_container_width=True)

        if login_button:
            if key_input == AUTH_KEY:
                st.session_state.authenticated = True
                st.session_state.fail_count = 0
                st.success("✅ 인증 성공! TradingAgents 시스템에 접근합니다...")
                time.sleep(1)  # 잠시 대기
                st.rerun()
            else:
                st.session_state.fail_count += 1
                remaining = 5 - st.session_state.fail_count
                if remaining > 0:
                    st.error(f"❌ 잘못된 Access Key입니다. {remaining}번의 시도가 남았습니다.")
                else:
                    st.session_state.locked = True
                    st.error("🚫 5회 연속 실패로 접근이 차단되었습니다!")
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 도움말 정보
        st.markdown("---")
        st.info("💡 **도움말**: Access Key가 없다면 관리자에게 문의하세요.")
        st.markdown("""
        **보안 정책:**
        - 5회 연속 실패 시 접근이 차단됩니다
        - 인증된 사용자만 시스템에 접근할 수 있습니다
        - 세션은 브라우저 종료 시 만료됩니다
        """)
    
    st.stop()

# ============================================
# 🎉 인증 성공 - 메인 애플리케이션 시작
# ============================================

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('streamlit_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

# AnalystType enum definition (from CLI)
class AnalystType(str, Enum):
    market = "market"
    social = "social"
    news = "news"
    fundamentals = "fundamentals"

# MessageBuffer class adapted from CLI version for real-time tracking
class MessageBuffer:
    def __init__(self, max_length=100):
        self.messages = deque(maxlen=max_length)
        self.tool_calls = deque(maxlen=max_length)
        self.current_report = None
        self.final_report = None
        self.agent_status = {
            # Analyst Team
            "Market Analyst": "pending",
            "Social Analyst": "pending",
            "News Analyst": "pending",
            "Fundamentals Analyst": "pending",
            # Research Team
            "Bull Researcher": "pending",
            "Bear Researcher": "pending",
            "Research Manager": "pending",
            # Trading Team
            "Trader": "pending",
            # Risk Management Team
            "Risky Analyst": "pending",
            "Neutral Analyst": "pending",
            "Safe Analyst": "pending",
            # Portfolio Management Team
            "Portfolio Manager": "pending",
        }
        self.current_agent = None
        self.report_sections = {
            "market_report": None,
            "sentiment_report": None,
            "news_report": None,
            "fundamentals_report": None,
            "investment_plan": None,
            "trader_investment_plan": None,
            "final_trade_decision": None,
        }

    def add_message(self, message_type, content):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.messages.append((timestamp, message_type, content))
        # Log to console and file
        logger.info(f"[{message_type}] {content[:500]}{'...' if len(str(content)) > 500 else ''}")
        print(f"🔹 [{timestamp}] {message_type}: {content[:500]}{'...' if len(str(content)) > 500 else ''}")
        sys.stdout.flush()

    def add_tool_call(self, tool_name, args):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.tool_calls.append((timestamp, tool_name, args))
        # Log tool calls
        args_str = str(args)[:100] + "..." if len(str(args)) > 100 else str(args)
        logger.info(f"[TOOL] {tool_name}({args_str})")
        print(f"🔧 [{timestamp}] TOOL: {tool_name}({args_str})")
        sys.stdout.flush()

    def update_agent_status(self, agent, status):
        if agent in self.agent_status:
            old_status = self.agent_status[agent]
            self.agent_status[agent] = status
            self.current_agent = agent
            # Log status changes
            if old_status != status:
                logger.info(f"[STATUS] {agent}: {old_status} → {status}")
                print(f"📊 {agent}: {old_status} → {status}")
                sys.stdout.flush()
                
                # Add status change directly to messages (without triggering logging)
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                status_message = f"Agent Status Change: {agent} ({old_status} → {status})"
                self.messages.append((timestamp, "📊 Status", status_message))

    def update_report_section(self, section_name, content):
        if section_name in self.report_sections:
            self.report_sections[section_name] = content
            self._update_current_report()
            # Log report updates
            content_preview = content[:500] + "..." if len(str(content)) > 500 else str(content)
            logger.info(f"[REPORT] {section_name} updated: {content_preview}")
            print(f"📝 REPORT: {section_name} generated")
            sys.stdout.flush()

    def _update_current_report(self):
        # For the panel display, only show the most recently updated section
        latest_section = None
        latest_content = None

        # Find the most recently updated section
        for section, content in self.report_sections.items():
            if content is not None:
                latest_section = section
                latest_content = content
               
        if latest_section and latest_content:
            # Format the current section for display
            section_titles = {
                "market_report": "Market Analysis",
                "sentiment_report": "Social Sentiment",
                "news_report": "News Analysis",
                "fundamentals_report": "Fundamentals Analysis",
                "investment_plan": "Research Team Decision",
                "trader_investment_plan": "Trading Team Plan",
                "final_trade_decision": "Portfolio Management Decision",
            }
            self.current_report = (
                f"### {section_titles[latest_section]}\n{latest_content}"
            )

        # Update the final complete report
        self._update_final_report()

    def _update_final_report(self):
        report_parts = []

        # Analyst Team Reports
        if any(
            self.report_sections[section]
            for section in [
                "market_report",
                "sentiment_report",
                "news_report",
                "fundamentals_report",
            ]
        ):
            report_parts.append("## Analyst Team Reports")
            if self.report_sections["market_report"]:
                report_parts.append(
                    f"### Market Analysis\n{self.report_sections['market_report']}"
                )
            if self.report_sections["sentiment_report"]:
                report_parts.append(
                    f"### Social Sentiment\n{self.report_sections['sentiment_report']}"
                )
            if self.report_sections["news_report"]:
                report_parts.append(
                    f"### News Analysis\n{self.report_sections['news_report']}"
                )
            if self.report_sections["fundamentals_report"]:
                report_parts.append(
                    f"### Fundamentals Analysis\n{self.report_sections['fundamentals_report']}"
                )

        # Research Team Reports
        if self.report_sections["investment_plan"]:
            report_parts.append("## Research Team Decision")
            report_parts.append(f"{self.report_sections['investment_plan']}")

        # Trading Team Reports
        if self.report_sections["trader_investment_plan"]:
            report_parts.append("## Trading Team Plan")
            report_parts.append(f"{self.report_sections['trader_investment_plan']}")

        # Portfolio Management Decision
        if self.report_sections["final_trade_decision"]:
            report_parts.append("## Portfolio Management Decision")
            report_parts.append(f"{self.report_sections['final_trade_decision']}")

        self.final_report = "\n\n".join(report_parts) if report_parts else None

    def get_all_messages(self):
        """Get combined messages and tool calls sorted by timestamp"""
        all_messages = []
        
        # Add tool calls
        for timestamp, tool_name, args in self.tool_calls:
            if isinstance(args, str) and len(args) > 500:
                args = args[:497] + "..."
            all_messages.append((timestamp, "Tool", f"{tool_name}: {args}"))

        # Add regular messages
        for timestamp, msg_type, content in self.messages:
            content_str = self._format_content(content)
            if len(content_str) > 500:
                content_str = content_str[:497] + "..."
            all_messages.append((timestamp, msg_type, content_str))

        # Sort by timestamp
        all_messages.sort(key=lambda x: x[0])
        return all_messages

    def _format_content(self, content):
        """Format content to string handling various formats"""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item.get('type') == 'tool_use':
                        text_parts.append(f"[Tool: {item.get('name', 'unknown')}]")
                else:
                    text_parts.append(str(item))
            return ' '.join(text_parts)
        else:
            return str(content)

# Global message buffer instance
if 'message_buffer' not in st.session_state:
    st.session_state.message_buffer = MessageBuffer()

# Initialize session state with MessageBuffer integration
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

# Helper function to update research team status
def update_research_team_status(status):
    """Update status for all research team members and trader."""
    research_team = ["Bull Researcher", "Bear Researcher", "Research Manager", "Trader"]
    for agent in research_team:
        st.session_state.message_buffer.update_agent_status(agent, status)

def main():
    st.set_page_config(
        page_title="TradingAgents - Multi-Agent Financial Analysis",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="auto"
    )
    
    # 🔒 인증된 사용자용 로그아웃 버튼 (사이드바 상단에 배치)
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 사용자 정보")
        st.success("✅ 인증된 사용자로 로그인됨")
        
        if st.button("🚪 로그아웃", type="secondary", use_container_width=True):
            # 세션 상태 초기화
            st.session_state.authenticated = False
            st.session_state.fail_count = 0
            st.session_state.locked = False
            # 분석 상태도 초기화
            st.session_state.analysis_complete = False
            st.session_state.analysis_results = None
            if 'message_buffer' in st.session_state:
                st.session_state.message_buffer = MessageBuffer()
            st.success("🔓 로그아웃되었습니다. 페이지를 새로고침합니다...")
            time.sleep(1)
            st.rerun()
        
        st.markdown("---")
    
    # Custom CSS for mobile responsiveness and modern design
    st.markdown("""
    <style>
    /* Mobile-first responsive design */
    .main > div {
        padding: 1rem;
    }
    
    /* Custom styling for better mobile experience */
    .stSelectbox, .stTextInput, .stDateInput {
        margin-bottom: 1rem;
    }
    
    /* Responsive sidebar */
    @media (max-width: 768px) {
        .css-1d391kg {
            padding: 0.5rem;
        }
        
        .stButton > button {
            width: 100%;
            margin: 0.5rem 0;
        }
        
        .element-container {
            margin-bottom: 0.5rem;
        }
    }
    
    /* Modern card styling */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .status-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Responsive tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap;
        }
        
        .stTabs [data-baseweb="tab"] {
            min-width: calc(50% - 0.25rem);
            margin-bottom: 0.5rem;
        }
    }
    
    /* Loading animation */
    .loading-spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 0 auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Beautiful gradient backgrounds */
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    
    /* Improved expander styling */
    .streamlit-expanderHeader {
        background-color: #f8f9fa;
        border-radius: 5px;
    }
    
    /* Mobile-friendly font sizes */
    @media (max-width: 768px) {
        h1 {
            font-size: 1.8rem !important;
        }
        
        h2 {
            font-size: 1.4rem !important;
        }
        
        h3 {
            font-size: 1.2rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Modern Header with responsive design
    st.markdown("""
    <div class="hero-section">
        <h1 style="margin: 0; font-size: 2.5rem;">📈 TradingAgents</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">Multi-Agent LLM Financial Trading Framework</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main content area - configuration moved to main screen for mobile compatibility
    st.subheader("🔧 Analysis Configuration")
    
    # Create expandable configuration section
    with st.expander("⚙️ Configure Analysis Settings", expanded=not st.session_state.analysis_complete):
        
        # Step 1: Ticker Symbol
        ticker = st.text_input("Ticker Symbol", value="SPY", help="Enter the stock ticker to analyze")
        
        # Step 2: Analysis Date
        analysis_date = st.date_input(
            "Analysis Date", 
            value=datetime.date.today(),
            max_value=datetime.date.today(),
            help="Select the date for analysis (cannot be in the future)"
        )
        
        # Step 3: Select Analysts with better mobile layout
        st.subheader("👥 Select Analysts")
        selected_analysts = []
        
        # Use columns for better mobile layout
        col1, col2 = st.columns(2)
        
        with col1:
            if st.checkbox("📈 Market", value=True, key="market"):
                selected_analysts.append(AnalystType.market)
            if st.checkbox("📰 News", value=True, key="news"):
                selected_analysts.append(AnalystType.news)
        
        with col2:
            if st.checkbox("💬 Social", value=True, key="social"):
                selected_analysts.append(AnalystType.social)
            if st.checkbox("🏢 Fundamentals", value=True, key="fundamentals"):
                selected_analysts.append(AnalystType.fundamentals)
        
        # Step 4: Research Depth - using CLI options
        st.subheader("🔍 Research Depth")
        research_depth_options = {
            "Shallow - Quick research, few debate rounds": 1,
            "Medium - Moderate debate rounds and strategy discussion": 3, 
            "Deep - Comprehensive research, in-depth debate and strategy": 5
        }
        
        research_depth_choice = st.selectbox(
            "Select Research Depth Level",
            options=list(research_depth_options.keys()),
            index=1,  # Default to Medium
            help="Controls the number of debate rounds between research team agents"
        )
        research_depth = research_depth_options[research_depth_choice]
        
        # Step 5: LLM Provider - using CLI options
        st.subheader("🌐 LLM Provider")
        provider_options = {
            "OpenAI": "https://api.openai.com/v1"
        }
        
        llm_provider = st.selectbox(
            "Select LLM Provider",
            options=list(provider_options.keys()),
            index=0,
            help="Choose your preferred LLM service provider"
        )
        backend_url = provider_options[llm_provider]
        
        # Environment Variables Check
        st.subheader("🔑 API Keys Status")
        import os
        
        key_status = {}
        key_status['OpenAI'] = "✅ Set" if os.getenv('OPENAI_API_KEY') else "❌ Missing" 
        
        status_col1, status_col2, status_col3 = st.columns(3)
        with status_col1:
            st.info(f"OpenAI: {key_status['OpenAI']}")
        # with status_col2:
        #     st.info(f"OpenAI: {key_status['OpenAI']}")
        
        
        if key_status[llm_provider] == "❌ Missing":
            st.error(f"⚠️ {llm_provider.upper()}_API_KEY environment variable is required!")
            st.code(f"export {llm_provider.upper()}_API_KEY=your_api_key_here")
        
        # Step 6: Thinking Agents - using CLI options
        st.subheader("🧠 Thinking Agents")
        
        # Define agent options based on CLI
        shallow_agent_options = {
            "openai": {
                "GPT-4o-mini - Fast and efficient": "gpt-4o-mini",
                "GPT-4.1-mini - Compact model": "gpt-4.1-mini",
                "GPT-4o - Standard model": "gpt-4o",
            },
        }
        deep_agent_options = {
            "openai": {
                "GPT-4o - Standard model": "gpt-4o",
                "o4-mini - Specialized reasoning": "o4-mini",
                "o3-mini - Advanced reasoning": "o3-mini",
                "o1 - Premier reasoning": "o1",
                "GPT-5 - Premier reasoning": "gpt-5",
            },
        }
        
        provider_key = llm_provider.lower()
        
        col1, col2 = st.columns(2)
        with col1:
            shallow_options = shallow_agent_options.get(provider_key, {"Default": "default"})
            shallow_choice = st.selectbox(
                "Quick-Thinking Agent",
                options=list(shallow_options.keys()),
                index=0,
                help="Fast model for quick tasks"
            )
            shallow_thinker = shallow_options[shallow_choice]
        
        with col2:
            deep_options = deep_agent_options.get(provider_key, {"Default": "default"})
            deep_choice = st.selectbox(
                "Deep-Thinking Agent", 
                options=list(deep_options.keys()),
                index=0,
                help="Advanced model for complex reasoning"
            )
            deep_thinker = deep_options[deep_choice]
        
        # Analysis Configuration Summary
        st.markdown("---")
        st.subheader("📋 Configuration Summary")
        
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            if selected_analysts:
                st.success(f"✅ **Analysts**: {len(selected_analysts)} selected")
                analyst_names = [f"• {analyst.value.title()}" for analyst in selected_analysts]
                st.markdown("\n".join(analyst_names))
            else:
                st.warning("⚠️ **No analysts selected**")
            
            st.info(f"🔍 **Research Depth**: {research_depth_choice.split(' - ')[0]}")
            st.info(f"🌐 **Provider**: {llm_provider}")
        
        with summary_col2:
            st.info(f"📊 **Ticker**: {ticker}")
            st.info(f"📅 **Date**: {analysis_date}")
            st.info(f"⚡ **Quick Agent**: {shallow_choice.split(' - ')[0]}")
            st.info(f"🧠 **Deep Agent**: {deep_choice.split(' - ')[0]}")
        
        st.markdown("---")
        
        if st.button("🚀 Start Analysis", type="primary", use_container_width=True, disabled=not selected_analysts):
            if not selected_analysts:
                st.error("Please select at least one analyst!")
            else:
                # Reset analysis state
                st.session_state.analysis_complete = False
                st.session_state.analysis_results = None
                
                # Reset MessageBuffer
                st.session_state.message_buffer = MessageBuffer()  # Fresh instance
                
                # Start analysis
                run_analysis(
                    ticker=ticker,
                    analysis_date=analysis_date.strftime("%Y-%m-%d"),
                    selected_analysts=selected_analysts,
                    research_depth=research_depth,
                    llm_provider=llm_provider.lower(),
                    backend_url=backend_url,
                    shallow_thinker=shallow_thinker,
                    deep_thinker=deep_thinker
                )
        
        # 🔍 Start Analysis 버튼 바로 아래에 상세한 로깅 및 디버그 섹션 추가
        st.markdown("---")
        st.markdown("### 🔍 실시간 로깅 및 모니터링")
        st.info("💡 분석 진행 상황을 실시간으로 모니터링할 수 있습니다. 분석을 시작하면 자동으로 업데이트됩니다.")
        
        # 탭으로 구성된 모니터링 섹션
        monitor_tabs = st.tabs(["📊 상태 모니터링", "📄 리포트 뷰어", "🔧 시스템 로그", "⚙️ 디버그 정보"])
        
        # Tab 1: 상태 모니터링
        with monitor_tabs[0]:
            st.subheader("📊 실시간 상태 모니터링")
            
            # 새로고침 버튼
            col_refresh1, col_refresh2 = st.columns([4, 1])
            with col_refresh2:
                if st.button("🔄 새로고침", key="refresh_status_main"):
                    st.rerun()
            
            # 전체 통계
            col1, col2, col3, col4 = st.columns(4)
            
            total_messages = len(st.session_state.message_buffer.messages)
            total_tools = len(st.session_state.message_buffer.tool_calls)
            llm_calls = sum(1 for _, msg_type, _ in st.session_state.message_buffer.messages if msg_type == "Reasoning")
            reports_count = sum(1 for content in st.session_state.message_buffer.report_sections.values() if content is not None)
            
            with col1:
                st.metric("💬 총 메시지", total_messages, help="전체 메시지 수")
            with col2:
                st.metric("🔧 도구 호출", total_tools, help="도구 호출 횟수")
            with col3:
                st.metric("🧠 LLM 호출", llm_calls, help="LLM 추론 호출")
            with col4:
                st.metric("📋 생성 리포트", reports_count, help="생성된 리포트 수")
            
            # 에이전트 상태 모니터링
            st.markdown("### 👥 에이전트 상태 현황")
            
            # 팀별로 구성
            teams = {
                "👥 분석팀": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
                "🔍 연구팀": ["Bull Researcher", "Bear Researcher", "Research Manager"],
                "💼 트레이딩팀": ["Trader"],
                "⚠️ 리스크 관리팀": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
                "🎯 포트폴리오 관리팀": ["Portfolio Manager"]
            }
            
            for team_name, agents in teams.items():
                with st.expander(f"{team_name} ({len([a for a in agents if st.session_state.message_buffer.agent_status[a] == 'completed'])}/{len(agents)} 완료)", expanded=True):
                    # 팀 진행률
                    completed = sum(1 for agent in agents if st.session_state.message_buffer.agent_status[agent] == "completed")
                    progress = completed / len(agents)
                    st.progress(progress, text=f"팀 진행률: {completed}/{len(agents)} ({progress:.1%})")
                    
                    # 각 에이전트 상태
                    for agent in agents:
                        status = st.session_state.message_buffer.agent_status[agent]
                        col_agent, col_status = st.columns([3, 1])
                        
                        with col_agent:
                            st.write(f"**{agent}**")
                        
                        with col_status:
                            if status == "completed":
                                st.success("✅ 완료")
                            elif status == "in_progress":
                                st.info("🔄 진행중")
                            elif status == "error":
                                st.error("❌ 오류")
                            else:
                                st.warning("⏳ 대기중")
            
            # 현재 활성 에이전트
            if st.session_state.message_buffer.current_agent:
                st.markdown("### 🎯 현재 활성 에이전트")
                st.success(f"**{st.session_state.message_buffer.current_agent}**가 작업 중입니다.")
            
            # 최근 상태 변경
            st.markdown("### 🔄 최근 상태 변경")
            status_changes = [msg for msg in st.session_state.message_buffer.messages if msg[1] == "📊 Status"]
            if status_changes:
                for timestamp, _, content in status_changes[-5:]:
                    st.info(f"`{timestamp}` {content}")
            else:
                st.caption("아직 상태 변경이 없습니다.")
        
        # Tab 2: 리포트 뷰어
        with monitor_tabs[1]:
            st.subheader("📄 생성된 리포트 뷰어")
            
            # 새로고침 버튼
            col_refresh1, col_refresh2 = st.columns([4, 1])
            with col_refresh2:
                if st.button("🔄 새로고침", key="refresh_reports_main"):
                    st.rerun()
            
            section_titles = {
                "market_report": "📈 시장 분석",
                "sentiment_report": "💬 소셜 센티먼트", 
                "news_report": "📰 뉴스 분석",
                "fundamentals_report": "🏢 펀더멘털 분석",
                "investment_plan": "🔍 연구팀 결정",
                "trader_investment_plan": "💼 트레이딩 플랜",
                "final_trade_decision": "🎯 최종 투자 결정"
            }
            
            # 리포트 상태 요약
            available_reports = [(name, content) for name, content in st.session_state.message_buffer.report_sections.items() if content is not None]
            
            if available_reports:
                st.success(f"📊 **{len(available_reports)}/{len(section_titles)}** 리포트가 생성되었습니다.")
                
                # 리포트 선택기
                report_names = [section_titles.get(name, name) for name, _ in available_reports]
                selected_report = st.selectbox("보고 싶은 리포트를 선택하세요:", ["전체 리포트"] + report_names, key="report_selector_main")
                
                if selected_report == "전체 리포트":
                    # 전체 리포트 표시
                    for section_name, content in available_reports:
                        title = section_titles.get(section_name, section_name)
                        with st.expander(f"{title}", expanded=False):
                            st.markdown(content)
                            
                            # 개별 리포트 다운로드
                            st.download_button(
                                label=f"💾 {title} 다운로드",
                                data=content,
                                file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                mime="text/markdown",
                                key=f"download_report_main_{section_name}"
                            )
                else:
                    # 선택된 리포트만 표시
                    selected_index = report_names.index(selected_report)
                    section_name, content = available_reports[selected_index]
                    title = section_titles.get(section_name, section_name)
                    
                    st.markdown(f"### {title}")
                    st.markdown(content)
                    
                    # 다운로드 버튼
                    st.download_button(
                        label=f"💾 {title} 다운로드",
                        data=content,
                        file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                        mime="text/markdown",
                        key="download_selected_main"
                    )
            else:
                st.info("📋 아직 생성된 리포트가 없습니다. 분석이 완료되면 여기에 리포트가 표시됩니다.")
                
                # 예상 리포트 목록
                st.markdown("### 🔮 예상 리포트 목록:")
                for section_name, title in section_titles.items():
                    st.markdown(f"- {title} ⏳")
        
        # Tab 3: 시스템 로그
        with monitor_tabs[2]:
            st.subheader("🔧 시스템 로그")
            
            # 새로고침 버튼
            col_refresh1, col_refresh2 = st.columns([4, 1])
            with col_refresh2:
                if st.button("🔄 새로고침", key="refresh_logs_main"):
                    st.rerun()
            
            # 로그 파일 정보
            log_file_size = "N/A"
            try:
                import os
                if os.path.exists('streamlit_analysis.log'):
                    log_file_size = f"{os.path.getsize('streamlit_analysis.log') // 1024} KB"
            except:
                pass
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📄 로그 파일 크기", log_file_size)
            with col2:
                if st.session_state.get('analysis_complete', False):
                    try:
                        if os.path.exists('streamlit_analysis.log'):
                            with open('streamlit_analysis.log', 'r', encoding='utf-8') as f:
                                log_content = f.read()
                            st.download_button(
                                label="📋 로그 파일 다운로드",
                                data=log_content,
                                file_name=f"streamlit_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                                mime="text/plain",
                                key="download_log_main"
                            )
                    except Exception as e:
                        st.warning(f"로그 파일 읽기 실패: {str(e)}")
            
            st.info("💡 Console logs are printed to terminal. Log file: `streamlit_analysis.log`")
            
            # 활동 로그 표시
            st.markdown("### 📜 활동 로그")
            
            all_activity = []
            
            # 메시지와 도구 호출을 시간순으로 결합
            for timestamp, msg_type, content in st.session_state.message_buffer.messages:
                icon = "🧠" if msg_type == "Reasoning" else "💬" if msg_type == "System" else "📊"
                all_activity.append((timestamp, f"{icon} {msg_type}", content))
            
            for timestamp, tool_name, args in st.session_state.message_buffer.tool_calls:
                args_str = f"{tool_name}({str(args)[:150]}...)" if len(str(args)) > 150 else f"{tool_name}({args})"
                all_activity.append((timestamp, "🔧 TOOL", args_str))
            
            # 시간순 정렬 (최신 순)
            all_activity.sort(key=lambda x: x[0], reverse=True)
            
            if all_activity:
                # 활동 수 선택
                activity_count = st.selectbox("표시할 활동 수", [10, 20, 50, 100], index=1, key="activity_count_main")
                
                # 필터링 옵션
                filter_option = st.selectbox("필터링", ["전체", "🧠 Reasoning", "🔧 Tool", "💬 System", "📊 Status"], key="log_filter_main")
                
                # 필터링 적용
                if filter_option != "전체":
                    all_activity = [item for item in all_activity if filter_option.split(' ')[1] in item[1]]
                
                for i, (timestamp, activity_type, content) in enumerate(all_activity[:activity_count]):
                    with st.expander(f"`{timestamp}` {activity_type}", expanded=False):
                        content_str = str(content)
                        if len(content_str) > 1000:
                            st.text_area("내용", content_str[:1000] + "...", height=150, key=f"log_content_main_{i}_{timestamp.replace(':', '')}")
                            if st.button(f"전체 내용 보기", key=f"show_full_main_{i}"):
                                st.text(content_str)
                        else:
                            st.markdown(content_str)
            else:
                st.info("📋 아직 활동 기록이 없습니다.")
        
        # Tab 4: 디버그 정보
        with monitor_tabs[3]:
            st.subheader("⚙️ 디버그 정보")
            
            # 새로고침 버튼
            col_refresh1, col_refresh2 = st.columns([4, 1])
            with col_refresh2:
                if st.button("🔄 새로고침", key="refresh_debug_main"):
                    st.rerun()
            
            # 세션 상태 정보
            with st.expander("🔍 세션 상태", expanded=False):
                st.json({
                    "Session State Keys": list(st.session_state.keys()),
                    "Analysis Complete": st.session_state.get('analysis_complete', False),
                    "Has Analysis Results": bool(st.session_state.get('analysis_results')),
                    "Results Directory": st.session_state.get('results_dir', 'Not Set'),
                    "Log File": st.session_state.get('log_file', 'Not Set')
                })
            
            # 메시지 버퍼 상태
            with st.expander("💾 메시지 버퍼 상태", expanded=False):
                st.json({
                    "Messages Count": len(st.session_state.message_buffer.messages),
                    "Tool Calls Count": len(st.session_state.message_buffer.tool_calls),
                    "Current Agent": st.session_state.message_buffer.current_agent,
                    "Agent Status": dict(st.session_state.message_buffer.agent_status),
                    "Available Reports": [k for k, v in st.session_state.message_buffer.report_sections.items() if v is not None],
                    "Report Sections Keys": list(st.session_state.message_buffer.report_sections.keys())
                })
            
            # 성능 메트릭
            with st.expander("📈 성능 메트릭", expanded=False):
                current_time = datetime.datetime.now()
                
                # 분석 시작 시간 추정 (첫 번째 메시지 시간 기준)
                start_time_str = "N/A"
                duration = "N/A"
                if st.session_state.message_buffer.messages:
                    first_message_time = st.session_state.message_buffer.messages[0][0]
                    start_time_str = first_message_time
                    try:
                        # 시간 차이 계산 (대략적)
                        duration = "분석 진행 중"
                        if st.session_state.get('analysis_complete', False):
                            duration = "분석 완료"
                    except:
                        pass
                
                st.json({
                    "Analysis Start Time": start_time_str,
                    "Duration": duration,
                    "Current Time": current_time.strftime("%H:%M:%S"),
                    "Messages Rate": f"{len(st.session_state.message_buffer.messages)} messages",
                    "Tools Rate": f"{len(st.session_state.message_buffer.tool_calls)} tools",
                    "Average Message Length": f"{sum(len(str(content)) for _, _, content in st.session_state.message_buffer.messages) // max(1, len(st.session_state.message_buffer.messages))} chars" if st.session_state.message_buffer.messages else "0 chars"
                })
    
    # Main content area - using MessageBuffer for state detection
    if not st.session_state.analysis_complete and (st.session_state.message_buffer.messages or st.session_state.message_buffer.tool_calls):
        show_analysis_progress()
    elif st.session_state.analysis_complete and st.session_state.analysis_results:
        show_analysis_results()
    else:
        show_welcome_screen()

def show_welcome_screen():
    """Display welcome screen with instructions"""
    # Responsive layout for mobile
    st.markdown("""
    <div class="hero-section" style="margin: 2rem 0;">
        <h2 style="margin: 0; color: white;">🎯 Welcome to TradingAgents</h2>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Advanced Multi-Agent Financial Analysis Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature highlights with cards
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; color: white;">🤖 AI-Powered</h4>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">Multiple LLM agents working together</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; color: white;">📈 Real-time</h4>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">Live market data analysis</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; color: white;">📱 Mobile-Ready</h4>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">Optimized for all devices</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Workflow explanation with better mobile layout
    st.markdown("### 🔄 Analysis Workflow")
    
    workflow_steps = [
        ("👥", "Analyst Team", "Market, Social, News, Fundamentals Analysis"),
        ("🔍", "Research Team", "Bull vs Bear Debate & Research Manager Decision"),
        ("💼", "Trading Team", "Trader Investment Plan Development"),
        ("⚠️", "Risk Management", "Risk Analysis & Assessment"),
        ("🎯", "Portfolio Management", "Final Investment Decision")
    ]
    
    for i, (icon, title, description) in enumerate(workflow_steps, 1):
        st.markdown(f"""
        <div class="status-card">
            <h5 style="margin: 0; color: #333;">{icon} {i}. {title}</h5>
            <p style="margin: 0.3rem 0 0 0; color: #666; font-size: 0.9rem;">{description}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # How to use section
    st.markdown("### 🚀 Getting Started")
    st.info("""
    1. **Configure** your analysis parameters in the sidebar
    2. **Select** the analysts you want to include
    3. **Choose** your preferred LLM provider and models
    4. **Click** "Start Analysis" to begin the comprehensive analysis
    """)

def show_analysis_progress():
    """Display real-time analysis progress"""
    st.markdown("""
    <div class="hero-section">
        <h2 style="margin: 0; color: white;">📊 Analysis in Progress</h2>
        <div class="loading-spinner" style="margin: 1rem auto;"></div>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">AI agents are analyzing your selected stock...</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh for real-time updates during analysis (removed to prevent UI blocking)
    # Real-time updates are handled by the streaming process
    
    # Comprehensive Statistics (CLI-style)
    st.markdown("### 📈 Analysis Statistics")
    
    # Calculate detailed statistics
    tool_calls_count = len(st.session_state.message_buffer.tool_calls)
    llm_calls_count = sum(1 for _, msg_type, _ in st.session_state.message_buffer.messages if msg_type == "Reasoning")
    system_messages = sum(1 for _, msg_type, _ in st.session_state.message_buffer.messages if msg_type == "System")
    status_changes = sum(1 for _, msg_type, _ in st.session_state.message_buffer.messages if msg_type == "📊 Status")
    reports_count = sum(1 for content in st.session_state.message_buffer.report_sections.values() if content is not None)
    total_messages = len(st.session_state.message_buffer.messages)
    
    # Agent statistics
    completed_agents = sum(1 for status in st.session_state.message_buffer.agent_status.values() if status == "completed")
    in_progress_agents = sum(1 for status in st.session_state.message_buffer.agent_status.values() if status == "in_progress")
    total_agents = len(st.session_state.message_buffer.agent_status)
    
    # Display comprehensive stats in rows for better mobile experience
    stats_row1 = st.columns(4)
    stats_row2 = st.columns(4)
    
    with stats_row1[0]:
        st.metric("🔧 Tool Calls", tool_calls_count, help="API and function calls made by agents")
    
    with stats_row1[1]:
        st.metric("🧠 LLM Calls", llm_calls_count, help="Large Language Model reasoning calls")
    
    with stats_row1[2]:
        st.metric("📊 Reports Generated", reports_count, help="Completed analysis reports")
    
    with stats_row1[3]:
        st.metric("✅ Agents Progress", f"{completed_agents}/{total_agents}", help="Completed vs Total agents")
    
    with stats_row2[0]:
        st.metric("💬 Total Messages", total_messages, help="All messages exchanged")
    
    with stats_row2[1]:
        st.metric("⚙️ System Messages", system_messages, help="System and configuration messages")
    
    with stats_row2[2]:
        st.metric("🔄 Status Changes", status_changes, help="Agent status transitions")
    
    with stats_row2[3]:
        progress_pct = (completed_agents / total_agents) * 100 if total_agents > 0 else 0
        st.metric("📈 Completion %", f"{progress_pct:.1f}%", help="Overall completion percentage")
    
    # Activity timeline (like CLI)
    if st.session_state.message_buffer.messages or st.session_state.message_buffer.tool_calls:
        st.markdown("#### ⏱️ Activity Timeline")
        
        # Get start time
        if st.session_state.message_buffer.messages:
            start_time = st.session_state.message_buffer.messages[0][0]
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            st.info(f"🚀 Analysis started: {start_time} | Current time: {current_time}")
        
        # Show activity rate
        total_activities = len(st.session_state.message_buffer.messages) + len(st.session_state.message_buffer.tool_calls)
        if total_activities > 0:
            st.success(f"⚡ Activity rate: {total_activities} actions performed")
    
    # Token usage estimation (like CLI)
    if llm_calls_count > 0:
        st.markdown("#### 💰 Usage Estimation")
        usage_col1, usage_col2, usage_col3 = st.columns(3)
        
        # Rough estimates based on average message lengths
        avg_message_length = sum(len(str(content)) for _, _, content in st.session_state.message_buffer.messages) / len(st.session_state.message_buffer.messages) if st.session_state.message_buffer.messages else 0
        estimated_input_tokens = int(llm_calls_count * avg_message_length * 0.25)  # Rough estimate: 4 chars per token
        estimated_output_tokens = int(reports_count * 1000)  # Rough estimate: 1000 tokens per report
        
        with usage_col1:
            st.metric("📥 Est. Input Tokens", f"{estimated_input_tokens:,}", help="Estimated input tokens to LLM")
        
        with usage_col2:
            st.metric("📤 Est. Output Tokens", f"{estimated_output_tokens:,}", help="Estimated output tokens from LLM")
        
        with usage_col3:
            total_tokens = estimated_input_tokens + estimated_output_tokens
            st.metric("🎯 Est. Total Tokens", f"{total_tokens:,}", help="Estimated total token usage")
        
        # Show cost estimation (very rough)
        if total_tokens > 0:
            # Rough cost estimates for different providers (per 1M tokens)
            cost_estimates = {
                "OpenAI": 2.00,  # GPT-4o pricing
                
            }
            
            # Use provider from session state if available
            provider = "OpenAI"  # Default
            if hasattr(st.session_state, 'llm_provider'):
                provider = st.session_state.llm_provider
            
            cost_per_million = cost_estimates.get(provider, 1.00)
            estimated_cost = (total_tokens / 1_000_000) * cost_per_million
            
            st.info(f"💵 Estimated cost ({provider}): ${estimated_cost:.4f}")
    
    st.markdown("---")
    
    st.markdown("---")
    
    # Enhanced Progress Overview for better mobile/desktop experience
    st.markdown("### 🎯 Current Status")
    
    # Show current agent prominently
    if st.session_state.message_buffer.current_agent:
        st.markdown(f"""
        <div class="hero-section" style="margin: 1rem 0;">
            <h3 style="margin: 0; color: white;">🎯 Currently Active</h3>
            <h2 style="margin: 0.5rem 0 0 0; color: white;">{st.session_state.message_buffer.current_agent}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Agent Status in expandable sections for better mobile experience
    st.markdown("### 👥 Team Progress")
    
    # Group agents by team
    teams = {
        "👥 Analyst Team": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
        "🔍 Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "💼 Trading Team": ["Trader"],
        "⚠️ Risk Management": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
        "🎯 Portfolio Management": ["Portfolio Manager"]
    }
    
    for team_name, agents in teams.items():
        # Calculate team progress
        team_completed = sum(1 for agent in agents if st.session_state.message_buffer.agent_status[agent] == "completed")
        team_total = len(agents)
        team_progress = team_completed / team_total
        
        # Determine if team section should be expanded
        team_active = any(st.session_state.message_buffer.agent_status[agent] == "in_progress" for agent in agents)
        
        with st.expander(f"{team_name} ({team_completed}/{team_total})", expanded=team_active):
            # Show team progress bar
            st.progress(team_progress, text=f"Team Progress: {team_completed}/{team_total}")
            
            # Show each agent status
            cols = st.columns(2) if len(agents) > 2 else [st.container()]
            for i, agent in enumerate(agents):
                col = cols[i % len(cols)] if len(cols) > 1 else cols[0]
                with col:
                    status = st.session_state.message_buffer.agent_status[agent]
                    if status == "completed":
                        st.success(f"✅ {agent}")
                    elif status == "in_progress":
                        st.info(f"🔄 {agent} (Working...)")
                    elif status == "error":
                        st.error(f"❌ {agent} (Error)")
                    else:
                        st.warning(f"⏳ {agent} (Waiting...)")
    
    # Recent Activity in a more prominent display
    st.markdown("### 📋 Live Activity Feed")
    
    all_messages = st.session_state.message_buffer.get_all_messages()
    if all_messages:
        # Show last 5 messages prominently
        recent_messages = all_messages[-5:]
        
        for i, (timestamp, msg_type, content) in enumerate(reversed(recent_messages)):
            # Format message type with icons
            type_icons = {
                "Tool": "🔧",
                "Reasoning": "🧠", 
                "System": "⚙️",
                "Analysis": "📊"
            }
            icon = type_icons.get(msg_type, "💬")
            
            # Show most recent message expanded
            expanded = (i == 0)
            
            with st.expander(f"{icon} {timestamp} - {msg_type}", expanded=expanded):
                if msg_type == "Tool":
                    st.code(content)
                else:
                    st.markdown(content[:1000] + ("..." if len(content) > 1000 else ""))
    else:
        st.info("📋 Activity feed will show live updates during analysis...")
    
    # Current Report Section (if available)
    if st.session_state.message_buffer.current_report:
        st.markdown("### 📄 Latest Generated Report")
        
        st.markdown("""
        <div class="status-card">
            <h4 style="margin: 0 0 1rem 0; color: #333;">📊 Most Recent Report Section</h4>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📖 View Latest Report", expanded=True):
            st.markdown(st.session_state.message_buffer.current_report[:5000] + 
                      ("..." if len(st.session_state.message_buffer.current_report) > 2000 else ""))
    
    # Always visible Recent Activity Section
    st.markdown("---")
    st.subheader("📋 Recent Activity")
    
    # Show recent activity prominently (combined messages and status changes)
    recent_activity = []
    
    # Add recent messages
    for timestamp, msg_type, content in st.session_state.message_buffer.messages[-10:]:
        recent_activity.append((timestamp, msg_type, str(content)[:500] + ('...' if len(str(content)) > 500 else '')))
    
    # Add recent tool calls with better formatting
    for timestamp, tool_name, args in st.session_state.message_buffer.tool_calls[-5:]:
        args_str = str(args)[:500] + ('...' if len(str(args)) > 200 else '')
        recent_activity.append((timestamp, "🔧 Tool Call", f"{tool_name}({args_str})"))
    
    # Sort by timestamp and show most recent first
    recent_activity.sort(key=lambda x: x[0], reverse=True)
    
    if recent_activity:
        for timestamp, activity_type, content in recent_activity[:8]:  # Show last 8 activities
            # Format different activity types
            if activity_type == "🔧 Tool Call":
                st.markdown(f"`{timestamp}` **{activity_type}**")
                st.code(content)
            else:
                st.markdown(f"`{timestamp}` **{activity_type}:** {content}")
            st.markdown("---")
    else:
        st.info("📋 Recent activity will appear here during analysis...")
    
    # Comprehensive Agent Status Board (CLI-style)
    st.markdown("### 📊 Complete Agent Status Board")
    
    # Show overall progress first
    total_agents = len(st.session_state.message_buffer.agent_status)
    completed_agents = sum(1 for status in st.session_state.message_buffer.agent_status.values() if status == "completed")
    in_progress_agents = sum(1 for status in st.session_state.message_buffer.agent_status.values() if status == "in_progress")
    
    progress_col1, progress_col2, progress_col3 = st.columns(3)
    with progress_col1:
        st.metric("✅ Completed", completed_agents)
    with progress_col2:
        st.metric("🔄 In Progress", in_progress_agents)
    with progress_col3:
        st.metric("⏳ Pending", total_agents - completed_agents - in_progress_agents)
    
    # Overall progress bar
    overall_progress = completed_agents / total_agents
    st.progress(overall_progress, text=f"Overall Progress: {completed_agents}/{total_agents} ({overall_progress:.1%})")
    
    # Show all agents in CLI-style table format
    st.markdown("#### 📋 Detailed Agent Status")
    
    teams = {
        "👥 Analyst Team": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
        "🔍 Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"], 
        "💼 Trading Team": ["Trader"],
        "⚠️ Risk Management": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
        "🎯 Portfolio Management": ["Portfolio Manager"]
    }
    
    # Create a comprehensive status display
    status_data = []
    for team_name, agents in teams.items():
        for agent in agents:
            status = st.session_state.message_buffer.agent_status[agent]
            status_emoji = {
                "completed": "✅",
                "in_progress": "🔄", 
                "error": "❌",
                "pending": "⏳"
            }.get(status, "❓")
            
            is_current = agent == st.session_state.message_buffer.current_agent
            current_indicator = "🎯 ACTIVE" if is_current else ""
            
            status_data.append({
                "Team": team_name.replace("👥 ", "").replace("🔍 ", "").replace("💼 ", "").replace("⚠️ ", "").replace("🎯 ", ""),
                "Agent": agent,
                "Status": f"{status_emoji} {status.title()}",
                "Current": current_indicator
            })
    
    # Display in a table format
    try:
        import pandas as pd
        df = pd.DataFrame(status_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    except ImportError:
        # Fallback display without pandas
        for data in status_data:
            cols = st.columns(4)
            with cols[0]:
                st.write(data["Team"])
            with cols[1]: 
                st.write(data["Agent"])
            with cols[2]:
                st.write(data["Status"])
            with cols[3]:
                st.write(data["Current"])
    
    # Show recent status changes only
    st.markdown("#### 🔄 Recent Status Changes")
    status_changes = [msg for msg in st.session_state.message_buffer.messages if msg[1] == "📊 Status"]
    if status_changes:
        for timestamp, msg_type, content in status_changes[-5:]:  # Show last 5 status changes
            st.success(f"`{timestamp}` {content}")
    else:
        st.info("Status changes will appear here during analysis...")
    
    
    # Enhanced Reports Display for better mobile/desktop experience
    st.markdown("---")
    st.subheader("📊 Generated Reports")
    
    section_titles = {
        "market_report": "📈 Market Analysis",
        "sentiment_report": "💬 Social Sentiment", 
        "news_report": "📰 News Analysis",
        "fundamentals_report": "🏢 Fundamentals Analysis",
        "investment_plan": "🔍 Research Team Decision",
        "trader_investment_plan": "💼 Trading Team Plan",
        "final_trade_decision": "🎯 Portfolio Management Decision"
    }
    
    # Show reports in tabs for better organization
    if any(st.session_state.message_buffer.report_sections.values()):
        # Create tabs for different report categories
        available_reports = [(section_name, content) for section_name, content in st.session_state.message_buffer.report_sections.items() if content]
        
        if available_reports:
            # Group reports by category
            analyst_reports = [(name, content) for name, content in available_reports if name in ["market_report", "sentiment_report", "news_report", "fundamentals_report"]]
            team_reports = [(name, content) for name, content in available_reports if name in ["investment_plan", "trader_investment_plan", "final_trade_decision"]]
            
            # Create tabs
            tab_names = []
            if analyst_reports:
                tab_names.append("👥 Analyst Reports")
            if team_reports:
                tab_names.append("🏆 Team Decisions")
            if len(available_reports) > 0:
                tab_names.append("📋 All Reports")
            
            if tab_names:
                tabs = st.tabs(tab_names)
                tab_index = 0
                
                # Analyst Reports Tab
                if analyst_reports:
                    with tabs[tab_index]:
                        for section_name, content in analyst_reports:
                            title = section_titles.get(section_name, section_name.replace("_", " ").title())
                            
                            st.markdown(f"""
                            <div class="status-card">
                                <h4 style="margin: 0 0 1rem 0; color: #333;">{title}</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.expander(f"📄 View {title}", expanded=False):
                                st.markdown(content)
                                
                                # Add download button for individual report
                                st.download_button(
                                    label=f"💾 Download {title}",
                                    data=content,
                                    file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                    mime="text/markdown",
                                    key=f"download_{section_name}"
                                )
                    tab_index += 1
                
                # Team Decisions Tab
                if team_reports:
                    with tabs[tab_index]:
                        for section_name, content in team_reports:
                            title = section_titles.get(section_name, section_name.replace("_", " ").title())
                            
                            st.markdown(f"""
                            <div class="status-card">
                                <h4 style="margin: 0 0 1rem 0; color: #333;">{title}</h4>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            with st.expander(f"📄 View {title}", expanded=True):
                                st.markdown(content)
                                
                                # Add download button for individual report
                                st.download_button(
                                    label=f"💾 Download {title}",
                                    data=content,
                                    file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                                    mime="text/markdown",
                                    key=f"download_team_{section_name}"
                                )
                    tab_index += 1
                
                # All Reports Tab
                if len(available_reports) > 0:
                    with tabs[tab_index]:
                        st.markdown("### 📋 Complete Analysis Overview")
                        
                        for section_name, content in available_reports:
                            title = section_titles.get(section_name, section_name.replace("_", " ").title())
                            
                            st.markdown(f"""
                            <div class="status-card">
                                <h5 style="margin: 0 0 0.5rem 0; color: #333;">{title}</h5>
                                <p style="margin: 0; color: #666; font-size: 0.9rem;">Generated: {datetime.datetime.now().strftime('%H:%M:%S')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Show preview of content
                            preview = content[:800] + "..." if len(content) > 800 else content
                            st.markdown(f"**Preview:** {preview}")
                            
                            with st.expander(f"📖 Read Full {title}", expanded=False):
                                st.markdown(content)
        else:
            st.info("📋 Reports will appear here as agents complete their analysis...")
    else:
        st.info("📋 Reports will appear here as agents complete their analysis...")
        
        # Show placeholder cards for expected reports
        st.markdown("### 🔮 Expected Reports:")
        expected_reports = [
            ("📈 Market Analysis", "Technical analysis and market trends"),
            ("💬 Social Sentiment", "Social media sentiment analysis"),  
            ("📰 News Analysis", "Latest news impact analysis"),
            ("🏢 Fundamentals Analysis", "Company financial fundamentals"),
            ("🔍 Research Team Decision", "Bull vs Bear research conclusion"),
            ("💼 Trading Team Plan", "Investment strategy and plan"),
            ("🎯 Final Decision", "Portfolio management recommendation")
        ]
        
        cols = st.columns(2)
        for i, (title, description) in enumerate(expected_reports):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="status-card" style="opacity: 0.6;">
                    <h5 style="margin: 0 0 0.5rem 0; color: #666;">{title}</h5>
                    <p style="margin: 0; color: #999; font-size: 0.9rem;">{description}</p>
                    <p style="margin: 0.5rem 0 0 0; color: #999; font-size: 0.8rem;">⏳ Waiting...</p>
                </div>
                """, unsafe_allow_html=True)
    
    # 🔍 분석 진행 중에도 로깅 및 디버그 섹션 추가
    st.markdown("---")
    st.markdown("### 🔍 실시간 로깅 및 모니터링")
    st.info("💡 분석 진행 상황을 실시간으로 모니터링할 수 있습니다. 새로고침 버튼을 눌러 최신 정보를 확인하세요.")
    
    # 탭으로 구성된 모니터링 섹션
    progress_monitor_tabs = st.tabs(["📊 상태 모니터링", "📄 리포트 뷰어", "🔧 시스템 로그", "⚙️ 디버그 정보"])
    
    # Tab 1: 상태 모니터링
    with progress_monitor_tabs[0]:
        st.subheader("📊 실시간 상태 모니터링")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_status_progress"):
                st.rerun()
        
        # 전체 통계
        col1, col2, col3, col4 = st.columns(4)
        
        total_messages = len(st.session_state.message_buffer.messages)
        total_tools = len(st.session_state.message_buffer.tool_calls)
        llm_calls = sum(1 for _, msg_type, _ in st.session_state.message_buffer.messages if msg_type == "Reasoning")
        reports_count = sum(1 for content in st.session_state.message_buffer.report_sections.values() if content is not None)
        
        with col1:
            st.metric("💬 총 메시지", total_messages, help="전체 메시지 수")
        with col2:
            st.metric("🔧 도구 호출", total_tools, help="도구 호출 횟수")
        with col3:
            st.metric("🧠 LLM 호출", llm_calls, help="LLM 추론 호출")
        with col4:
            st.metric("📋 생성 리포트", reports_count, help="생성된 리포트 수")
        
        # 에이전트 상태 모니터링
        st.markdown("### 👥 에이전트 상태 현황")
        
        # 팀별로 구성
        teams = {
            "👥 분석팀": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
            "🔍 연구팀": ["Bull Researcher", "Bear Researcher", "Research Manager"],
            "💼 트레이딩팀": ["Trader"],
            "⚠️ 리스크 관리팀": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
            "🎯 포트폴리오 관리팀": ["Portfolio Manager"]
        }
        
        for team_name, agents in teams.items():
            with st.expander(f"{team_name} ({len([a for a in agents if st.session_state.message_buffer.agent_status[a] == 'completed'])}/{len(agents)} 완료)", expanded=True):
                # 팀 진행률
                completed = sum(1 for agent in agents if st.session_state.message_buffer.agent_status[agent] == "completed")
                progress = completed / len(agents)
                st.progress(progress, text=f"팀 진행률: {completed}/{len(agents)} ({progress:.1%})")
                
                # 각 에이전트 상태
                for agent in agents:
                    status = st.session_state.message_buffer.agent_status[agent]
                    col_agent, col_status = st.columns([3, 1])
                    
                    with col_agent:
                        st.write(f"**{agent}**")
                    
                    with col_status:
                        if status == "completed":
                            st.success("✅ 완료")
                        elif status == "in_progress":
                            st.info("🔄 진행중")
                        elif status == "error":
                            st.error("❌ 오류")
                        else:
                            st.warning("⏳ 대기중")
        
        # 현재 활성 에이전트
        if st.session_state.message_buffer.current_agent:
            st.markdown("### 🎯 현재 활성 에이전트")
            st.success(f"**{st.session_state.message_buffer.current_agent}**가 작업 중입니다.")
        
        # 최근 상태 변경
        st.markdown("### 🔄 최근 상태 변경")
        status_changes = [msg for msg in st.session_state.message_buffer.messages if msg[1] == "📊 Status"]
        if status_changes:
            for timestamp, _, content in status_changes[-5:]:
                st.info(f"`{timestamp}` {content}")
        else:
            st.caption("아직 상태 변경이 없습니다.")
    
    # Tab 2: 리포트 뷰어
    with progress_monitor_tabs[1]:
        st.subheader("📄 생성된 리포트 뷰어")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_reports_progress"):
                st.rerun()
        
        section_titles = {
            "market_report": "📈 시장 분석",
            "sentiment_report": "💬 소셜 센티먼트", 
            "news_report": "📰 뉴스 분석",
            "fundamentals_report": "🏢 펀더멘털 분석",
            "investment_plan": "🔍 연구팀 결정",
            "trader_investment_plan": "💼 트레이딩 플랜",
            "final_trade_decision": "🎯 최종 투자 결정"
        }
        
        # 리포트 상태 요약
        available_reports = [(name, content) for name, content in st.session_state.message_buffer.report_sections.items() if content is not None]
        
        if available_reports:
            st.success(f"📊 **{len(available_reports)}/{len(section_titles)}** 리포트가 생성되었습니다.")
            
            # 리포트 선택기
            report_names = [section_titles.get(name, name) for name, _ in available_reports]
            selected_report = st.selectbox("보고 싶은 리포트를 선택하세요:", ["전체 리포트"] + report_names, key="report_selector_progress")
            
            if selected_report == "전체 리포트":
                # 전체 리포트 표시
                for section_name, content in available_reports:
                    title = section_titles.get(section_name, section_name)
                    with st.expander(f"{title}", expanded=False):
                        st.markdown(content)
                        
                        # 개별 리포트 다운로드
                        st.download_button(
                            label=f"💾 {title} 다운로드",
                            data=content,
                            file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                            key=f"download_report_progress_{section_name}"
                        )
            else:
                # 선택된 리포트만 표시
                selected_index = report_names.index(selected_report)
                section_name, content = available_reports[selected_index]
                title = section_titles.get(section_name, section_name)
                
                st.markdown(f"### {title}")
                st.markdown(content)
                
                # 다운로드 버튼
                st.download_button(
                    label=f"💾 {title} 다운로드",
                    data=content,
                    file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    key="download_selected_progress"
                )
        else:
            st.info("📋 아직 생성된 리포트가 없습니다. 분석이 완료되면 여기에 리포트가 표시됩니다.")
            
            # 예상 리포트 목록
            st.markdown("### 🔮 예상 리포트 목록:")
            for section_name, title in section_titles.items():
                st.markdown(f"- {title} ⏳")
    
    # Tab 3: 시스템 로그
    with progress_monitor_tabs[2]:
        st.subheader("🔧 시스템 로그")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_logs_progress"):
                st.rerun()
        
        # 로그 파일 정보
        log_file_size = "N/A"
        try:
            import os
            if os.path.exists('streamlit_analysis.log'):
                log_file_size = f"{os.path.getsize('streamlit_analysis.log') // 1024} KB"
        except:
            pass
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📄 로그 파일 크기", log_file_size)
        with col2:
            if st.session_state.get('analysis_complete', False):
                try:
                    if os.path.exists('streamlit_analysis.log'):
                        with open('streamlit_analysis.log', 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        st.download_button(
                            label="📋 로그 파일 다운로드",
                            data=log_content,
                            file_name=f"streamlit_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                            mime="text/plain",
                            key="download_log_progress"
                        )
                except Exception as e:
                    st.warning(f"로그 파일 읽기 실패: {str(e)}")
        
        st.info("💡 Console logs are printed to terminal. Log file: `streamlit_analysis.log`")
        
        # 활동 로그 표시
        st.markdown("### 📜 활동 로그")
        
        all_activity = []
        
        # 메시지와 도구 호출을 시간순으로 결합
        for timestamp, msg_type, content in st.session_state.message_buffer.messages:
            icon = "🧠" if msg_type == "Reasoning" else "💬" if msg_type == "System" else "📊"
            all_activity.append((timestamp, f"{icon} {msg_type}", content))
        
        for timestamp, tool_name, args in st.session_state.message_buffer.tool_calls:
            args_str = f"{tool_name}({str(args)[:150]}...)" if len(str(args)) > 150 else f"{tool_name}({args})"
            all_activity.append((timestamp, "🔧 TOOL", args_str))
        
        # 시간순 정렬 (최신 순)
        all_activity.sort(key=lambda x: x[0], reverse=True)
        
        if all_activity:
            # 활동 수 선택
            activity_count = st.selectbox("표시할 활동 수", [10, 20, 50, 100], index=1, key="activity_count_progress")
            
            # 필터링 옵션
            filter_option = st.selectbox("필터링", ["전체", "🧠 Reasoning", "🔧 Tool", "💬 System", "📊 Status"], key="log_filter_progress")
            
            # 필터링 적용
            if filter_option != "전체":
                all_activity = [item for item in all_activity if filter_option.split(' ')[1] in item[1]]
            
            for i, (timestamp, activity_type, content) in enumerate(all_activity[:activity_count]):
                with st.expander(f"`{timestamp}` {activity_type}", expanded=False):
                    content_str = str(content)
                    if len(content_str) > 1000:
                        st.text_area("내용", content_str[:1000] + "...", height=150, key=f"log_content_progress_{i}_{timestamp.replace(':', '')}")
                        if st.button(f"전체 내용 보기", key=f"show_full_progress_{i}"):
                            st.text(content_str)
                    else:
                        st.markdown(content_str)
        else:
            st.info("📋 아직 활동 기록이 없습니다.")
    
    # Tab 4: 디버그 정보
    with progress_monitor_tabs[3]:
        st.subheader("⚙️ 디버그 정보")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_debug_progress"):
                st.rerun()
        
        # 세션 상태 정보
        with st.expander("🔍 세션 상태", expanded=False):
            st.json({
                "Session State Keys": list(st.session_state.keys()),
                "Analysis Complete": st.session_state.get('analysis_complete', False),
                "Has Analysis Results": bool(st.session_state.get('analysis_results')),
                "Results Directory": st.session_state.get('results_dir', 'Not Set'),
                "Log File": st.session_state.get('log_file', 'Not Set')
            })
        
        # 메시지 버퍼 상태
        with st.expander("💾 메시지 버퍼 상태", expanded=False):
            st.json({
                "Messages Count": len(st.session_state.message_buffer.messages),
                "Tool Calls Count": len(st.session_state.message_buffer.tool_calls),
                "Current Agent": st.session_state.message_buffer.current_agent,
                "Agent Status": dict(st.session_state.message_buffer.agent_status),
                "Available Reports": [k for k, v in st.session_state.message_buffer.report_sections.items() if v is not None],
                "Report Sections Keys": list(st.session_state.message_buffer.report_sections.keys())
            })
        
        # 성능 메트릭
        with st.expander("📈 성능 메트릭", expanded=False):
            current_time = datetime.datetime.now()
            
            # 분석 시작 시간 추정 (첫 번째 메시지 시간 기준)
            start_time_str = "N/A"
            duration = "N/A"
            if st.session_state.message_buffer.messages:
                first_message_time = st.session_state.message_buffer.messages[0][0]
                start_time_str = first_message_time
                try:
                    # 시간 차이 계산 (대략적)
                    duration = "분석 진행 중"
                    if st.session_state.get('analysis_complete', False):
                        duration = "분석 완료"
                except:
                    pass
            
            st.json({
                "Analysis Start Time": start_time_str,
                "Duration": duration,
                "Current Time": current_time.strftime("%H:%M:%S"),
                "Messages Rate": f"{len(st.session_state.message_buffer.messages)} messages",
                "Tools Rate": f"{len(st.session_state.message_buffer.tool_calls)} tools",
                "Average Message Length": f"{sum(len(str(content)) for _, _, content in st.session_state.message_buffer.messages) // max(1, len(st.session_state.message_buffer.messages))} chars" if st.session_state.message_buffer.messages else "0 chars"
            })

def show_analysis_results():
    """Display final analysis results"""
    st.markdown("""
    <div class="hero-section">
        <h2 style="margin: 0; color: white;">📈 Analysis Results</h2>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Comprehensive AI-powered analysis complete</p>
    </div>
    """, unsafe_allow_html=True)
    
    results = st.session_state.analysis_results
    
    # Add summary metrics at the top
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; color: white;">📊 Market Score</h4>
            <h2 style="margin: 0.5rem 0 0 0; color: white;">8.5/10</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; color: white;">💰 Risk Level</h4>
            <h2 style="margin: 0.5rem 0 0 0; color: white;">Medium</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; color: white;">📈 Sentiment</h4>
            <h2 style="margin: 0.5rem 0 0 0; color: white;">Bullish</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h4 style="margin: 0; color: white;">⭐ Confidence</h4>
            <h2 style="margin: 0.5rem 0 0 0; color: white;">High</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Display results in responsive tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Analyst Team", "🔍 Research Team", "💼 Trading Plan", 
        "⚠️ Risk Management", "🎯 Final Decision"
    ])
    
    with tab1:
        st.markdown("### 👥 Analyst Team Reports")
        
        # Create responsive grid for analyst reports
        reports = [
            ("market_report", "📈 Market Analysis", "Market trends and technical indicators"),
            ("sentiment_report", "💬 Social Sentiment", "Social media and community sentiment"),
            ("news_report", "📰 News Analysis", "Latest news impact analysis"),
            ("fundamentals_report", "🏢 Fundamentals Analysis", "Company financial fundamentals")
        ]
        
        for report_key, title, description in reports:
            if results.get(report_key):
                st.markdown(f"""
                <div class="status-card">
                    <h4 style="margin: 0 0 0.5rem 0; color: #333;">{title}</h4>
                    <p style="margin: 0 0 1rem 0; color: #666; font-size: 0.9rem;">{description}</p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("View Full Report", expanded=False):
                    st.markdown(results[report_key])
            else:
                st.markdown(f"""
                <div class="status-card" style="opacity: 0.6;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #666;">{title}</h4>
                    <p style="margin: 0; color: #999; font-size: 0.9rem;">No data available</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        st.subheader("Research Team Decision")
        
        if results.get("investment_debate_state"):
            debate_state = results["investment_debate_state"]
            
            col1, col2 = st.columns(2)
            
            with col1:
                if debate_state.get("bull_history"):
                    with st.expander("🐂 Bull Researcher", expanded=True):
                        st.markdown(debate_state["bull_history"])
            
            with col2:
                if debate_state.get("bear_history"):
                    with st.expander("🐻 Bear Researcher", expanded=True):
                        st.markdown(debate_state["bear_history"])
            
            if debate_state.get("judge_decision"):
                with st.expander("👨‍💼 Research Manager Decision", expanded=True):
                    st.markdown(debate_state["judge_decision"])
    
    with tab3:
        st.subheader("Trading Team Plan")
        
        if results.get("trader_investment_plan"):
            st.markdown(results["trader_investment_plan"])
    
    with tab4:
        st.subheader("Risk Management Analysis")
        
        if results.get("risk_debate_state"):
            risk_state = results["risk_debate_state"]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if risk_state.get("risky_history"):
                    with st.expander("🔥 Aggressive Analyst", expanded=True):
                        st.markdown(risk_state["risky_history"])
            
            with col2:
                if risk_state.get("neutral_history"):
                    with st.expander("⚖️ Neutral Analyst", expanded=True):
                        st.markdown(risk_state["neutral_history"])
            
            with col3:
                if risk_state.get("safe_history"):
                    with st.expander("🛡️ Conservative Analyst", expanded=True):
                        st.markdown(risk_state["safe_history"])
    
    with tab5:
        st.markdown("### 🎯 Portfolio Manager Final Decision")
        
        if results.get("risk_debate_state", {}).get("judge_decision"):
            st.markdown("""
            <div class="status-card">
                <h4 style="margin: 0 0 1rem 0; color: #333;">💼 Portfolio Manager Analysis</h4>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(results["risk_debate_state"]["judge_decision"])
        
        # Display final trade decision with enhanced styling
        if results.get("final_trade_decision"):
            final_decision = results["final_trade_decision"]
            
            st.markdown("""
            <div class="hero-section" style="margin: 2rem 0;">
                <h3 style="margin: 0; color: white;">✅ Analysis Complete!</h3>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Final investment recommendation ready</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 🎯 Final Investment Decision:")
            st.success(f"**Decision:** {final_decision}")
            
            # Show saved files info
            if hasattr(st.session_state, 'results_dir'):
                st.info(f"📁 **Results saved to:** `{st.session_state.results_dir}`")
            
            # Add action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📊 Export Report", use_container_width=True, type="primary"):
                    st.session_state.show_export = True
                    st.rerun()
            with col2:
                if st.button("🔄 New Analysis", use_container_width=True):
                    restart_analysis()
            with col3:
                if st.button("📤 Share Results", use_container_width=True):
                    share_results()
            
            # Show export section if export button was clicked
            if st.session_state.get('show_export', False):
                st.markdown("---")
                export_analysis_report()

def export_analysis_report():
    """Export analysis report with multiple format options"""
    try:
        if st.session_state.analysis_results:
            st.subheader("📊 Download Analysis Results")
            
            # Show saved files location
            if hasattr(st.session_state, 'results_dir'):
                st.info(f"📁 **Results saved to:** `{st.session_state.results_dir}`")
                
                # List all saved files
                results_path = Path(st.session_state.results_dir)
                if results_path.exists():
                    st.markdown("### 📄 Available Files:")
                    
                    # Complete report
                    complete_report_file = results_path / "complete_analysis_report.md"
                    if complete_report_file.exists():
                        with open(complete_report_file, 'r', encoding='utf-8') as f:
                            complete_content = f.read()
                        st.download_button(
                            label="📝 Download Complete Report (Markdown)",
                            data=complete_content,
                            file_name=f"complete_analysis_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown"
                        )
                    
                    # Final state JSON
                    final_state_file = results_path / "final_state.json"
                    if final_state_file.exists():
                        with open(final_state_file, 'r', encoding='utf-8') as f:
                            json_content = f.read()
                        st.download_button(
                            label="🔧 Download Final State (JSON)",
                            data=json_content,
                            file_name=f"final_state_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    
                    # Log file
                    if hasattr(st.session_state, 'log_file'):
                        log_path = Path(st.session_state.log_file)
                        if log_path.exists():
                            with open(log_path, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                            st.download_button(
                                label="📋 Download Activity Log",
                                data=log_content,
                                file_name=f"activity_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                                mime="text/plain"
                            )
                    
                    # Individual reports
                    if hasattr(st.session_state, 'report_dir'):
                        report_path = Path(st.session_state.report_dir)
                        if report_path.exists():
                            st.markdown("### 📑 Individual Reports:")
                            for report_file in report_path.glob("*.md"):
                                with open(report_file, 'r', encoding='utf-8') as f:
                                    report_content = f.read()
                                st.download_button(
                                    label=f"📄 {report_file.name}",
                                    data=report_content,
                                    file_name=report_file.name,
                                    mime="text/markdown",
                                    key=f"download_{report_file.name}"
                                )
            
            # Legacy JSON export
            st.markdown("---")
            report_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "results": st.session_state.analysis_results
            }
            
            json_str = json.dumps(report_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📦 Download Legacy JSON Report",
                data=json_str,
                file_name=f"trading_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            st.success("✅ All reports prepared for download!")
        else:
            st.error("❌ No analysis results to export")
    except Exception as e:
        st.error(f"❌ Export failed: {str(e)}")
        st.exception(e)

def restart_analysis():
    """Restart the analysis process"""
    try:
        st.session_state.analysis_complete = False
        st.session_state.analysis_results = None
        # Reset MessageBuffer to fresh state
        st.session_state.message_buffer = MessageBuffer()
        st.rerun()
    except Exception as e:
        st.error(f"❌ Restart failed: {str(e)}")

def share_results():
    """Share analysis results"""
    try:
        if st.session_state.analysis_results:
            # Create shareable summary
            summary = f"""
            📈 TradingAgents Analysis Summary
            
            ⏰ Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            📊 Analysis Complete
            
            Key Insights:
            - Market Analysis ✅
            - Sentiment Analysis ✅  
            - News Analysis ✅
            - Risk Assessment ✅
            - Final Decision: Available ✅
            
            Generated by TradingAgents Multi-Agent Framework
            """
            
            st.text_area("Shareable Summary", summary, height=200)
            st.info("💡 Copy the summary above to share your analysis results!")
        else:
            st.error("❌ No analysis results to share")
    except Exception as e:
        st.error(f"❌ Share failed: {str(e)}")

def run_analysis(ticker, analysis_date, selected_analysts, research_depth, 
                llm_provider, backend_url, shallow_thinker, deep_thinker):
    """Run the trading analysis"""
    
    # Create config
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = research_depth
    config["max_risk_discuss_rounds"] = research_depth
    config["quick_think_llm"] = shallow_thinker
    config["deep_think_llm"] = deep_thinker
    config["backend_url"] = backend_url
    config["llm_provider"] = llm_provider
    
    # Initialize graph with enhanced error handling and debugging
    try:
        loading_placeholder = st.empty()
        with loading_placeholder.container():
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <div class="loading-spinner"></div>
                <h4 style="margin-top: 1rem;">Initializing Analysis...</h4>
                <p>Setting up AI agents and preparing market data...</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Log configuration details
        logger.info(f"Creating TradingAgentsGraph with config: {config}")
        print(f"🔧 Config Details:")
        print(f"   - LLM Provider: {config['llm_provider']}")
        print(f"   - Backend URL: {config['backend_url']}")
        print(f"   - Deep Think LLM: {config['deep_think_llm']}")
        print(f"   - Quick Think LLM: {config['quick_think_llm']}")
        print(f"   - Selected Analysts: {[analyst.value for analyst in selected_analysts]}")
        print(f"   - Max Debate Rounds: {config['max_debate_rounds']}")
        sys.stdout.flush()
        
        # Check for API keys based on provider
        import os
        if config['llm_provider'].lower() == 'openai':
            openai_key = os.getenv('OPENAI_API_KEY')
            if not openai_key:
                st.error("❌ OPENAI_API_KEY environment variable not set!")
                logger.error("OPENAI_API_KEY not found in environment variables") 
                return
            else:
                print(f"✅ OpenAI API Key found: {openai_key[:10]}...")
        
        sys.stdout.flush()
            
        with st.spinner("Loading..."):
            print("🔄 Creating TradingAgentsGraph instance...")
            sys.stdout.flush()
            
            graph = TradingAgentsGraph(
                [analyst.value for analyst in selected_analysts], 
                config=config, 
                debug=True
            )
            
            print("✅ TradingAgentsGraph created successfully!")
            sys.stdout.flush()
            loading_placeholder.empty()
        
        # Create result directory and log files (like CLI version)
        results_dir = Path(config["results_dir"]) / ticker / analysis_date
        results_dir.mkdir(parents=True, exist_ok=True)
        report_dir = results_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        log_file = results_dir / "message_tool.log"
        log_file.touch(exist_ok=True)
        
        print(f"📁 Results directory created: {results_dir}")
        print(f"📁 Reports directory: {report_dir}")
        print(f"📄 Log file: {log_file}")
        sys.stdout.flush()
        
        # Set up file logging decorators (like CLI version)
        def save_message_decorator(obj, func_name):
            func = getattr(obj, func_name)
            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
                timestamp, message_type, content = obj.messages[-1]
                content = str(content).replace("\n", " ")  # Replace newlines with spaces
                with open(log_file, "a", encoding='utf-8') as f:
                    f.write(f"{timestamp} [{message_type}] {content}\n")
            return wrapper
        
        def save_tool_call_decorator(obj, func_name):
            func = getattr(obj, func_name)
            @wraps(func)
            def wrapper(*args, **kwargs):
                func(*args, **kwargs)
                timestamp, tool_name, args = obj.tool_calls[-1]
                args_str = ", ".join(f"{k}={v}" for k, v in args.items()) if isinstance(args, dict) else str(args)
                with open(log_file, "a", encoding='utf-8') as f:
                    f.write(f"{timestamp} [Tool Call] {tool_name}({args_str})\n")
            return wrapper

        def save_report_section_decorator(obj, func_name):
            func = getattr(obj, func_name)
            @wraps(func)
            def wrapper(section_name, content):
                func(section_name, content)
                if section_name in obj.report_sections and obj.report_sections[section_name] is not None:
                    content = obj.report_sections[section_name]
                    if content:
                        file_name = f"{section_name}.md"
                        with open(report_dir / file_name, "w", encoding='utf-8') as f:
                            f.write(content)
                        print(f"💾 Report saved: {report_dir / file_name}")
                        sys.stdout.flush()
            return wrapper

        # Apply decorators to MessageBuffer
        st.session_state.message_buffer.add_message = save_message_decorator(st.session_state.message_buffer, "add_message")
        st.session_state.message_buffer.add_tool_call = save_tool_call_decorator(st.session_state.message_buffer, "add_tool_call")
        st.session_state.message_buffer.update_report_section = save_report_section_decorator(st.session_state.message_buffer, "update_report_section")
        
        # Add initial messages to MessageBuffer
        logger.info(f"🚀 Starting analysis - Ticker: {ticker}, Date: {analysis_date}")
        print(f"\n🚀 ANALYSIS STARTED")
        print(f"📊 Ticker: {ticker}")
        print(f"📅 Date: {analysis_date}") 
        print(f"👥 Analysts: {', '.join(analyst.value for analyst in selected_analysts)}")
        print(f"🔍 Research Depth: {research_depth}")
        print(f"🌐 Provider: {llm_provider}")
        print(f"⚡ Quick Agent: {shallow_thinker}")
        print(f"🧠 Deep Agent: {deep_thinker}")
        print("=" * 60)
        sys.stdout.flush()
        
        st.session_state.message_buffer.add_message("System", f"Selected ticker: {ticker}")
        st.session_state.message_buffer.add_message("System", f"Analysis date: {analysis_date}")
        st.session_state.message_buffer.add_message("System", f"Selected analysts: {', '.join(analyst.value for analyst in selected_analysts)}")
        
        # Set first analyst to in_progress
        first_analyst = f"{selected_analysts[0].value.capitalize()} Analyst"
        st.session_state.message_buffer.update_agent_status(first_analyst, "in_progress")
        
        # Create progress placeholder
        progress_placeholder = st.empty()
        
        # Create main progress container that will be updated in real-time
        main_progress_container = st.empty()
        
        # Create a dedicated debug container
        debug_container = st.empty()
        
        with main_progress_container.container():
            st.info(f"🚀 Starting analysis for {ticker} on {analysis_date}")
            
            # 실시간 디버그 정보를 위한 컨테이너 업데이트
            with debug_container.container():
                st.markdown("### 🔧 초기화 진행상황")
                st.write("📋 분석 시스템 초기화 중...")
            
            # Initialize state
            print("🔄 Creating initial state...")
            sys.stdout.flush()
            
            with debug_container.container():
                st.markdown("### 🔧 초기화 진행상황")
                st.success("✅ TradingAgentsGraph 생성 완료")
                st.info("🔄 초기 상태 생성 중...")
            
            init_agent_state = graph.propagator.create_initial_state(ticker, analysis_date)
            print(f"✅ Initial state created: {list(init_agent_state.keys())}")
            
            with debug_container.container():
                st.markdown("### 🔧 초기화 진행상황")
                st.success("✅ TradingAgentsGraph 생성 완료")
                st.success(f"✅ 초기 상태 생성 완료: {list(init_agent_state.keys())}")
                st.info("🔄 그래프 인수 설정 중...")
            
            print("🔄 Getting graph args...")
            sys.stdout.flush()
            args = graph.propagator.get_graph_args()
            print(f"✅ Graph args: {args}")
            
            with debug_container.container():
                st.markdown("### 🔧 초기화 진행상황")
                st.success("✅ TradingAgentsGraph 생성 완료")
                st.success(f"✅ 초기 상태 생성 완료: {list(init_agent_state.keys())}")
                st.success(f"✅ 그래프 인수 설정 완료: {args}")
                st.info("🔄 스트림 처리 시작 중...")
            
            print("🔄 Starting stream processing...")
            sys.stdout.flush()
            
            # Process the analysis stream with real-time updates
            trace = []
            
            print("🔄 About to start streaming from graph.graph.stream...")
            sys.stdout.flush()
            
            # Update main container to show streaming is starting
            with main_progress_container.container():
                st.success("🚀 Stream starting - real-time updates will begin shortly...")
                st.info("💡 The page will auto-refresh to show progress. Check the terminal for detailed logs.")
            
            with debug_container.container():
                st.markdown("### 🔧 스트림 처리")
                st.info("🔄 스트림 이터레이터 생성 중...")
            
            try:
                stream_iterator = graph.graph.stream(init_agent_state, **args)
                print(f"✅ Stream iterator created: {type(stream_iterator)}")
                print("📺 Real-time UI updates will begin now...")
                sys.stdout.flush()
                
                with debug_container.container():
                    st.markdown("### 🔧 스트림 처리")
                    st.success(f"✅ 스트림 이터레이터 생성 완료: {type(stream_iterator)}")
                    st.info("🔄 실시간 업데이트 시작...")
                
            except Exception as e:
                print(f"❌ Stream iterator creation failed: {str(e)}")
                with debug_container.container():
                    st.markdown("### 🔧 스트림 처리")
                    st.error(f"❌ 스트림 이터레이터 생성 실패: {str(e)}")
                    st.code(f"Error: {type(e).__name__}: {str(e)}")
                raise e
            
            # Create containers for real-time updates
            status_placeholder = st.empty()
            progress_placeholder = st.empty()
            
            for chunk_count, chunk in enumerate(stream_iterator):
                logger.info(f"📦 Processing chunk {chunk_count + 1}")
                print(f"📦 Chunk {chunk_count + 1}: {list(chunk.keys())}")
                print(f"📦 Chunk content preview: {str(chunk)[:500]}...")
                sys.stdout.flush()
                
                # Update debug container with chunk information
                with debug_container.container():
                    st.markdown("### 🔧 스트림 처리")
                    st.success(f"✅ 스트림 이터레이터 생성 완료")
                    st.info(f"🔄 청크 {chunk_count + 1} 처리 중: {', '.join(chunk.keys())}")
                    if chunk.keys():
                        st.code(f"청크 키: {list(chunk.keys())}")
                        # 청크 내용 미리보기
                        chunk_preview = str(chunk)[:300] + "..." if len(str(chunk)) > 300 else str(chunk)
                        st.text_area("청크 내용 미리보기", chunk_preview, height=100, key=f"chunk_preview_{chunk_count}")
                
                # Update status in real-time
                with status_placeholder.container():
                    st.info(f"🔄 Processing chunk {chunk_count + 1}: {', '.join(chunk.keys())}")
                    st.caption(f"청크 처리 진행률: {chunk_count + 1} 개 처리됨")
                
                if len(chunk["messages"]) > 0:
                    # Get the last message from the chunk
                    last_message = chunk["messages"][-1]
                    
                    # Extract message content and type
                    if hasattr(last_message, "content"):
                        content = extract_content_string(last_message.content)
                        msg_type = "Reasoning"
                    else:
                        content = str(last_message)
                        msg_type = "System"
                    
                    # Add message to buffer
                    st.session_state.message_buffer.add_message(msg_type, content)
                    
                    # If it's a tool call, add it to tool calls
                    if hasattr(last_message, "tool_calls"):
                        for tool_call in last_message.tool_calls:
                            # Handle both dictionary and object tool calls
                            if isinstance(tool_call, dict):
                                st.session_state.message_buffer.add_tool_call(
                                    tool_call["name"], tool_call["args"]
                                )
                            else:
                                st.session_state.message_buffer.add_tool_call(tool_call.name, tool_call.args)
                    
                    # Update agent status and reports using CLI logic
                    update_agent_status_from_chunk(chunk, selected_analysts)
                    
                    # Update progress display in real-time
                    with progress_placeholder.container():
                        # Show current agent
                        if st.session_state.message_buffer.current_agent:
                            st.success(f"🎯 Current: **{st.session_state.message_buffer.current_agent}**")
                        
                        # Show progress stats
                        completed_agents = sum(1 for status in st.session_state.message_buffer.agent_status.values() if status == "completed")
                        total_agents = len(st.session_state.message_buffer.agent_status)
                        progress = completed_agents / total_agents
                        st.progress(progress, text=f"Progress: {completed_agents}/{total_agents} agents completed")
                        
                        # Show latest activity including status changes
                        recent_messages = list(st.session_state.message_buffer.messages)[-5:]
                        if recent_messages:
                            st.markdown("**Recent Activity:**")
                            for timestamp, msg_type, content in recent_messages:
                                if msg_type == "📊 Status":
                                    st.success(f"`{timestamp}` {msg_type}: {str(content)}")
                                else:
                                    st.caption(f"`{timestamp}` {msg_type}: {str(content)[:300]}...")
                    
                    # Force UI update for better responsiveness
                    if chunk_count % 2 == 0:  # Update every 2 chunks
                        # Update the main container with current progress
                        with main_progress_container.container():
                            st.info(f"🔄 Processing chunk {chunk_count + 1}: {', '.join(chunk.keys())}")
                            
                            # Mini progress display
                            completed = sum(1 for s in st.session_state.message_buffer.agent_status.values() if s == "completed") 
                            total = len(st.session_state.message_buffer.agent_status)
                            st.progress(completed / total, text=f"Progress: {completed}/{total}")
                            
                            if st.session_state.message_buffer.current_agent:
                                st.success(f"🎯 Active: {st.session_state.message_buffer.current_agent}")
                        
                        time.sleep(0.1)  # Small delay for UI responsiveness
                
                trace.append(chunk)
                
                # Check if we have final results
                if any(key in chunk for key in ['final_trade_decision', 'risk_debate_state']):
                    with status_placeholder.container():
                        st.success("🎉 Analysis nearing completion...")
            
            # Clear progress placeholders when done
            status_placeholder.empty()
            progress_placeholder.empty()
            
            # Analysis complete
            final_state = trace[-1]
            
            logger.info("🎉 Analysis stream completed successfully")
            print("\n🎉 ANALYSIS STREAM COMPLETED")
            print("=" * 60)
            sys.stdout.flush()
            
            # Mark all agents as completed
            for agent in st.session_state.message_buffer.agent_status:
                st.session_state.message_buffer.update_agent_status(agent, "completed")
            
            st.session_state.message_buffer.add_message("Analysis", f"Completed analysis for {analysis_date}")
            
            # Update final report sections
            for section in st.session_state.message_buffer.report_sections.keys():
                if section in final_state:
                    st.session_state.message_buffer.update_report_section(section, final_state[section])
            
            # Save final complete report (like CLI version)
            if st.session_state.message_buffer.final_report:
                final_report_file = results_dir / "complete_analysis_report.md"
                with open(final_report_file, "w", encoding='utf-8') as f:
                    f.write(f"# TradingAgents Analysis Report\n\n")
                    f.write(f"**Ticker:** {ticker}\n")
                    f.write(f"**Analysis Date:** {analysis_date}\n")
                    f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(st.session_state.message_buffer.final_report)
                print(f"💾 Complete report saved: {final_report_file}")
                sys.stdout.flush()
            
            # Save final state as JSON
            final_state_file = results_dir / "final_state.json"
            with open(final_state_file, "w", encoding='utf-8') as f:
                # Convert to JSON-serializable format
                serializable_state = {}
                for key, value in final_state.items():
                    if isinstance(value, (str, int, float, bool, list, dict)):
                        serializable_state[key] = value
                    else:
                        serializable_state[key] = str(value)
                
                json.dump(serializable_state, f, indent=2, ensure_ascii=False)
            print(f"💾 Final state saved: {final_state_file}")
            sys.stdout.flush()
            
            # Store results
            st.session_state.analysis_results = final_state
            st.session_state.analysis_complete = True
            
            # Store file paths for download
            st.session_state.results_dir = str(results_dir)
            st.session_state.report_dir = str(report_dir)
            st.session_state.log_file = str(log_file)
            
            logger.info("✅ Analysis results stored and UI updated")
            print("✅ ANALYSIS COMPLETE - Results ready!")
            print(f"📁 All files saved to: {results_dir}")
            sys.stdout.flush()
            
            st.success("✅ Analysis Complete!")
            st.rerun()
            
    except ImportError as e:
        st.error("❌ Missing Dependencies")
        st.error("Some required packages are not installed. Please check your environment.")
        st.code(f"ImportError: {str(e)}")
        st.info("💡 Try installing missing packages with: pip install plotly")
        
        # Debug information for import error
        with st.expander("🔧 디버그 정보", expanded=True):
            st.markdown("### 📋 ImportError 디버그 정보")
            st.code(f"에러 타입: {type(e).__name__}")
            st.code(f"에러 메시지: {str(e)}")
            st.markdown("**가능한 해결책:**")
            st.markdown("1. 필요한 패키지를 설치하세요: `pip install -r requirements.txt`")
            st.markdown("2. 가상환경이 활성화되어 있는지 확인하세요")
            st.markdown("3. Python 버전 호환성을 확인하세요")
    
    except ConnectionError as e:
        st.error("🌐 Connection Error")
        st.error("Unable to connect to the required APIs. Please check your internet connection and API keys.")
        st.code(f"ConnectionError: {str(e)}")
        
        # Debug information for connection error
        with st.expander("🔧 디버그 정보", expanded=True):
            st.markdown("### 📋 ConnectionError 디버그 정보")
            st.code(f"에러 타입: {type(e).__name__}")
            st.code(f"에러 메시지: {str(e)}")
            st.markdown("**가능한 해결책:**")
            st.markdown("1. 인터넷 연결을 확인하세요")
            st.markdown("2. API 키가 올바르게 설정되어 있는지 확인하세요")
            st.markdown("3. 방화벽 또는 프록시 설정을 확인하세요")
            
            # Show API key status
            import os
            st.markdown("**API 키 상태:**")
            for key_name in ['OPENAI_API_KEY']:
                key_value = os.getenv(key_name)
                if key_value:
                    st.success(f"✅ {key_name}: 설정됨 ({key_value[:10]}...)")
                else:
                    st.error(f"❌ {key_name}: 설정되지 않음")
    
    except ValueError as e:
        st.error("❌ Configuration Error")
        st.error("Invalid configuration parameters provided.")
        st.code(f"ValueError: {str(e)}")
        
        # Debug information for value error
        with st.expander("🔧 디버그 정보", expanded=True):
            st.markdown("### 📋 ValueError 디버그 정보")
            st.code(f"에러 타입: {type(e).__name__}")
            st.code(f"에러 메시지: {str(e)}")
            st.markdown("**가능한 해결책:**")
            st.markdown("1. 입력 매개변수를 확인하세요")
            st.markdown("2. 날짜 형식이 올바른지 확인하세요")
            st.markdown("3. 선택한 분석가와 설정이 유효한지 확인하세요")
    
    except Exception as e:
        st.error("❌ Unexpected Error")
        st.error("An unexpected error occurred during analysis.")
        
        with st.expander("🔧 디버그 정보", expanded=True):
            st.markdown("### 📋 예상치 못한 오류 디버그 정보")
            st.code(f"에러 타입: {type(e).__name__}")
            st.code(f"에러 메시지: {str(e)}")
            st.exception(e)
            
            st.markdown("**현재 상태:**")
            st.json({
                "분석 완료": st.session_state.get('analysis_complete', False),
                "분석 결과 있음": bool(st.session_state.get('analysis_results')),
                "메시지 수": len(st.session_state.message_buffer.messages),
                "도구 호출 수": len(st.session_state.message_buffer.tool_calls),
                "현재 에이전트": st.session_state.message_buffer.current_agent,
            })
            
            st.markdown("**가능한 해결책:**")
            st.markdown("1. 페이지를 새로고침하세요")
            st.markdown("2. 설정 매개변수를 조정하세요")
            st.markdown("3. 다른 LLM 모델을 시도해보세요")
            st.markdown("4. 터미널에서 자세한 로그를 확인하세요")
        
        st.info("💡 문제가 지속되면 터미널 로그를 확인하고 설정을 다시 검토해주세요.")

def extract_content_string(content):
    """Extract string content from various message formats"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
                elif item.get('type') == 'tool_use':
                    text_parts.append(f"[Tool: {item.get('name', 'unknown')}]")
            else:
                text_parts.append(str(item))
        return ' '.join(text_parts)
    else:
        return str(content)

def update_agent_status_from_chunk(chunk, selected_analysts):
    """Update agent status and reports based on chunk content - CLI style logic"""
    
    # Analyst Team Reports
    if "market_report" in chunk and chunk["market_report"]:
        st.session_state.message_buffer.update_report_section("market_report", chunk["market_report"])
        st.session_state.message_buffer.update_agent_status("Market Analyst", "completed")
        # Set next analyst to in_progress
        if AnalystType.social in selected_analysts:
            st.session_state.message_buffer.update_agent_status("Social Analyst", "in_progress")

    if "sentiment_report" in chunk and chunk["sentiment_report"]:
        st.session_state.message_buffer.update_report_section("sentiment_report", chunk["sentiment_report"])
        st.session_state.message_buffer.update_agent_status("Social Analyst", "completed")
        # Set next analyst to in_progress
        if AnalystType.news in selected_analysts:
            st.session_state.message_buffer.update_agent_status("News Analyst", "in_progress")

    if "news_report" in chunk and chunk["news_report"]:
        st.session_state.message_buffer.update_report_section("news_report", chunk["news_report"])
        st.session_state.message_buffer.update_agent_status("News Analyst", "completed")
        # Set next analyst to in_progress
        if AnalystType.fundamentals in selected_analysts:
            st.session_state.message_buffer.update_agent_status("Fundamentals Analyst", "in_progress")

    if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
        st.session_state.message_buffer.update_report_section("fundamentals_report", chunk["fundamentals_report"])
        st.session_state.message_buffer.update_agent_status("Fundamentals Analyst", "completed")
        # Set all research team members to in_progress
        update_research_team_status("in_progress")

    # Research Team - Handle Investment Debate State
    if "investment_debate_state" in chunk and chunk["investment_debate_state"]:
        debate_state = chunk["investment_debate_state"]

        # Update Bull Researcher status and report
        if "bull_history" in debate_state and debate_state["bull_history"]:
            # Keep all research team members in progress
            update_research_team_status("in_progress")
            # Extract latest bull response
            bull_responses = debate_state["bull_history"].split("\n")
            latest_bull = bull_responses[-1] if bull_responses else ""
            if latest_bull:
                st.session_state.message_buffer.add_message("Reasoning", latest_bull)
                # Update research report with bull's latest analysis
                st.session_state.message_buffer.update_report_section(
                    "investment_plan", f"### Bull Researcher Analysis\n{latest_bull}"
                )

        # Update Bear Researcher status and report
        if "bear_history" in debate_state and debate_state["bear_history"]:
            # Keep all research team members in progress
            update_research_team_status("in_progress")
            # Extract latest bear response
            bear_responses = debate_state["bear_history"].split("\n")
            latest_bear = bear_responses[-1] if bear_responses else ""
            if latest_bear:
                st.session_state.message_buffer.add_message("Reasoning", latest_bear)
                # Update research report with bear's latest analysis
                current_report = st.session_state.message_buffer.report_sections.get('investment_plan', '')
                st.session_state.message_buffer.update_report_section(
                    "investment_plan", f"{current_report}\n\n### Bear Researcher Analysis\n{latest_bear}"
                )

        # Update Research Manager status and final decision
        if "judge_decision" in debate_state and debate_state["judge_decision"]:
            # Keep all research team members in progress until final decision
            update_research_team_status("in_progress")
            st.session_state.message_buffer.add_message("Reasoning", f"Research Manager: {debate_state['judge_decision']}")
            # Update research report with final decision
            current_report = st.session_state.message_buffer.report_sections.get('investment_plan', '')
            st.session_state.message_buffer.update_report_section(
                "investment_plan", f"{current_report}\n\n### Research Manager Decision\n{debate_state['judge_decision']}"
            )
            # Mark all research team members as completed
            update_research_team_status("completed")
            # Set trader to in_progress
            st.session_state.message_buffer.update_agent_status("Trader", "in_progress")

    # Trading Team
    if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
        st.session_state.message_buffer.update_report_section("trader_investment_plan", chunk["trader_investment_plan"])
        st.session_state.message_buffer.update_agent_status("Trader", "completed")
        # Set risk analysts to in_progress
        st.session_state.message_buffer.update_agent_status("Risky Analyst", "in_progress")
        st.session_state.message_buffer.update_agent_status("Neutral Analyst", "in_progress")
        st.session_state.message_buffer.update_agent_status("Safe Analyst", "in_progress")

    # Risk Management Team - Handle Risk Debate State
    if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
        risk_state = chunk["risk_debate_state"]

        # Update Risky Analyst status and report
        if "current_risky_response" in risk_state and risk_state["current_risky_response"]:
            st.session_state.message_buffer.update_agent_status("Risky Analyst", "in_progress")
            st.session_state.message_buffer.add_message("Reasoning", f"Risky Analyst: {risk_state['current_risky_response']}")
            # Update risk report with risky analyst's latest analysis
            st.session_state.message_buffer.update_report_section(
                "final_trade_decision", f"### Risky Analyst Analysis\n{risk_state['current_risky_response']}"
            )

        # Update Safe Analyst status and report
        if "current_safe_response" in risk_state and risk_state["current_safe_response"]:
            st.session_state.message_buffer.update_agent_status("Safe Analyst", "in_progress")
            st.session_state.message_buffer.add_message("Reasoning", f"Safe Analyst: {risk_state['current_safe_response']}")
            # Update risk report with safe analyst's latest analysis
            st.session_state.message_buffer.update_report_section(
                "final_trade_decision", f"### Safe Analyst Analysis\n{risk_state['current_safe_response']}"
            )

        # Update Neutral Analyst status and report
        if "current_neutral_response" in risk_state and risk_state["current_neutral_response"]:
            st.session_state.message_buffer.update_agent_status("Neutral Analyst", "in_progress")
            st.session_state.message_buffer.add_message("Reasoning", f"Neutral Analyst: {risk_state['current_neutral_response']}")
            # Update risk report with neutral analyst's latest analysis
            st.session_state.message_buffer.update_report_section(
                "final_trade_decision", f"### Neutral Analyst Analysis\n{risk_state['current_neutral_response']}"
            )

        # Update Portfolio Manager status and final decision
        if "judge_decision" in risk_state and risk_state["judge_decision"]:
            st.session_state.message_buffer.update_agent_status("Portfolio Manager", "in_progress")
            st.session_state.message_buffer.add_message("Reasoning", f"Portfolio Manager: {risk_state['judge_decision']}")
            # Update risk report with final decision
            st.session_state.message_buffer.update_report_section(
                "final_trade_decision", f"### Portfolio Manager Decision\n{risk_state['judge_decision']}"
            )
            # Mark risk analysts as completed
            st.session_state.message_buffer.update_agent_status("Risky Analyst", "completed")
            st.session_state.message_buffer.update_agent_status("Safe Analyst", "completed")
            st.session_state.message_buffer.update_agent_status("Neutral Analyst", "completed")
            st.session_state.message_buffer.update_agent_status("Portfolio Manager", "completed")

def show_logging_section():
    """별도 로깅 및 디버그 섹션 표시"""
    st.markdown("---")
    st.markdown("---")
    
    # 로깅 및 디버그 헤더
    st.markdown("""
    <div class="hero-section" style="margin: 2rem 0;">
        <h2 style="margin: 0; color: white;">🔍 로깅 및 디버그</h2>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">실시간 활동 모니터링 및 시스템 로그</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 탭으로 구성된 로깅 섹션
    log_tabs = st.tabs(["📊 상태 모니터링", "📄 리포트 뷰어", "🔧 시스템 로그", "⚙️ 디버그 정보"])
    
    # Tab 1: 상태 모니터링
    with log_tabs[0]:
        st.subheader("📊 실시간 상태 모니터링")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_status_monitoring"):
                st.rerun()
        
        # 전체 통계
        col1, col2, col3, col4 = st.columns(4)
        
        total_messages = len(st.session_state.message_buffer.messages)
        total_tools = len(st.session_state.message_buffer.tool_calls)
        llm_calls = sum(1 for _, msg_type, _ in st.session_state.message_buffer.messages if msg_type == "Reasoning")
        reports_count = sum(1 for content in st.session_state.message_buffer.report_sections.values() if content is not None)
        
        with col1:
            st.metric("💬 총 메시지", total_messages, help="전체 메시지 수")
        with col2:
            st.metric("🔧 도구 호출", total_tools, help="도구 호출 횟수")
        with col3:
            st.metric("🧠 LLM 호출", llm_calls, help="LLM 추론 호출")
        with col4:
            st.metric("📋 생성 리포트", reports_count, help="생성된 리포트 수")
        
        # 에이전트 상태 모니터링
        st.markdown("### 👥 에이전트 상태 현황")
        
        # 팀별로 구성
        teams = {
            "👥 분석팀": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
            "🔍 연구팀": ["Bull Researcher", "Bear Researcher", "Research Manager"],
            "💼 트레이딩팀": ["Trader"],
            "⚠️ 리스크 관리팀": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
            "🎯 포트폴리오 관리팀": ["Portfolio Manager"]
        }
        
        for team_name, agents in teams.items():
            with st.expander(f"{team_name} ({len([a for a in agents if st.session_state.message_buffer.agent_status[a] == 'completed'])}/{len(agents)} 완료)", expanded=True):
                # 팀 진행률
                completed = sum(1 for agent in agents if st.session_state.message_buffer.agent_status[agent] == "completed")
                progress = completed / len(agents)
                st.progress(progress, text=f"팀 진행률: {completed}/{len(agents)} ({progress:.1%})")
                
                # 각 에이전트 상태
                for agent in agents:
                    status = st.session_state.message_buffer.agent_status[agent]
                    col_agent, col_status = st.columns([3, 1])
                    
                    with col_agent:
                        st.write(f"**{agent}**")
                    
                    with col_status:
                        if status == "completed":
                            st.success("✅ 완료")
                        elif status == "in_progress":
                            st.info("🔄 진행중")
                        elif status == "error":
                            st.error("❌ 오류")
                        else:
                            st.warning("⏳ 대기중")
        
        # 현재 활성 에이전트
        if st.session_state.message_buffer.current_agent:
            st.markdown("### 🎯 현재 활성 에이전트")
            st.success(f"**{st.session_state.message_buffer.current_agent}**가 작업 중입니다.")
        
        # 최근 상태 변경
        st.markdown("### 🔄 최근 상태 변경")
        status_changes = [msg for msg in st.session_state.message_buffer.messages if msg[1] == "📊 Status"]
        if status_changes:
            for timestamp, _, content in status_changes[-5:]:
                st.info(f"`{timestamp}` {content}")
        else:
            st.caption("아직 상태 변경이 없습니다.")
    
    # Tab 2: 리포트 뷰어
    with log_tabs[1]:
        st.subheader("📄 생성된 리포트 뷰어")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_reports"):
                st.rerun()
        
        section_titles = {
            "market_report": "📈 시장 분석",
            "sentiment_report": "💬 소셜 센티먼트", 
            "news_report": "📰 뉴스 분석",
            "fundamentals_report": "🏢 펀더멘털 분석",
            "investment_plan": "🔍 연구팀 결정",
            "trader_investment_plan": "💼 트레이딩 플랜",
            "final_trade_decision": "🎯 최종 투자 결정"
        }
        
        # 리포트 상태 요약
        available_reports = [(name, content) for name, content in st.session_state.message_buffer.report_sections.items() if content is not None]
        
        if available_reports:
            st.success(f"📊 **{len(available_reports)}/{len(section_titles)}** 리포트가 생성되었습니다.")
            
            # 리포트 선택기
            report_names = [section_titles.get(name, name) for name, _ in available_reports]
            selected_report = st.selectbox("보고 싶은 리포트를 선택하세요:", ["전체 리포트"] + report_names)
            
            if selected_report == "전체 리포트":
                # 전체 리포트 표시
                for section_name, content in available_reports:
                    title = section_titles.get(section_name, section_name)
                    with st.expander(f"{title}", expanded=False):
                        st.markdown(content)
                        
                        # 개별 리포트 다운로드
                        st.download_button(
                            label=f"💾 {title} 다운로드",
                            data=content,
                            file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                            key=f"download_report_{section_name}"
                        )
            else:
                # 선택된 리포트만 표시
                selected_index = report_names.index(selected_report)
                section_name, content = available_reports[selected_index]
                title = section_titles.get(section_name, section_name)
                
                st.markdown(f"### {title}")
                st.markdown(content)
                
                # 다운로드 버튼
                st.download_button(
                    label=f"💾 {title} 다운로드",
                    data=content,
                    file_name=f"{section_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
        else:
            st.info("📋 아직 생성된 리포트가 없습니다. 분석이 완료되면 여기에 리포트가 표시됩니다.")
            
            # 예상 리포트 목록
            st.markdown("### 🔮 예상 리포트 목록:")
            for section_name, title in section_titles.items():
                st.markdown(f"- {title} ⏳")
    
    # Tab 3: 시스템 로그
    with log_tabs[2]:
        st.subheader("🔧 시스템 로그")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_system_logs"):
                st.rerun()
        
        # 로그 파일 정보
        log_file_size = "N/A"
        try:
            import os
            if os.path.exists('streamlit_analysis.log'):
                log_file_size = f"{os.path.getsize('streamlit_analysis.log') // 1024} KB"
        except:
            pass
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📄 로그 파일 크기", log_file_size)
        with col2:
            if st.session_state.get('analysis_complete', False):
                try:
                    if os.path.exists('streamlit_analysis.log'):
                        with open('streamlit_analysis.log', 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        st.download_button(
                            label="📋 로그 파일 다운로드",
                            data=log_content,
                            file_name=f"streamlit_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                            mime="text/plain"
                        )
                except Exception as e:
                    st.warning(f"로그 파일 읽기 실패: {str(e)}")
        
        st.info("💡 Console logs are printed to terminal. Log file: `streamlit_analysis.log`")
        
        # 활동 로그 표시
        st.markdown("### 📜 활동 로그")
        
        all_activity = []
        
        # 메시지와 도구 호출을 시간순으로 결합
        for timestamp, msg_type, content in st.session_state.message_buffer.messages:
            icon = "🧠" if msg_type == "Reasoning" else "💬" if msg_type == "System" else "📊"
            all_activity.append((timestamp, f"{icon} {msg_type}", content))
        
        for timestamp, tool_name, args in st.session_state.message_buffer.tool_calls:
            args_str = f"{tool_name}({str(args)[:150]}...)" if len(str(args)) > 150 else f"{tool_name}({args})"
            all_activity.append((timestamp, "🔧 TOOL", args_str))
        
        # 시간순 정렬 (최신 순)
        all_activity.sort(key=lambda x: x[0], reverse=True)
        
        if all_activity:
            # 활동 수 선택
            activity_count = st.selectbox("표시할 활동 수", [10, 20, 50, 100], index=1, key="activity_count_log")
            
            # 필터링 옵션
            filter_option = st.selectbox("필터링", ["전체", "🧠 Reasoning", "🔧 Tool", "💬 System", "📊 Status"], key="log_filter")
            
            # 필터링 적용
            if filter_option != "전체":
                all_activity = [item for item in all_activity if filter_option.split(' ')[1] in item[1]]
            
            for i, (timestamp, activity_type, content) in enumerate(all_activity[:activity_count]):
                with st.expander(f"`{timestamp}` {activity_type}", expanded=False):
                    content_str = str(content)
                    if len(content_str) > 1000:
                        st.text_area("내용", content_str[:1000] + "...", height=150, key=f"log_content_{i}_{timestamp.replace(':', '')}")
                        if st.button(f"전체 내용 보기", key=f"show_full_{i}"):
                            st.text(content_str)
                    else:
                        st.markdown(content_str)
        else:
            st.info("📋 아직 활동 기록이 없습니다.")
    
    # Tab 4: 디버그 정보
    with log_tabs[3]:
        st.subheader("⚙️ 디버그 정보")
        
        # 새로고침 버튼
        col_refresh1, col_refresh2 = st.columns([4, 1])
        with col_refresh2:
            if st.button("🔄 새로고침", key="refresh_debug_info"):
                st.rerun()
        
        # 세션 상태 정보
        with st.expander("🔍 세션 상태", expanded=False):
            st.json({
                "Session State Keys": list(st.session_state.keys()),
                "Analysis Complete": st.session_state.get('analysis_complete', False),
                "Has Analysis Results": bool(st.session_state.get('analysis_results')),
                "Results Directory": st.session_state.get('results_dir', 'Not Set'),
                "Log File": st.session_state.get('log_file', 'Not Set')
            })
        
        # 메시지 버퍼 상태
        with st.expander("💾 메시지 버퍼 상태", expanded=False):
            st.json({
                "Messages Count": len(st.session_state.message_buffer.messages),
                "Tool Calls Count": len(st.session_state.message_buffer.tool_calls),
                "Current Agent": st.session_state.message_buffer.current_agent,
                "Agent Status": dict(st.session_state.message_buffer.agent_status),
                "Available Reports": [k for k, v in st.session_state.message_buffer.report_sections.items() if v is not None],
                "Report Sections Keys": list(st.session_state.message_buffer.report_sections.keys())
            })
        
        # 성능 메트릭
        with st.expander("📈 성능 메트릭", expanded=False):
            import time
            current_time = time.time()
            
            # 분석 시작 시간 추정 (첫 번째 메시지 시간 기준)
            start_time_str = "N/A"
            duration = "N/A"
            if st.session_state.message_buffer.messages:
                first_message_time = st.session_state.message_buffer.messages[0][0]
                start_time_str = first_message_time
                try:
                    # 시간 차이 계산 (대략적)
                    duration = "분석 진행 중"
                    if st.session_state.get('analysis_complete', False):
                        duration = "분석 완료"
                except:
                    pass
            
            st.json({
                "Analysis Start Time": start_time_str,
                "Duration": duration,
                "Current Time": datetime.datetime.now().strftime("%H:%M:%S"),
                "Messages Rate": f"{len(st.session_state.message_buffer.messages)} messages",
                "Tools Rate": f"{len(st.session_state.message_buffer.tool_calls)} tools",
                "Average Message Length": f"{sum(len(str(content)) for _, _, content in st.session_state.message_buffer.messages) // max(1, len(st.session_state.message_buffer.messages))} chars" if st.session_state.message_buffer.messages else "0 chars"
            })

if __name__ == "__main__":
    main()