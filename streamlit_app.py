import streamlit as st
import datetime
import time
import logging
import os
from pathlib import Path
from collections import deque
import json
import io
from typing import Optional, List, Dict, Any
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import required modules from the trading system
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    from cli.models import AnalystType
    from cli.utils import ANALYST_ORDER
except ImportError as e:
    st.error(f"Failed to import trading modules: {e}")
    st.stop()

# Set page config
st.set_page_config(
    page_title="TradingAgents Dashboard", 
    page_icon="💹",  # 예쁜 이모지로 변경
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Global app styling - Clean white theme */
    .stApp {
        background-color: #ffffff;
        color: #111827;
    }
    
    /* All text elements - consistent black on white */
    body, .stApp, .main, .stSidebar,
    h1, h2, h3, h4, h5, h6, p, span, div, label, 
    .stMarkdown, .stText, .streamlit-container {
        color: #111827 !important;
        background-color: transparent;
    }
    
    /* Force expander content to stay white */
    .streamlit-expanderContent, .streamlit-expanderContent * {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    
    /* Expander open state */
    .streamlit-expander[aria-expanded="true"] .streamlit-expanderContent {
        background-color: #ffffff !important;
    }
    
    /* Main content area */
    .main > div {
        padding-top: 2rem;
        background-color: #ffffff;
    }
    
    /* Sidebar - consistent with main theme */
    .css-1d391kg, .stSidebar {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    /* All sidebar text - black */
    .css-1d391kg *, .stSidebar * {
        color: #111827 !important;
    }
    
    /* Form elements - consistent styling */
    .stTextInput input, .stSelectbox select, .stDateInput input {
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 0.5rem !important;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus, .stDateInput input:focus {
        border-color: #059669 !important;
        box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.1) !important;
    }
    
    /* Checkboxes */
    .stCheckbox label {
        color: #111827 !important;
    }
    
    /* Metrics styling */
    .stMetric {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    .stMetric label {
        color: #111827 !important;
        font-weight: 700 !important;
        font-size: 0.875rem !important;
    }
    
    .stMetric > div > div {
        color: #111827 !important;
    }
    
    .stMetric > div > div[data-testid="metric-value"] {
        color: #111827 !important;
        font-weight: 800 !important;
        font-size: 1.5rem !important;
    }
    
    .stMetric > div > div[data-testid="metric-delta"] {
        color: #374151 !important;
    }
    
    /* Agent status cards */
    .agent-status {
        padding: 0.75rem;
        border-radius: 0.5rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    
    .agent-status:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .status-pending {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        border: 1px solid #f59e0b;
    }
    
    .status-in-progress {
        background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
        color: #1d4ed8;
        border: 1px solid #3b82f6;
    }
    
    .status-completed {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #065f46;
        border: 1px solid #10b981;
    }
    
    .status-error {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #991b1b;
        border: 1px solid #ef4444;
    }
    
    /* Log container */
    .log-container {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
        max-height: 400px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 0.875rem;
        color: #374151;
    }
    
    /* Welcome header */
    .welcome-header {
        text-align: center;
        padding: 2.5rem;
        background: linear-gradient(135deg, #059669 0%, #047857 50%, #065f46 100%);
        color: white;
        border-radius: 1rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
    }
    
    .welcome-header h1 {
        margin-bottom: 0.5rem;
        font-size: 2.5rem;
        font-weight: 800;
    }
    
    .welcome-header h3 {
        margin-bottom: 1rem;
        font-weight: 400;
        opacity: 0.9;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* Form inputs */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        border: 2px solid #e2e8f0;
        border-radius: 0.5rem;
        color: #1f2937;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .stSelectbox > div > div > div {
        background-color: #ffffff;
        border: 2px solid #e2e8f0;
        color: #1f2937;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        color: #1f2937 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background-color: #f8fafc;
        color: #6b7280;
        border-radius: 0.5rem 0.5rem 0 0;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f1f5f9;
        color: #374151;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
    }
    
    /* Buttons - consistent styling with better colors */
    .stButton button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
        color: #ffffff !important;
        border: none;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.4);
        background: linear-gradient(135deg, #047857 0%, #065f46 100%);
    }
    
    /* Success/Info/Warning/Error messages - all with black text */
    .stSuccess {
        background-color: #ecfdf5;
        border: 1px solid #10b981;
        color: #111827 !important;
    }
    
    .stInfo {
        background-color: #f0fdfa;
        border: 1px solid #14b8a6;
        color: #111827 !important;
    }
    
    .stWarning {
        background-color: #fffbeb;
        border: 1px solid #f59e0b;
        color: #111827 !important;
    }
    
    .stError {
        background-color: #fef2f2;
        border: 1px solid #ef4444;
        color: #111827 !important;
    }
    
    /* Ensure all nested elements in messages are black */
    .stSuccess *, .stInfo *, .stWarning *, .stError * {
        color: #111827 !important;
    }
    
    /* Expanders - Analysis Logs and others - keep white background always */
    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    
    .streamlit-expanderHeader svg {
        fill: #111827 !important;
    }
    
    /* Override any dark theme on expander content */
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    
    /* Ensure nested elements in expander stay white */
    .streamlit-expanderContent div,
    .streamlit-expanderContent p,
    .streamlit-expanderContent span,
    .streamlit-expanderContent .stTabs,
    .streamlit-expanderContent .stDataFrame {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    
    /* Sidebar toggle button - always visible */
    .css-1rs6os, .css-17eq0hr, [data-testid="collapsedControl"] {
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 2px solid #111827 !important;
        border-radius: 0.5rem !important;
        padding: 0.5rem !important;
    }
    
    /* Sidebar toggle icon - always black */
    .css-1rs6os svg, .css-17eq0hr svg, [data-testid="collapsedControl"] svg {
        fill: #111827 !important;
        stroke: #111827 !important;
    }
    
    /* Header styling - consistent colors */
    .css-18e3th9, [data-testid="stHeader"] {
        background-color: #ffffff !important;
        color: #111827 !important;
    }
    
    /* App header */
    header[data-testid="stHeader"] {
        background-color: #ffffff !important;
        border-bottom: 1px solid #e2e8f0 !important;
    }
    
    /* Toolbar buttons in header */
    .css-18e3th9 button, [data-testid="stHeader"] button {
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* All header elements */
    .css-18e3th9 *, [data-testid="stHeader"] * {
        color: #111827 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background-color: #f8fafc;
        color: #111827 !important;
        border-radius: 0.5rem 0.5rem 0 0;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f1f5f9;
        color: #111827 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #059669 !important;
        color: #ffffff !important;
    }
    
    /* DataFrames */
    .stDataFrame {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
    }
    
    .stDataFrame th, .stDataFrame td {
        color: #111827 !important;
    }
</style>
""", unsafe_allow_html=True)

# Setup logging
def setup_logging():
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('streamlit_analysis.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Authentication functions
def init_auth_session_state():
    """Initialize authentication session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'blocked_until' not in st.session_state:
        st.session_state.blocked_until = None

def is_blocked():
    """Check if user is currently blocked from logging in"""
    if st.session_state.blocked_until is None:
        return False
    
    current_time = datetime.datetime.now()
    if current_time < st.session_state.blocked_until:
        return True
    else:
        # Unblock user and reset attempts
        st.session_state.blocked_until = None
        st.session_state.login_attempts = 0
        return False

def authenticate_user(password: str) -> bool:
    """Authenticate user with password"""
    auth_key = os.getenv('STREAMLIT_AUTH_KEY', 'default_password')
    
    if password == auth_key:
        st.session_state.authenticated = True
        st.session_state.login_attempts = 0
        logger.info("[AUTH] User successfully authenticated")
        return True
    else:
        st.session_state.login_attempts += 1
        logger.warning(f"[AUTH] Failed login attempt {st.session_state.login_attempts}/5")
        
        if st.session_state.login_attempts >= 5:
            # Block user for 30 minutes
            st.session_state.blocked_until = datetime.datetime.now() + datetime.timedelta(minutes=30)
            logger.warning("[AUTH] User blocked for 5 failed attempts (30 minutes)")
        
        return False

def render_login_page():
    """Render the login page"""
    st.markdown("""
    <div class="welcome-header">
        <h1>🔐 TradingAgents Dashboard</h1>
        <h3>Secure Access Required</h3>
        <p>Please enter your authentication key to continue</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if user is blocked
    if is_blocked():
        time_left = st.session_state.blocked_until - datetime.datetime.now()
        minutes_left = int(time_left.total_seconds() / 60) + 1
        st.error(f"🚫 Access blocked due to too many failed attempts. Try again in {minutes_left} minutes.")
        st.stop()
    
    # Show remaining attempts
    remaining_attempts = 5 - st.session_state.login_attempts
    if st.session_state.login_attempts > 0:
        if remaining_attempts > 0:
            st.warning(f"⚠️ {remaining_attempts} attempt(s) remaining")
        
    # Login form
    with st.form("login_form"):
        st.subheader("🔑 Authentication")
        
        password = st.text_input(
            "Enter Authentication Key", 
            type="password",
            placeholder="Enter your authentication key...",
            help="Get the authentication key from your system administrator"
        )
        
        submitted = st.form_submit_button("🚀 Login", type="primary")
        
        if submitted:
            if not password:
                st.error("❌ Please enter an authentication key")
            else:
                if authenticate_user(password):
                    st.success("✅ Authentication successful! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    remaining = 5 - st.session_state.login_attempts
                    if remaining > 0:
                        st.error(f"❌ Invalid authentication key. {remaining} attempt(s) remaining.")
                    else:
                        st.error("🚫 Too many failed attempts. Access blocked for 30 minutes.")
    
    # Instructions
    st.markdown("---")
    st.markdown("""
    ### 📋 Instructions
    - Enter the authentication key provided by your administrator
    - You have **5 attempts** before being blocked for 30 minutes
    - Contact support if you need assistance accessing the system
    
    ### 🔧 Environment Setup
    Make sure your `.env` file contains:
    ```
    STREAMLIT_AUTH_KEY=your_secure_password_here
    ```
    """)

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False
    
    if 'message_buffer' not in st.session_state:
        st.session_state.message_buffer = {
            'messages': deque(maxlen=200),
            'tool_calls': deque(maxlen=200),
            'agent_status': {
                "Market Analyst": "pending",
                "Social Analyst": "pending", 
                "News Analyst": "pending",
                "Fundamentals Analyst": "pending",
                "Bull Researcher": "pending",
                "Bear Researcher": "pending", 
                "Research Manager": "pending",
                "Trader": "pending",
                "Risky Analyst": "pending",
                "Neutral Analyst": "pending",
                "Safe Analyst": "pending",
                "Portfolio Manager": "pending",
            },
            'current_agent': None,
            'report_sections': {
                "market_report": None,
                "sentiment_report": None,
                "news_report": None,
                "fundamentals_report": None,
                "investment_plan": None,
                "trader_investment_plan": None,
                "final_trade_decision": None,
            },
            'final_state': None,
            'llm_call_count': 0,
            'tool_call_count': 0,
            'analysis_start_time': None,
            'analysis_end_time': None
        }
    
    # Initialize empty config - user will set these
    if 'config' not in st.session_state:
        st.session_state.config = {}
    
    # Initialize configuration state
    if 'config_set' not in st.session_state:
        st.session_state.config_set = False

# Helper functions for configuration
def get_llm_options():
    """Get LLM model options based on provider"""
    return {
        "openai": {
            "shallow": [
                ("GPT-4o-mini - Fast and efficient", "gpt-4o-mini"),
                ("GPT-4.1-nano - Ultra-lightweight", "gpt-4.1-nano"),
                ("GPT-4.1-mini - Compact model", "gpt-4.1-mini"),
                ("GPT-4o - Standard model", "gpt-4o"),
            ],
            "deep": [
                ("GPT-4.1-nano - Ultra-lightweight", "gpt-4.1-nano"),
                ("GPT-4.1-mini - Compact model", "gpt-4.1-mini"),
                ("GPT-4o - Standard model", "gpt-4o"),
                ("o4-mini - Specialized reasoning", "o4-mini"),
                ("o3-mini - Advanced reasoning", "o3-mini"),
                ("o3 - Full advanced reasoning", "o3"),
                ("o1 - Premier reasoning", "o1"),
            ]
        },
        "anthropic": {
            "shallow": [
                ("Claude Haiku 3.5 - Fast inference", "claude-3-5-haiku-latest"),
                ("Claude Sonnet 3.5 - Highly capable", "claude-3-5-sonnet-latest"),
                ("Claude Sonnet 3.7 - Exceptional reasoning", "claude-3-7-sonnet-latest"),
                ("Claude Sonnet 4 - High performance", "claude-sonnet-4-0"),
            ],
            "deep": [
                ("Claude Haiku 3.5 - Fast inference", "claude-3-5-haiku-latest"),
                ("Claude Sonnet 3.5 - Highly capable", "claude-3-5-sonnet-latest"),
                ("Claude Sonnet 3.7 - Exceptional reasoning", "claude-3-7-sonnet-latest"),
                ("Claude Sonnet 4 - High performance", "claude-sonnet-4-0"),
                ("Claude Opus 4 - Most powerful", "claude-opus-4-0"),
            ]
        },
        "google": {
            "shallow": [
                ("Gemini 2.0 Flash-Lite - Cost efficient", "gemini-2.0-flash-lite"),
                ("Gemini 2.0 Flash - Next generation", "gemini-2.0-flash"),
                ("Gemini 2.5 Flash - Adaptive thinking", "gemini-2.5-flash"),
            ],
            "deep": [
                ("Gemini 2.0 Flash-Lite - Cost efficient", "gemini-2.0-flash-lite"),
                ("Gemini 2.0 Flash - Next generation", "gemini-2.0-flash"),
                ("Gemini 2.5 Flash - Adaptive thinking", "gemini-2.5-flash"),
                ("Gemini 2.5 Pro", "gemini-2.5-pro"),
            ]
        }
    }

def get_provider_urls():
    """Get provider URL mappings"""
    return {
        "OpenAI": "https://api.openai.com/v1",
        "Anthropic": "https://api.anthropic.com/",
        "Google": "https://generativelanguage.googleapis.com/v1",
        "Openrouter": "https://openrouter.ai/api/v1",
        "Ollama": "http://localhost:11434/v1",
    }

def render_welcome_header():
    """Render the welcome header"""
    st.markdown("""
    <div class="welcome-header">
        <h1>💹 TradingAgents Dashboard</h1>
        <h3>Multi-Agents LLM Financial Trading Framework</h3>
        <p><strong>Workflow:</strong> 🧑‍💼 Analyst Team ➡️ 🧑‍🔬 Research Team ➡️ 💼 Trader ➡️ 🛡️ Risk Management ➡️ 📊 Portfolio Management</p>
    </div>
    """, unsafe_allow_html=True)

def render_configuration_section():
    """Render the configuration section in sidebar"""
    st.sidebar.markdown("### 🛠️ Configuration")
    
    # Configuration form
    with st.sidebar.form("config_form"):
        st.markdown("#### 📊 Analysis Settings")
        
        # Step 1: Ticker Symbol
        st.markdown("**1. 📈 Ticker Symbol**")
        ticker = st.text_input(
            "Enter ticker symbol", 
            value=st.session_state.config.get("ticker", "SPY"),
            help="Stock ticker symbol to analyze (e.g., AAPL, TSLA, SPY)",
            placeholder="Enter symbol..."
        ).upper()
        
        # Step 2: Analysis Date  
        st.markdown("**2. 📅 Analysis Date**")
        current_date = st.session_state.config.get("analysis_date")
        if current_date:
            try:
                default_date = datetime.datetime.strptime(current_date, "%Y-%m-%d").date()
            except:
                default_date = datetime.date.today()
        else:
            default_date = datetime.date.today()
            
        analysis_date = st.date_input(
            "Select analysis date",
            value=default_date,
            max_value=datetime.date.today(),
            help="Date for the analysis (cannot be in future)"
        )
        
        # Step 3: Select Analysts
        st.markdown("**3. 👥 Analyst Team**")
        selected_analysts = []
        analyst_options = {
            "📈 Market Analyst": AnalystType.MARKET,
            "💬 Social Media Analyst": AnalystType.SOCIAL, 
            "📰 News Analyst": AnalystType.NEWS,
            "📊 Fundamentals Analyst": AnalystType.FUNDAMENTALS
        }
        
        current_analysts = st.session_state.config.get("analysts", [AnalystType.MARKET, AnalystType.SOCIAL, AnalystType.NEWS, AnalystType.FUNDAMENTALS])
        
        # Create two columns for better layout
        col1, col2 = st.columns(2)
        analyst_items = list(analyst_options.items())
        
        for i, (display_name, analyst_type) in enumerate(analyst_items):
            with col1 if i % 2 == 0 else col2:
                if st.checkbox(display_name, value=analyst_type in current_analysts, key=f"analyst_{analyst_type.value}"):
                    selected_analysts.append(analyst_type)
        
        # Step 4: Research Depth
        st.markdown("**4. 🔍 Research Depth**")
        depth_options = {
            "🌊 Shallow (1 round)": 1,
            "⛰️ Medium (3 rounds)": 3, 
            "🌋 Deep (5 rounds)": 5
        }
        current_depth = st.session_state.config.get("research_depth", 3)
        depth_key = next((k for k, v in depth_options.items() if v == current_depth), "⛰️ Medium (3 rounds)")
        
        research_depth = st.selectbox(
            "Select research depth",
            options=list(depth_options.keys()),
            index=list(depth_options.keys()).index(depth_key),
            help="Number of debate rounds for research team"
        )
        
        # Step 5: LLM Provider
        st.write("**5. LLM Provider**")
        provider_urls = get_provider_urls()
        current_provider = st.session_state.config.get("llm_provider", "openai").title()
        if current_provider not in provider_urls:
            current_provider = "OpenAI"
            
        llm_provider = st.selectbox(
            "Select LLM provider",
            options=list(provider_urls.keys()),
            index=list(provider_urls.keys()).index(current_provider)
        )
        
        # Step 6: Thinking Agents
        st.write("**6. Thinking Agents**")
        llm_options = get_llm_options()
        provider_key = llm_provider.lower()
        
        if provider_key in llm_options:
            shallow_options = llm_options[provider_key]["shallow"]
            deep_options = llm_options[provider_key]["deep"]
            
            current_shallow = st.session_state.config.get("shallow_thinker", shallow_options[0][1])
            current_deep = st.session_state.config.get("deep_thinker", deep_options[0][1])
            
            # Ensure current values exist in options
            if not any(opt[1] == current_shallow for opt in shallow_options):
                current_shallow = shallow_options[0][1]
            if not any(opt[1] == current_deep for opt in deep_options):
                current_deep = deep_options[0][1]
            
            shallow_thinker = st.selectbox(
                "⚡ Quick-thinking LLM",
                options=[opt[1] for opt in shallow_options],
                format_func=lambda x: next(opt[0] for opt in shallow_options if opt[1] == x),
                index=[opt[1] for opt in shallow_options].index(current_shallow),
                help="Model for quick reasoning tasks"
            )
            
            deep_thinker = st.selectbox(
                "🧠 Deep-thinking LLM", 
                options=[opt[1] for opt in deep_options],
                format_func=lambda x: next(opt[0] for opt in deep_options if opt[1] == x),
                index=[opt[1] for opt in deep_options].index(current_deep),
                help="Model for complex reasoning tasks"
            )
        else:
            shallow_thinker = "gpt-4o-mini"
            deep_thinker = "gpt-4o"
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Configuration", type="primary")
        
        if submitted:
            # Store configuration
            st.session_state.config = {
                "ticker": ticker,
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "analysts": selected_analysts,
                "research_depth": depth_options[research_depth],
                "llm_provider": llm_provider.lower(),
                "backend_url": provider_urls[llm_provider],
                "shallow_thinker": shallow_thinker,
                "deep_thinker": deep_thinker
            }
            st.session_state.config_set = True
            st.sidebar.success("✅ Configuration saved!")
    
    # Show current configuration status
    if st.session_state.config_set and st.session_state.config:
        st.sidebar.success("🎯 Configuration Ready")
        with st.sidebar.expander("📋 Current Settings", expanded=False):
            st.write(f"📊 **Ticker:** {st.session_state.config.get('ticker', 'N/A')}")
            st.write(f"📅 **Date:** {st.session_state.config.get('analysis_date', 'N/A')}")
            st.write(f"👥 **Analysts:** {len(st.session_state.config.get('analysts', []))}")
            st.write(f"🔍 **Depth:** {st.session_state.config.get('research_depth', 'N/A')} rounds")
            st.write(f"🤖 **Provider:** {st.session_state.config.get('llm_provider', 'N/A').title()}")
    else:
        st.sidebar.warning("⚠️ Please configure and save settings")
    
    return st.session_state.config_set and len(st.session_state.config.get("analysts", [])) > 0

def render_agent_status():
    """Render agent status monitoring"""
    st.markdown("### 🧑‍💻 Agent Status")
    
    # Group agents by team with better icons
    teams = {
        "📈 Analyst Team": ["Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst"],
        "🔬 Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "💼 Trading Team": ["Trader"],
        "🛡️ Risk Management": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
        "📊 Portfolio Management": ["Portfolio Manager"]
    }
    
    # Create responsive columns
    cols = st.columns(len(teams))
    
    for idx, (team_name, agents) in enumerate(teams.items()):
        with cols[idx]:
            st.markdown(f"**{team_name}**")
            
            for agent in agents:
                status = st.session_state.message_buffer['agent_status'].get(agent, "pending")
                
                if status == "pending":
                    status_class = "status-pending"
                    emoji = "⏳"
                    status_text = "Waiting"
                elif status == "in_progress":
                    status_class = "status-in-progress" 
                    emoji = "🔄"
                    status_text = "Working"
                elif status == "completed":
                    status_class = "status-completed"
                    emoji = "✅"
                    status_text = "Done"
                else:
                    status_class = "status-error"
                    emoji = "❌"
                    status_text = "Error"
                
                # Shortened agent names for better display
                agent_display = agent.replace(" Analyst", "").replace(" Researcher", "").replace(" Manager", "")
                
                st.markdown(f"""
                <div class="agent-status {status_class}">
                    <div style="font-size: 1.2em;">{emoji}</div>
                    <div style="font-size: 0.9em; margin: 0.25rem 0;">{agent_display}</div>
                    <div style="font-size: 0.75em; opacity: 0.8;">{status_text}</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

def render_metrics():
    """Render key metrics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🛠️ Tool Calls", 
            st.session_state.message_buffer['tool_call_count']
        )
    
    with col2:
        st.metric(
            "🤖 LLM Calls",
            st.session_state.message_buffer['llm_call_count'] 
        )
    
    with col3:
        reports_count = sum(1 for content in st.session_state.message_buffer['report_sections'].values() if content is not None)
        st.metric("📄 Generated Reports", reports_count)
    
    with col4:
        if st.session_state.message_buffer['analysis_start_time'] and st.session_state.message_buffer['analysis_end_time']:
            duration = st.session_state.message_buffer['analysis_end_time'] - st.session_state.message_buffer['analysis_start_time']
            st.metric("⏱️ Duration", f"{duration:.1f}s")
        elif st.session_state.message_buffer['analysis_start_time']:
            current_duration = time.time() - st.session_state.message_buffer['analysis_start_time']
            st.metric("⏱️ Duration", f"{current_duration:.1f}s")
        else:
            st.metric("⏱️ Duration", "0s")

def render_logging_section():
    """Render collapsible logging section"""
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
                        for msg in list(st.session_state.message_buffer['messages'])[-50:]  # Last 50 messages
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
                    for call in list(st.session_state.message_buffer['tool_calls'])[-50:]  # Last 50 tool calls
                ])
                st.dataframe(tool_calls_df, use_container_width=True, hide_index=True)
            else:
                st.info("No tool calls yet. Start analysis to see tool usage.")

def render_reports_section():
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
            
            for tab_idx, (tab, section) in enumerate(zip(selected_tabs, tabs)):
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

def add_message(msg_type: str, content: str):
    """Add message to buffer"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.message_buffer['messages'].append((timestamp, msg_type, content))
    if msg_type == "Reasoning":
        st.session_state.message_buffer['llm_call_count'] += 1
    
    # Log the message
    logger.info(f"[{msg_type}] {content[:200]}{'...' if len(content) > 200 else ''}")

def add_tool_call(tool_name: str, args: dict):
    """Add tool call to buffer"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.message_buffer['tool_calls'].append((timestamp, tool_name, args))
    st.session_state.message_buffer['tool_call_count'] += 1
    
    # Log the tool call
    logger.info(f"[TOOL] {tool_name} called with args: {str(args)[:100]}{'...' if len(str(args)) > 100 else ''}")

def update_agent_status(agent: str, status: str):
    """Update agent status"""
    if agent in st.session_state.message_buffer['agent_status']:
        st.session_state.message_buffer['agent_status'][agent] = status
        st.session_state.message_buffer['current_agent'] = agent
        
        # Log agent status change
        logger.info(f"[AGENT] {agent} status changed to: {status}")

def update_report_section(section_name: str, content: str):
    """Update report section"""
    if section_name in st.session_state.message_buffer['report_sections']:
        st.session_state.message_buffer['report_sections'][section_name] = content
        
        # Log report section update
        logger.info(f"[REPORT] {section_name} report updated ({len(content)} chars)")

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

def run_analysis():
    """Run analysis directly without threading"""
    try:
        config = st.session_state.config.copy()
        
        # Create config with selected research depth
        full_config = DEFAULT_CONFIG.copy()
        full_config["max_debate_rounds"] = config["research_depth"]
        full_config["max_risk_discuss_rounds"] = config["research_depth"]
        full_config["quick_think_llm"] = config["shallow_thinker"]
        full_config["deep_think_llm"] = config["deep_thinker"]
        full_config["backend_url"] = config["backend_url"]
        full_config["llm_provider"] = config["llm_provider"]
        
        # Initialize the graph
        graph = TradingAgentsGraph(
            [analyst.value for analyst in config["analysts"]], 
            config=full_config, 
            debug=True
        )
        
        # Reset message buffer
        st.session_state.message_buffer['analysis_start_time'] = time.time()
        
        # Reset agent statuses
        for agent in st.session_state.message_buffer['agent_status']:
            update_agent_status(agent, "pending")
        
        # Reset report sections
        for section in st.session_state.message_buffer['report_sections']:
            st.session_state.message_buffer['report_sections'][section] = None
        
        # Add initial messages
        add_message("System", f"Selected ticker: {config['ticker']}")
        add_message("System", f"Analysis date: {config['analysis_date']}")
        add_message("System", f"Selected analysts: {', '.join(analyst.value for analyst in config['analysts'])}")
        
        # Update first analyst to in_progress
        first_analyst = f"{config['analysts'][0].value.capitalize()} Analyst"
        update_agent_status(first_analyst, "in_progress")
        
        # Initialize state and get graph args
        init_agent_state = graph.propagator.create_initial_state(
            config["ticker"], config["analysis_date"]
        )
        args = graph.propagator.get_graph_args()
        
        # Stream the analysis
        trace = []
        
        for chunk in graph.graph.stream(init_agent_state, **args):
            if len(chunk.get("messages", [])) > 0:
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
                add_message(msg_type, content)
                
                # If it's a tool call, add it to tool calls
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        if isinstance(tool_call, dict):
                            add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            add_tool_call(tool_call.name, tool_call.args)
                
                # Update reports and agent status based on chunk content
                # Analyst Team Reports
                if "market_report" in chunk and chunk["market_report"]:
                    update_report_section("market_report", chunk["market_report"])
                    update_agent_status("Market Analyst", "completed")
                
                if "sentiment_report" in chunk and chunk["sentiment_report"]:
                    update_report_section("sentiment_report", chunk["sentiment_report"])
                    update_agent_status("Social Analyst", "completed")
                
                if "news_report" in chunk and chunk["news_report"]:
                    update_report_section("news_report", chunk["news_report"])
                    update_agent_status("News Analyst", "completed")
                
                if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
                    update_report_section("fundamentals_report", chunk["fundamentals_report"])
                    update_agent_status("Fundamentals Analyst", "completed")
                
                # Research Team
                if "investment_debate_state" in chunk and chunk["investment_debate_state"]:
                    debate_state = chunk["investment_debate_state"]
                    
                    if "judge_decision" in debate_state and debate_state["judge_decision"]:
                        update_report_section("investment_plan", debate_state["judge_decision"])
                        update_agent_status("Bull Researcher", "completed")
                        update_agent_status("Bear Researcher", "completed")
                        update_agent_status("Research Manager", "completed")
                
                # Trading Team
                if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
                    update_report_section("trader_investment_plan", chunk["trader_investment_plan"])
                    update_agent_status("Trader", "completed")
                
                # Risk Management Team
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk_state = chunk["risk_debate_state"]
                    
                    if "judge_decision" in risk_state and risk_state["judge_decision"]:
                        update_report_section("final_trade_decision", risk_state["judge_decision"])
                        update_agent_status("Risky Analyst", "completed")
                        update_agent_status("Safe Analyst", "completed")
                        update_agent_status("Neutral Analyst", "completed")
                        update_agent_status("Portfolio Manager", "completed")
                
                # Force UI update after each chunk
                st.rerun()
            
            trace.append(chunk)
        
        # Get final state
        final_state = trace[-1] if trace else {}
        st.session_state.message_buffer['final_state'] = final_state
        st.session_state.message_buffer['analysis_end_time'] = time.time()
        
        # Update all agent statuses to completed
        for agent in st.session_state.message_buffer['agent_status']:
            update_agent_status(agent, "completed")
        
        add_message("Analysis", f"Completed analysis for {config['analysis_date']}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        add_message("Error", f"Analysis failed: {str(e)}")
        # Update all agent statuses to error
        for agent in st.session_state.message_buffer['agent_status']:
            update_agent_status(agent, "error")
        return False
    finally:
        st.session_state.analysis_running = False

def main():
    """Main Streamlit application"""
    # Initialize authentication first
    init_auth_session_state()
    
    # Check authentication
    if not st.session_state.authenticated:
        render_login_page()
        return
    
    # Initialize main session state
    init_session_state()
    
    # Add logout button in sidebar
    with st.sidebar:
        st.markdown("---")
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.authenticated = False
            st.session_state.login_attempts = 0
            logger.info("[AUTH] User logged out")
            st.rerun()
    
    # Welcome header
    render_welcome_header()
    
    # Configuration section (sidebar)
    config_valid = render_configuration_section()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Start Analysis Button
        st.subheader("🚦 Analysis Control")
        
        if not st.session_state.analysis_running:
            if st.button("▶️ Start Analysis", disabled=not config_valid, type="primary"):
                if config_valid:
                    st.session_state.analysis_running = True
                    # Initialize analysis state
                    config = st.session_state.config.copy()
                    
                    # Log analysis start
                    logger.info(f"[ANALYSIS] Starting analysis for {config['ticker']} on {config['analysis_date']}")
                    
                    # Create config with selected research depth
                    full_config = DEFAULT_CONFIG.copy()
                    full_config["max_debate_rounds"] = config["research_depth"]
                    full_config["max_risk_discuss_rounds"] = config["research_depth"]
                    full_config["quick_think_llm"] = config["shallow_thinker"]
                    full_config["deep_think_llm"] = config["deep_thinker"]
                    full_config["backend_url"] = config["backend_url"]
                    full_config["llm_provider"] = config["llm_provider"]
                    
                    # Initialize the graph
                    st.session_state.graph = TradingAgentsGraph(
                        [analyst.value for analyst in config["analysts"]], 
                        config=full_config, 
                        debug=True
                    )
                    
                    # Reset message buffer
                    st.session_state.message_buffer['analysis_start_time'] = time.time()
                    
                    # Reset agent statuses
                    for agent in st.session_state.message_buffer['agent_status']:
                        update_agent_status(agent, "pending")
                    
                    # Reset report sections
                    for section in st.session_state.message_buffer['report_sections']:
                        st.session_state.message_buffer['report_sections'][section] = None
                    
                    # Add initial messages
                    add_message("System", f"Selected ticker: {config['ticker']}")
                    add_message("System", f"Analysis date: {config['analysis_date']}")
                    add_message("System", f"Selected analysts: {', '.join(analyst.value for analyst in config['analysts'])}")
                    
                    # Initialize state and get graph args
                    st.session_state.init_agent_state = st.session_state.graph.propagator.create_initial_state(
                        config["ticker"], config["analysis_date"]
                    )
                    st.session_state.graph_args = st.session_state.graph.propagator.get_graph_args()
                    st.session_state.analysis_stream = st.session_state.graph.graph.stream(st.session_state.init_agent_state, **st.session_state.graph_args)
                    st.session_state.trace = []
                    
                    # Update first analyst to in_progress
                    first_analyst = f"{config['analysts'][0].value.capitalize()} Analyst"
                    update_agent_status(first_analyst, "in_progress")
                    
                    st.rerun()
                else:
                    st.error("Please select at least one analyst before starting analysis.")
        else:
            st.info("Analysis is currently running...")
            if st.button("⏹️ Stop Analysis", type="secondary"):
                st.session_state.analysis_running = False
                st.rerun()
        
        # Metrics
        render_metrics()
        
        # Agent Status
        render_agent_status()
        
        # Reports Section
        render_reports_section()
    
    with col2:
        # Logging Section
        render_logging_section()
        
        # Configuration Summary
        st.subheader("⚙️ Current Configuration")
        if st.session_state.config:
            config_data = {
                "📊 Ticker": st.session_state.config.get("ticker", "N/A"),
                "📅 Date": st.session_state.config.get("analysis_date", "N/A"),
                "👥 Analysts": len(st.session_state.config.get("analysts", [])),
                "🔍 Research Depth": f"{st.session_state.config.get('research_depth', 'N/A')} rounds",
                "🤖 Provider": st.session_state.config.get("llm_provider", "N/A").title()
            }
            
            for key, value in config_data.items():
                st.metric(key, value)
    
    # Process analysis stream if running
    if st.session_state.analysis_running and hasattr(st.session_state, 'analysis_stream'):
        try:
            chunk = next(st.session_state.analysis_stream)
            
            if len(chunk.get("messages", [])) > 0:
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
                add_message(msg_type, content)
                
                # If it's a tool call, add it to tool calls
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        if isinstance(tool_call, dict):
                            add_tool_call(tool_call["name"], tool_call["args"])
                        else:
                            add_tool_call(tool_call.name, tool_call.args)
                
                # Update reports and agent status based on chunk content
                # Analyst Team Reports
                if "market_report" in chunk and chunk["market_report"]:
                    update_report_section("market_report", chunk["market_report"])
                    update_agent_status("Market Analyst", "completed")
                
                if "sentiment_report" in chunk and chunk["sentiment_report"]:
                    update_report_section("sentiment_report", chunk["sentiment_report"])
                    update_agent_status("Social Analyst", "completed")
                
                if "news_report" in chunk and chunk["news_report"]:
                    update_report_section("news_report", chunk["news_report"])
                    update_agent_status("News Analyst", "completed")
                
                if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
                    update_report_section("fundamentals_report", chunk["fundamentals_report"])
                    update_agent_status("Fundamentals Analyst", "completed")
                
                # Research Team
                if "investment_debate_state" in chunk and chunk["investment_debate_state"]:
                    debate_state = chunk["investment_debate_state"]
                    
                    if "judge_decision" in debate_state and debate_state["judge_decision"]:
                        update_report_section("investment_plan", debate_state["judge_decision"])
                        update_agent_status("Bull Researcher", "completed")
                        update_agent_status("Bear Researcher", "completed")
                        update_agent_status("Research Manager", "completed")
                
                # Trading Team
                if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
                    update_report_section("trader_investment_plan", chunk["trader_investment_plan"])
                    update_agent_status("Trader", "completed")
                
                # Risk Management Team
                if "risk_debate_state" in chunk and chunk["risk_debate_state"]:
                    risk_state = chunk["risk_debate_state"]
                    
                    if "judge_decision" in risk_state and risk_state["judge_decision"]:
                        update_report_section("final_trade_decision", risk_state["judge_decision"])
                        update_agent_status("Risky Analyst", "completed")
                        update_agent_status("Safe Analyst", "completed")
                        update_agent_status("Neutral Analyst", "completed")
                        update_agent_status("Portfolio Manager", "completed")
            
            st.session_state.trace.append(chunk)
            
            # Continue processing
            time.sleep(0.1)  # Small delay to prevent overwhelming
            st.rerun()
            
        except StopIteration:
            # Analysis completed
            st.session_state.analysis_running = False
            st.session_state.message_buffer['analysis_end_time'] = time.time()
            
            # Calculate duration
            duration = st.session_state.message_buffer['analysis_end_time'] - st.session_state.message_buffer['analysis_start_time']
            
            # Update all agent statuses to completed
            for agent in st.session_state.message_buffer['agent_status']:
                update_agent_status(agent, "completed")
            
            config = st.session_state.config
            add_message("Analysis", f"Completed analysis for {config['analysis_date']}")
            
            # Get final state
            if st.session_state.trace:
                st.session_state.message_buffer['final_state'] = st.session_state.trace[-1]
            
            # Log analysis completion
            logger.info(f"[ANALYSIS] Analysis completed for {config['ticker']} in {duration:.2f} seconds")
            logger.info(f"[ANALYSIS] Final stats - LLM calls: {st.session_state.message_buffer['llm_call_count']}, Tool calls: {st.session_state.message_buffer['tool_call_count']}")
            
            st.success("✅ Analysis completed successfully!")
            st.rerun()
            
        except Exception as e:
            st.session_state.analysis_running = False
            error_msg = f"Analysis failed: {str(e)}"
            st.error(f"❌ {error_msg}")
            add_message("Error", error_msg)
            
            # Log the error
            logger.error(f"[ANALYSIS] {error_msg}", exc_info=True)
            
            # Update all agent statuses to error
            for agent in st.session_state.message_buffer['agent_status']:
                update_agent_status(agent, "error")
            st.rerun()
    
    # Auto-refresh when analysis is running
    elif st.session_state.analysis_running:
        time.sleep(0.5)
        st.rerun()

if __name__ == "__main__":
    main()