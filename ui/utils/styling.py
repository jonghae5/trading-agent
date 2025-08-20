"""
CSS Styling and Theme Management for Trading Agents Dashboard
"""

def get_custom_css():
    """Return the complete CSS styling for the dashboard"""
    return """
<style>
    /* CSS Variables for consistent theming */
    :root {
        /* Enhanced color palette */
        --primary-50: #f0f7ff;
        --primary-100: #e0efff;
        --primary-500: #0ea5e9;
        --primary-600: #0284c7;
        --primary-700: #0369a1;
        
        /* Semantic trading colors */
        --success-50: #ecfdf5;
        --success-500: #10b981;
        --success-600: #059669;
        
        --danger-50: #fef2f2;
        --danger-500: #ef4444;
        --danger-600: #dc2626;
        
        /* Enhanced neutral grays */
        --gray-50: #f8fafc;
        --gray-100: #f1f5f9;
        --gray-600: #475569;
        --gray-900: #0f172a;
    }

    /* Global app styling - Enhanced gradient background */
    .stApp {
        background: linear-gradient(135deg, #f0f7ff 0%, #f8fdff 30%, #ffffff 70%, #f8fafc 100%);
        min-height: 100vh;
    }
    
    /* Main content wrapper - Enhanced white container */
    .main .block-container {
        background: #ffffff;
        border-radius: 20px;
        padding: 2.5rem;
        margin: 1rem;
        box-shadow: 
            0 8px 32px rgba(14, 165, 233, 0.08),
            0 4px 16px rgba(14, 165, 233, 0.04);
        border: 1px solid rgba(14, 165, 233, 0.1);
        backdrop-filter: blur(8px);
    }
    
    /* Enhanced typography hierarchy */
    body, .stApp, .main, .stSidebar,
    h1, h2, h3, h4, h5, h6, p, span, div, label, 
    .stMarkdown, .stText, .streamlit-container {
        color: var(--gray-900) !important;
    }
    
    /* Modern heading styles with improved hierarchy */
    h1 {
        color: var(--primary-700) !important;
        font-size: clamp(1.875rem, 4vw, 2.5rem) !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
        line-height: 1.2 !important;
    }
    
    h2 {
        color: var(--primary-600) !important;
        font-size: clamp(1.5rem, 3vw, 1.875rem) !important;
        font-weight: 700 !important;
        letter-spacing: -0.015em !important;
    }
    
    h3 {
        color: var(--primary-600) !important;
        font-size: clamp(1.25rem, 2.5vw, 1.5rem) !important;
        font-weight: 600 !important;
    }
    
    /* Sidebar - Light blue accent */
    .css-1d391kg, .stSidebar {
        background: linear-gradient(180deg, #f5f9ff 0%, #ffffff 100%);
        border-right: 1px solid rgba(135, 206, 250, 0.2);
    }
    
    /* Sidebar content styling */
    .css-1d391kg *, .stSidebar * {
        color: #2c3e50 !important;
    }
    
    /* Clean form elements */
    .stTextInput input, .stSelectbox select, .stDateInput input {
        background: #ffffff !important;
        color: #2c3e50 !important;
        border: 2px solid #e3f2fd !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        transition: all 0.3s ease !important;
        font-weight: 500 !important;
    }
    
    .stTextInput input:focus, .stSelectbox select:focus, .stDateInput input:focus {
        border-color: #42a5f5 !important;
        box-shadow: 0 0 0 3px rgba(66, 165, 245, 0.1) !important;
        outline: none !important;
    }
    
    /* Clean checkboxes */
    .stCheckbox label {
        color: #2c3e50 !important;
        font-weight: 500 !important;
    }
    
    /* Enhanced modern metrics cards */
    .stMetric {
        background: linear-gradient(145deg, #ffffff 0%, var(--gray-50) 100%);
        border: 1px solid rgba(15, 23, 42, 0.05);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 
            0 1px 3px rgba(15, 23, 42, 0.04),
            0 1px 2px rgba(15, 23, 42, 0.06);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        min-height: 100px;
    }
    
    .stMetric::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--primary-500);
        transform: scaleX(0);
        transform-origin: left;
        transition: transform 0.3s ease;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 
            0 8px 25px rgba(15, 23, 42, 0.08),
            0 3px 10px rgba(15, 23, 42, 0.05);
    }
    
    .stMetric:hover::before {
        transform: scaleX(1);
    }
    
    .stMetric label {
        color: var(--gray-600) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.5rem !important;
    }
    
    .stMetric > div > div[data-testid="metric-value"] {
        color: var(--gray-900) !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        line-height: 1 !important;
        margin-bottom: 0.25rem !important;
    }
    
    .stMetric > div > div[data-testid="metric-delta"] {
        color: var(--success-600) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Enhanced agent status cards with modern flow design */
    .agent-status {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.875rem;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid transparent;
        min-width: 120px;
        justify-content: center;
        position: relative;
        overflow: hidden;
    }
    
    .agent-status::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s ease;
    }
    
    .agent-status:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    }
    
    .agent-status:hover::before {
        left: 100%;
    }
    
    .status-pending {
        background: linear-gradient(135deg, #fef3c7, #fbbf24);
        color: #92400e;
        border-color: #f59e0b;
    }
    
    .status-in-progress {
        background: linear-gradient(135deg, #dbeafe, #60a5fa);
        color: #1e40af;
        border-color: #3b82f6;
        animation: pulse-glow 2s infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { 
            box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
            transform: scale(1);
        }
        50% { 
            box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
            transform: scale(1.02);
        }
    }
    
    .status-completed {
        background: linear-gradient(135deg, #d1fae5, #34d399);
        color: #047857;
        border-color: #10b981;
    }
    
    .status-error {
        background: linear-gradient(135deg, #fee2e2, #f87171);
        color: #b91c1c;
        border-color: #ef4444;
    }
    
    /* Agent flow connector */
    .agent-connector {
        display: inline-block;
        width: 20px;
        height: 2px;
        background: linear-gradient(90deg, #e2e8f0, #cbd5e1);
        margin: 0 0.5rem;
        position: relative;
    }
    
    .agent-connector::after {
        content: '→';
        position: absolute;
        right: -8px;
        top: -8px;
        color: #64748b;
        font-size: 0.75rem;
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
    
    /* Enhanced welcome header with modern design */
    .welcome-header {
        text-align: center;
        padding: 4rem 3rem;
        background: linear-gradient(135deg, var(--primary-50) 0%, #ffffff 40%, var(--gray-50) 70%, #ffffff 100%);
        color: var(--primary-700);
        border-radius: 24px;
        margin-bottom: 3rem;
        box-shadow: 
            0 8px 32px rgba(14, 165, 233, 0.08),
            0 4px 16px rgba(14, 165, 233, 0.04);
        border: 2px solid rgba(14, 165, 233, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .welcome-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--primary-500), var(--primary-600), var(--primary-500));
    }
    
    .welcome-header h1 {
        margin-bottom: 1rem;
        font-size: clamp(2rem, 5vw, 3rem) !important;
        font-weight: 800 !important;
        color: var(--primary-700) !important;
        letter-spacing: -0.02em !important;
        background: linear-gradient(135deg, var(--primary-600), var(--primary-700));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .welcome-header h3 {
        margin-bottom: 1.5rem;
        font-weight: 500 !important;
        color: var(--gray-600) !important;
        font-size: clamp(1.125rem, 2.5vw, 1.375rem) !important;
        line-height: 1.4 !important;
    }
    
    .welcome-header p {
        color: var(--gray-600) !important;
        font-size: clamp(0.875rem, 1.5vw, 1rem) !important;
        font-weight: 500 !important;
        line-height: 1.6 !important;
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Enhanced primary buttons with modern design */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-600) 0%, var(--primary-700) 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.875rem 2rem;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 
            0 1px 3px rgba(0, 0, 0, 0.1),
            0 1px 2px rgba(0, 0, 0, 0.06);
        position: relative;
        overflow: hidden;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.6s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 
            0 4px 15px rgba(3, 105, 161, 0.3),
            0 2px 4px rgba(0, 0, 0, 0.06);
        background: linear-gradient(135deg, var(--primary-700) 0%, var(--primary-600) 100%);
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:active {
        transform: translateY(0px);
        box-shadow: 0 2px 8px rgba(3, 105, 161, 0.2);
    }
    
    /* Secondary buttons (Stop button) */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.25);
    }
    
    .stButton > button[kind="secondary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.35);
        background: linear-gradient(135deg, #ee5a52 0%, #ff6b6b 100%);
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
    
    /* Clean secondary buttons */
    .stButton[data-baseweb="button"][kind="secondary"] button {
        background: #ffffff;
        color: #1976d2 !important;
        border: 2px solid #e3f2fd;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton[data-baseweb="button"][kind="secondary"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(66, 165, 245, 0.2);
        background: #f5f9ff;
        border-color: #42a5f5;
    }
    
    /* Clean alert messages */
    .stSuccess {
        background: #f1f8e9;
        border: 2px solid #c8e6c9;
        border-radius: 8px;
        color: #2e7d32 !important;
        box-shadow: 0 2px 8px rgba(76, 175, 80, 0.1);
        padding: 1rem;
    }
    
    .stInfo {
        background: #e3f2fd;
        border: 2px solid #bbdefb;
        border-radius: 8px;
        color: #1976d2 !important;
        box-shadow: 0 2px 8px rgba(66, 165, 245, 0.1);
        padding: 1rem;
    }
    
    .stWarning {
        background: #fff8e1;
        border: 2px solid #ffcc02;
        border-radius: 8px;
        color: #e65100 !important;
        box-shadow: 0 2px 8px rgba(255, 193, 7, 0.1);
        padding: 1rem;
    }
    
    .stError {
        background: #ffebee;
        border: 2px solid #ffcdd2;
        border-radius: 8px;
        color: #c62828 !important;
        box-shadow: 0 2px 8px rgba(244, 67, 54, 0.1);
        padding: 1rem;
    }
    
    /* Preserve text colors in messages */
    .stSuccess *, .stInfo *, .stWarning *, .stError * {
        color: inherit !important;
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
    
    /* Enhanced modern tab system */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--gray-50);
        border-radius: 12px;
        padding: 0.25rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #64748b !important;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(14, 165, 233, 0.05);
        color: var(--primary-600) !important;
        transform: translateY(-1px);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-600), var(--primary-700)) !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
    }
    
    /* Clean DataFrames */
    .stDataFrame {
        background: #ffffff;
        border: 2px solid #e3f2fd;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(66, 165, 245, 0.08);
        overflow: hidden;
    }
    
    .stDataFrame th {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%) !important;
        color: #1976d2 !important;
        font-weight: 700 !important;
        padding: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stDataFrame td {
        color: #2c3e50 !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid #f5f9ff !important;
    }
    
    .stDataFrame tr:hover {
        background: #f5f9ff !important;
    }
    
    /* Enhanced mobile optimization */
    @media (max-width: 768px) {
        /* Main container mobile optimization */
        .main .block-container {
            padding: 1.5rem;
            margin: 0.5rem;
            border-radius: 16px;
        }
        
        /* Welcome header mobile */
        .welcome-header {
            padding: 2rem 1.5rem;
            margin-bottom: 2rem;
        }
        
        /* Chart container mobile optimization */
        .stPlotlyChart {
            width: 100% !important;
            overflow-x: auto;
            touch-action: auto;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        
        /* Enhanced mobile chart handling */
        .js-plotly-plot .plotly {
            touch-action: auto !important;
            user-select: none !important;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            pointer-events: none !important;
        }
        
        /* Improved mobile metrics */
        .stMetric {
            margin-bottom: 1rem !important;
            padding: 1rem !important;
        }
        
        /* Enhanced mobile tabs */
        .stTabs [data-baseweb="tab"] {
            min-width: auto !important;
            font-size: 0.875rem !important;
            padding: 0.75rem 1rem !important;
        }
        
        /* Agent status mobile optimization */
        .agent-status {
            width: 100%;
            margin: 0.75rem 0;
            justify-content: space-between;
            padding: 1rem;
            font-size: 0.875rem;
        }
        
        /* Enhanced mobile columns */
        .stColumns > div {
            padding: 0 0.5rem !important;
        }
        
        /* Mobile buttons */
        .stButton > button {
            width: 100%;
            padding: 1rem 1.5rem;
            font-size: 1rem;
        }
        
        /* Mobile badge styles */
        div[style*="display: flex; flex-wrap: wrap"] {
            gap: 12px !important;
            justify-content: center;
        }
        
        div[style*="min-width: 160px"] {
            min-width: 280px !important;
            font-size: 0.9rem !important;
            text-align: center;
        }
    }
    
    /* Enhanced very small screen optimization */
    @media (max-width: 480px) {
        /* Main container for very small screens */
        .main .block-container {
            padding: 1rem;
            margin: 0.25rem;
            border-radius: 12px;
        }
        
        /* Welcome header very small screens */
        .welcome-header {
            padding: 1.5rem 1rem;
            margin-bottom: 1.5rem;
        }
        
        /* Enhanced tab design for small screens */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem !important;
            padding: 0.6rem 0.8rem !important;
        }
        
        /* Metric cards for small screens */
        .stMetric {
            padding: 0.75rem !important;
            margin-bottom: 0.75rem !important;
        }
        
        .stMetric > div > div[data-testid="metric-value"] {
            font-size: 1.5rem !important;
        }
        
        .stMetric label {
            font-size: 0.75rem !important;
        }
        
        /* Agent status very small screens */
        .agent-status {
            font-size: 0.75rem;
            padding: 0.75rem;
            min-width: 100px;
            margin: 0.5rem 0;
        }
        
        /* Enhanced badges for small screens */
        div[style*="min-width: 160px"] {
            min-width: 250px !important;
            padding: 12px 16px !important;
            font-size: 0.85rem !important;
        }
        
        div[style*="font-size: 1.5em"] {
            font-size: 1.25em !important;
        }
        
        /* Improved buttons for small screens */
        .stButton > button {
            padding: 0.875rem 1.25rem;
            font-size: 0.9rem;
        }
    }
    
    /* Loading states and animations */
    .loading-skeleton {
        background: linear-gradient(90deg, var(--gray-100) 25%, #e2e8f0 50%, var(--gray-100) 75%);
        background-size: 200% 100%;
        animation: loading-shimmer 2s infinite;
        border-radius: 8px;
    }
    
    @keyframes loading-shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    /* Smooth transitions for data updates */
    .data-transition {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Enhanced accessibility */
    *:focus {
        outline: 2px solid var(--primary-500);
        outline-offset: 2px;
        border-radius: 4px;
    }
    
    /* Financial data color coding */
    .positive-change {
        color: var(--success-600);
        background: var(--success-50);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-weight: 600;
    }
    
    .negative-change {
        color: var(--danger-600);
        background: var(--danger-50);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-weight: 600;
    }
    
    .neutral-change {
        color: var(--gray-600);
        background: var(--gray-100);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
"""