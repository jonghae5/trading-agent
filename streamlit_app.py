import streamlit as st
import datetime
import time
import logging
import os
from collections import deque
from dotenv import load_dotenv
import pytz
from typing import Optional, Any
from db_manager import DatabaseManager

# Import UI components
from ui.auth.login_page import LoginPage
from ui.auth.session_manager import SessionManager
from ui.dashboard.welcome_header import WelcomeHeader
from ui.dashboard.configuration_panel import ConfigurationPanel
from ui.dashboard.agent_status import AgentStatusDisplay
from ui.dashboard.metrics_display import MetricsDisplay
from ui.financial.economic_indicators import EconomicIndicators
from ui.reports.report_viewer import ReportViewer
from ui.reports.history_manager import HistoryManager
from ui.reports.report_history import ReportHistory
from ui.utils.styling import get_custom_css
from ui.dashboard.market_dashboard import MarketDashboard

# Security and Configuration Constants
SESSION_DURATION_SECONDS = 3600  # 1 hour
MAX_LOGIN_ATTEMPTS = 5
BLOCK_DURATION_MINUTES = 15
CACHE_TTL_SECONDS = 300  # 5 minutes
MAX_MESSAGE_BUFFER_SIZE = 500
MAX_LOG_DISPLAY_SIZE = 50

# UI Constants
DEFAULT_TICKER = "SPY"
DEFAULT_RESEARCH_DEPTH = 3
MIN_PASSWORD_LENGTH = 8
MAX_TICKER_LENGTH = 10

# Time zone settings
KST = pytz.timezone('Asia/Seoul')

# Environment variables validation
def validate_environment() -> bool:
    """Validate required environment variables are set"""
    required_vars = []  # Add any required env vars here
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    return True

def sanitize_ticker(ticker: str) -> str:
    """Sanitize and validate ticker input"""
    if not ticker:
        return ""
    
    # Remove dangerous characters and limit length
    sanitized = ''.join(c for c in ticker.upper() if c.isalnum())
    return sanitized[:MAX_TICKER_LENGTH]

def validate_ticker(ticker: str) -> bool:
    """Validate ticker format"""
    if not ticker:
        return False
    
    # Basic validation: only alphanumeric, reasonable length
    return (ticker.isalnum() and 
            1 <= len(ticker) <= MAX_TICKER_LENGTH and
            ticker.isascii())

def validate_date_input(date_input: Any) -> bool:
    """Validate date input"""
    if not date_input:
        return False
    
    try:
        if isinstance(date_input, str):
            datetime.datetime.strptime(date_input, "%Y-%m-%d")
        elif hasattr(date_input, 'strftime'):
            # It's a date object
            pass
        else:
            return False
        return True
    except (ValueError, AttributeError):
        return False

def sanitize_log_message(message: str) -> str:
    """Sanitize log messages to prevent log injection"""
    if not isinstance(message, str):
        message = str(message)
    
    # Remove newlines and control characters that could be used for log injection
    sanitized = ''.join(c for c in message if c.isprintable() and c not in '\n\r\t')
    
    # Limit length to prevent log spam
    return sanitized[:1000] + "..." if len(sanitized) > 1000 else sanitized

def get_kst_now() -> datetime.datetime:
    """현재 KST 시간을 반환 (timezone-aware)"""
    return datetime.datetime.now(KST)

def get_kst_naive_now():
    """현재 KST 시간을 naive datetime으로 반환"""
    return get_kst_now().replace(tzinfo=None)

