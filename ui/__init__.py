"""
UI Components for Trading Agents Dashboard

This module provides a clean separation of UI components from business logic,
making the codebase more maintainable and modular.
"""

from .auth.login_page import LoginPage
from .auth.session_manager import SessionManager
from .dashboard.welcome_header import WelcomeHeader
from .dashboard.configuration_panel import ConfigurationPanel
from .dashboard.metrics_display import MetricsDisplay
from .dashboard.agent_status import AgentStatusDisplay
from .financial.market_charts import MarketCharts
from .financial.economic_indicators import EconomicIndicators
from .reports.report_viewer import ReportViewer
from .reports.history_manager import HistoryManager
from .utils.styling import get_custom_css
from .utils.chart_utils import ChartUtils

__all__ = [
    'LoginPage',
    'SessionManager', 
    'WelcomeHeader',
    'ConfigurationPanel',
    'MetricsDisplay',
    'AgentStatusDisplay',
    'MarketCharts',
    'EconomicIndicators',
    'ReportViewer',
    'HistoryManager',
    'get_custom_css',
    'ChartUtils'
]