def to_kst_string(dt):
    """datetime을 KST 문자열로 변환"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        # naive datetime은 KST로 가정
        dt = KST.localize(dt)
    else:
        # timezone-aware datetime을 KST로 변환
        dt = dt.astimezone(KST)
    return dt.strftime("%Y-%m-%d %H:%M:%S KST")

def get_kst_date():
    """현재 KST 날짜를 date 객체로 반환"""
    return get_kst_now().date()


# Load environment variables
load_dotenv()

# Import required modules from the trading system
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    from cli.models import AnalystType
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

# Enhanced Custom CSS for modern, professional trading dashboard design
st.markdown(get_custom_css(), unsafe_allow_html=True)

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

# Initialize Database Manager with error handling
@st.cache_resource
def get_db_manager() -> Optional[DatabaseManager]:
    """Initialize database manager with error handling"""
    try:
        db_manager = DatabaseManager()
        return db_manager
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.error(f"Failed to initialize database manager: {error_msg}")
        logger.error(f"[DATABASE] Initialization failed: {error_msg}")
        return None

# DB 매니저 인스턴스
db_manager = get_db_manager()

# Check if database is available
if db_manager is None:
    st.error("❌ Database is not available. Some features may not work correctly.")
    st.stop()

def get_session_file(username=None):
    """Get session file path for specific user"""
    if username:
        return f".session_{username}.json"
    return ".current_session.json"

def save_session():
    """세션 저장 - DB 기반으로 변경되어 더이상 필요 없음"""
    # DB 매니저가 세션을 자동으로 관리하므로 별도 저장 불필요
    pass

def load_session():
    """Load session from database - check both session_state and query params"""
    # 먼저 session_state에서 세션 ID 확인
    session_id = getattr(st.session_state, 'session_id', None)
    
    # session_state에 없으면 query params에서 확인 (새로고침 대응)
    if not session_id:
        query_params = st.query_params
        session_id = query_params.get('session_id')
        
    if session_id:
        try:
            # DB에서 세션 유효성 검사
            username = db_manager.validate_session(session_id)
            
            if username:
                # 유효한 세션 - 상태 복원
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.session_id = session_id
                st.session_state.login_time = get_kst_naive_now()  # 현재 시간으로 갱신
                st.session_state.session_duration = 3600  # 1시간
                
                # URL에 세션 ID 유지 (새로고침 대응)
                st.query_params['session_id'] = session_id
                
                logger.info(f"[SESSION] DB session restored for {username}")
                return True
            else:
                # 세션 만료 또는 무효 - URL에서도 제거
                st.session_state.session_id = None
                if 'session_id' in st.query_params:
                    del st.query_params['session_id']
                logger.info(f"[SESSION] DB session expired or invalid: {session_id[:8] if session_id else 'None'}")
                
        except Exception as e:
            logger.error(f"[SESSION] Failed to validate DB session {session_id[:8] if session_id else 'None'}: {e}")
            st.session_state.session_id = None
            if 'session_id' in st.query_params:
                del st.query_params['session_id']
    
    # 기존 파일 세션 정리 (한번만 실행)
    cleanup_old_file_sessions()
    
    return False

def cleanup_old_file_sessions():
    """기존 파일 기반 세션 정리 (DB 전환 완료 후)"""
    try:
        session_files = [f for f in os.listdir('.') if f.startswith('.session_') and f.endswith('.json')]
        
        for session_file in session_files:
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    logger.info(f"[SESSION] Cleaned up old file session: {session_file}")
                except Exception as e:
                    logger.error(f"[SESSION] Failed to remove old session file {session_file}: {e}")
    except Exception as e:
        logger.error(f"[SESSION] Error during file session cleanup: {e}")

def clear_session():
    """Clear current user session from database"""
    session_id = getattr(st.session_state, 'session_id', None)
    username = getattr(st.session_state, 'username', None)
    
    if session_id:
        try:
            # DB에서 세션 무효화
            db_manager.invalidate_session(session_id)
            logger.info(f"[SESSION] DB session invalidated for {username}: {session_id[:8]}")
        except Exception as e:
            logger.error(f"[SESSION] Failed to invalidate DB session {session_id[:8] if session_id else 'None'}: {e}")
    
    # URL에서 세션 ID 제거
    if 'session_id' in st.query_params:
        del st.query_params['session_id']
    
    # 기존 파일 세션도 정리 (호환성)
    cleanup_old_file_sessions()

# Authentication functions
def init_auth_session_state():
    """Initialize authentication session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'blocked_until' not in st.session_state:
        st.session_state.blocked_until = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None
    if 'session_duration' not in st.session_state:
        st.session_state.session_duration = SESSION_DURATION_SECONDS

def is_session_expired():
    """Check if user session has expired using database"""
    if not st.session_state.authenticated:
        return False
    
    session_id = getattr(st.session_state, 'session_id', None)
    
    if not session_id:
        # 세션 ID가 없으면 만료된 것으로 간주
        return True
    
    # DB에서 세션 유효성 재검증
    username = db_manager.validate_session(session_id)
    
    if not username:
        # 세션 만료 또는 무효 - 간단하게 로그아웃 처리
        expired_user = st.session_state.get('username', 'Unknown')
        
        # Clear session
        clear_session()
        
        # Stop any running analysis
        if st.session_state.get('analysis_running', False):
            st.session_state.analysis_running = False
            st.session_state.stream_processing = False
        
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.session_id = None
        st.session_state.login_time = None
        
        logger.info(f"[AUTH] Session expired for {expired_user}")
        return True
    
    # 세션이 유효하면 사용자 정보 동기화
    if username != st.session_state.username:
        st.session_state.username = username
    
    return False

def is_blocked():
    """Check if user is currently blocked from logging in"""
    if st.session_state.blocked_until is None:
        return False
    
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

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with username and password using database"""
    try:
        # Input validation
        if not username or not password:
            return False
        
        # Sanitize inputs to prevent injection
        username = sanitize_log_message(username.strip())
        
        # Basic validation
        if len(username) > 50 or len(password) < MIN_PASSWORD_LENGTH:
            return False
        
        if db_manager.verify_user(username, password):
            # 인증 성공 - 세션 생성
            session_id = db_manager.create_session(username, duration_hours=1)
            
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.session_id = session_id
            st.session_state.login_attempts = 0
            st.session_state.login_time = get_kst_naive_now()
            st.session_state.blocked_until = None
            
            # URL에 세션 ID 추가 (새로고침 대응)
            st.query_params['session_id'] = session_id
            
            logger.info(f"[AUTH] User {username} successfully authenticated at {to_kst_string(get_kst_now())} - session will last 1 hour")
            return True
        else:
            st.session_state.login_attempts += 1
            logger.warning(f"[AUTH] Failed login attempt for {username}: {st.session_state.login_attempts}/5")
            
            # 클라이언트 사이드 차단
            if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
                st.session_state.blocked_until = get_kst_naive_now() + datetime.timedelta(minutes=BLOCK_DURATION_MINUTES)
                logger.warning(f"[AUTH] User blocked for {MAX_LOGIN_ATTEMPTS} failed attempts ({BLOCK_DURATION_MINUTES} minutes)")
            
            return False
    except Exception as e:
        logger.error(f"[AUTH] Authentication error for {username}: {e}")
        st.session_state.login_attempts += 1
        return False


# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False
    
    if 'message_buffer' not in st.session_state:
        st.session_state.message_buffer = {
            'messages': deque(maxlen=MAX_MESSAGE_BUFFER_SIZE),
            'tool_calls': deque(maxlen=MAX_MESSAGE_BUFFER_SIZE),
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




def add_message(msg_type: str, content: str):
    """Add message to buffer"""
    timestamp = get_kst_naive_now().strftime("%H:%M:%S KST")
    
    # Sanitize content for security
    safe_content = sanitize_log_message(str(content))
    safe_msg_type = sanitize_log_message(str(msg_type))
    
    st.session_state.message_buffer['messages'].append((timestamp, safe_msg_type, safe_content))
    if msg_type == "Reasoning":
        st.session_state.message_buffer['llm_call_count'] += 1
    
    # Log the message with sanitized content
    log_content = safe_content[:200] + "..." if len(safe_content) > 200 else safe_content
    logger.info(f"[{safe_msg_type}] {log_content}")

def add_tool_call(tool_name: str, args: dict):
    """Add tool call to buffer"""
    timestamp = get_kst_naive_now().strftime("%H:%M:%S KST")
    
    # Sanitize inputs
    safe_tool_name = sanitize_log_message(str(tool_name))
    safe_args = {sanitize_log_message(str(k)): sanitize_log_message(str(v)) for k, v in (args or {}).items()}
    
    st.session_state.message_buffer['tool_calls'].append((timestamp, safe_tool_name, safe_args))
    st.session_state.message_buffer['tool_call_count'] += 1
    
    # Log the tool call with sanitized content
    args_str = str(safe_args)[:100] + "..." if len(str(safe_args)) > 100 else str(safe_args)
    logger.info(f"[TOOL] {safe_tool_name} called with args: {args_str}")

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
        
        # Initialize the graph and store in session state
        graph = TradingAgentsGraph(
            [analyst.value for analyst in config["analysts"]], 
            config=full_config, 
            debug=True
        )
        st.session_state.graph = graph
        
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

def get_session_info():
    """Get current session information"""
    if not st.session_state.authenticated or st.session_state.login_time is None:
        return None
    
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

def main() -> None:
    """Main Streamlit application with enhanced security and error handling"""
    try:
        # Environment validation first
        if not validate_environment():
            st.error("❌ Environment validation failed. Please check configuration.")
            st.stop()
        
        # Initialize authentication first
        init_auth_session_state()
        
        # Try to restore session from database
        if not st.session_state.authenticated:
            load_session()
        
        # Check if session expired
        if is_session_expired():
            clear_session()
            st.error("🔒 Your session has expired. Please log in again.")
            LoginPage(db_manager).render()
            return
        
        # Check authentication
        if not st.session_state.authenticated:
            LoginPage(db_manager).render()
            return
            
    except Exception as e:
        error_msg = sanitize_log_message(str(e))
        st.error(f"❌ Application initialization failed: {error_msg}")
        logger.error(f"[MAIN] Initialization error: {error_msg}")
        st.stop()
    
    # Initialize main session state
    init_session_state()
    
    # Add session info and logout button in sidebar
    with st.sidebar:
        # Session information
        current_user, session_info = SessionManager(db_manager=db_manager).render_session_info()   
        SessionManager(db_manager=db_manager).render_logout_button(current_user=current_user)

    # Welcome header
    WelcomeHeader.render()
    # Configuration section (sidebar)
    config_valid = ConfigurationPanel().render()
    
    # Mobile-optimized tabs CSS
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        overflow-x: auto;
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0px 12px;
        font-size: 14px;
        min-width: fit-content;
        white-space: nowrap;
    }
    @media (max-width: 640px) {
        .stTabs [data-baseweb="tab"] {
            font-size: 12px;
            padding: 0px 8px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["🧠 AI분석", "📚 히스토리", "📈 주식분석", "📊 거시경제"])
    
    with tab1:
        # Main content area for AI Analysis
        col1, col2 = st.columns([2, 1])
    
    with col1:
        # Start Analysis Button
        st.subheader("🚦 Analysis Control")
        
        if not st.session_state.analysis_running:
            if st.button("▶️ Start Analysis", disabled=not config_valid, type="primary"):
                if config_valid:
                    st.session_state.analysis_running = True
                    st.session_state.stream_processing = False  # Initialize stream processing flag
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
                    
                    # Generate unique collection names for each run
                    import uuid
                    session_id = str(uuid.uuid4())[:8]  # Short unique ID
                    
                    # Add unique session ID to config for collection naming
                    full_config["session_id"] = session_id
                    
                    # Initialize the graph with unique collection names
                    try:
                        st.session_state.graph = TradingAgentsGraph(
                            [analyst.value for analyst in config["analysts"]], 
                            config=full_config, 
                            debug=True
                        )
                        logger.info(f"[ANALYSIS] Graph initialized with session ID: {session_id}")
                    except Exception as e:
                        st.error(f"❌ Failed to initialize analysis graph: {str(e)}")
                        logger.error(f"[ANALYSIS] Graph initialization failed: {str(e)}")
                        return
                    
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
                st.session_state.stream_processing = False  # Reset stream processing flag
                st.rerun()
        
        # Metrics
        MetricsDisplay.render()
        
        # Configuration Summary
        st.subheader("⚙️ Current Configuration")
        if st.session_state.config:
            config_date = st.session_state.config.get("analysis_date", "N/A")
            if config_date != "N/A":
                config_date = f"{config_date} (KST)"
            
            # Create compact configuration display with custom metrics
            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            
            def custom_metric(label, value):
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
            
            with col_cfg1:
                st.markdown(custom_metric("📊 Ticker", st.session_state.config.get("ticker", "N/A")), unsafe_allow_html=True)
                st.markdown(custom_metric("👥 Analysts", len(st.session_state.config.get("analysts", []))), unsafe_allow_html=True)
            with col_cfg2:
                st.markdown(custom_metric("📅 Date", config_date), unsafe_allow_html=True)
                st.markdown(custom_metric("🔍 Research Depth", f"{st.session_state.config.get('research_depth', 'N/A')} rounds"), unsafe_allow_html=True)
            with col_cfg3:
                st.markdown(custom_metric("🤖 Provider", st.session_state.config.get("llm_provider", "N/A").title()), unsafe_allow_html=True)
        else:
            st.info("No configuration set yet. Please configure in the sidebar.")
        
        # Agent Status
        AgentStatusDisplay.render()
        
        # Reports Section
        ReportViewer().render()
        
    
    with col2:
        # Logging Section
        HistoryManager().render()
    
    with tab2:
        # Report History Tab
        ReportHistory(db_manager).render()
        
    
    with tab3:
        # Market Agent Stock Analysis Tab
        MarketDashboard().render()
    
    with tab4:
        # Financial Indicators Visualization Tab
        EconomicIndicators().render()
        
    
    # Process analysis stream if running
    if st.session_state.analysis_running and hasattr(st.session_state, 'analysis_stream'):
        # Prevent re-entrant generator calls
        if 'stream_processing' not in st.session_state:
            st.session_state.stream_processing = False
        
        if st.session_state.stream_processing:
            return  # Skip if already processing
        
        st.session_state.stream_processing = True
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
            st.session_state.stream_processing = False  # Reset flag before rerun
            st.rerun()
            
        except StopIteration:
            # Analysis completed
            st.session_state.analysis_running = False
            st.session_state.stream_processing = False  # Reset flag
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
            
            # Save analysis to database
            try:
                # Extract final decision using graph's process_signal method
                final_decision = None
                confidence_score = None
                
                final_trade_decision = st.session_state.message_buffer['report_sections'].get('final_trade_decision')
                if final_trade_decision and hasattr(st.session_state, 'graph') and st.session_state.graph:
                    try:
                        # Use graph's process_signal method to extract clean decision
                        final_decision = st.session_state.graph.process_signal(final_trade_decision)
                        
                        # Use graph's extract_confidence method to extract confidence score
                        confidence_score = st.session_state.graph.extract_confidence_score(final_trade_decision)
                    except Exception as e:
                        error_msg = sanitize_log_message(str(e))
                        logger.warning(f"[ANALYSIS] Failed to process signal using graph method: {error_msg}")
                        # Fallback to None if process_signal fails
                        final_decision = "-"
                        confidence_score = "-"
                
                # Create analysis session in DB
                session_id = db_manager.create_analysis_session(
                    username=st.session_state.username,
                    ticker=config['ticker'],
                    analysis_date=config['analysis_date'],
                    config=config
                )
                
                # Save report sections
                for section_type, content in st.session_state.message_buffer['report_sections'].items():
                    if content:
                        db_manager.save_report_section(
                            session_id=session_id,
                            section_type=section_type,
                            agent_name=f"{section_type.replace('_', ' ').title()}",
                            content=content
                        )
                
                # Update session with final results
                db_manager.complete_analysis_session(
                    session_id=session_id,
                    final_decision=final_decision,
                    confidence_score=confidence_score,
                    execution_time_seconds=duration
                )
                
                logger.info(f"[DATABASE] Analysis saved to DB with session_id: {session_id}")
                
            except Exception as db_error:
                logger.error(f"[DATABASE] Failed to save analysis to DB: {db_error}")
                st.warning(f"⚠️ 분석 완료되었으나 DB 저장 실패: {db_error}")
            
            # Log analysis completion
            logger.info(f"[ANALYSIS] Analysis completed for {config['ticker']} in {duration:.2f} seconds")
            logger.info(f"[ANALYSIS] Final stats - LLM calls: {st.session_state.message_buffer['llm_call_count']}, Tool calls: {st.session_state.message_buffer['tool_call_count']}")
            
            st.success("✅ Analysis completed successfully!")
            st.rerun()
            
        except Exception as e:
            st.session_state.analysis_running = False
            st.session_state.stream_processing = False  # Reset flag on error
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
    
    # 자동 새로고침 최소화 - 사용자 경험 개선
    # 세션 만료는 사용자 액션 시에만 체크하도록 변경

if __name__ == "__main__":
    main()