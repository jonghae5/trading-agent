"""
Configuration Panel UI Component
"""
import streamlit as st
from typing import Dict, List


class ConfigurationPanel:
    """Handles the configuration sidebar panel for analysis settings"""
    
    def __init__(self):
        self.provider_urls = self._get_provider_urls()
        self.llm_options = self._get_llm_options()
    
    def render(self) -> bool:
        """Render the configuration section in sidebar"""
        st.sidebar.markdown("### 🛠️ Configuration")
        
        # Configuration form
        with st.sidebar.form("config_form"):
            st.markdown("#### 📊 Analysis Settings")
            
            # Get configuration values
            config = self._render_configuration_form()
            
            # Submit button
            submitted = st.form_submit_button("💾 Save Configuration", type="primary")
            
            if submitted:
                if self._validate_and_save_config(config):
                    st.sidebar.success("✅ Configuration saved!")
        
        # Show current configuration status
        return self._render_config_status()
    
    def _render_configuration_form(self) -> Dict:
        """Render the configuration form fields"""
        from streamlit_app import (
            sanitize_ticker, validate_ticker, validate_date_input,
            DEFAULT_TICKER, MAX_TICKER_LENGTH, DEFAULT_RESEARCH_DEPTH,
            get_kst_date
        )
        
        config = {}
        
        # Step 1: Ticker Symbol
        st.markdown("**1. 📈 Ticker Symbol**")
        ticker_input = st.text_input(
            "Enter ticker symbol", 
            value=st.session_state.config.get("ticker", DEFAULT_TICKER),
            help="Stock ticker symbol to analyze (e.g., SPY, TSLA, AAPL)",
            placeholder="Enter symbol...",
            max_chars=MAX_TICKER_LENGTH
        )
        
        # Sanitize and validate ticker input
        ticker = sanitize_ticker(ticker_input)
        if ticker_input and not validate_ticker(ticker):
            st.error("⚠️ Invalid ticker symbol. Use only letters and numbers (max 10 characters).")
        config["ticker"] = ticker
        
        # Step 2: Analysis Date  
        st.markdown("**2. 📅 Analysis Date (KST)**")
        config["analysis_date"] = self._render_date_selector()
        
        # Step 3: Select Analysts
        st.markdown("**3. 👥 Analyst Team**")
        config["analysts"] = self._render_analyst_selection()
        
        # Step 4: Research Depth
        st.markdown("**4. 🔍 Research Depth**")
        config["research_depth"] = self._render_depth_selection()
        
        # Step 5: LLM Provider
        st.write("**5. LLM Provider**")
        config["llm_provider"] = self._render_provider_selection()
        
        # Step 6: Thinking Agents
        st.write("**6. Thinking Agents**")
        shallow_thinker, deep_thinker = self._render_model_selection(config["llm_provider"])
        config["shallow_thinker"] = shallow_thinker
        config["deep_thinker"] = deep_thinker
        config["backend_url"] = self.provider_urls[config["llm_provider"]]
        
        return config
    
    def _render_date_selector(self):
        """Render date selection widget"""
        import datetime
        from streamlit_app import get_kst_date
        
        current_date = st.session_state.config.get("analysis_date")
        kst_today = get_kst_date()
        
        if current_date:
            try:
                default_date = datetime.datetime.strptime(current_date, "%Y-%m-%d").date()
                # 미래 날짜인 경우 오늘 날짜로 조정
                if default_date > kst_today:
                    default_date = kst_today
            except:
                default_date = kst_today
        else:
            default_date = kst_today
            
        analysis_date = st.date_input(
            "Select analysis date",
            value=default_date,
            max_value=kst_today,
            help=f"Date for the analysis (cannot be in future) - Current KST date: {kst_today.strftime('%Y-%m-%d')}"
        )
        
        return analysis_date.strftime("%Y-%m-%d")
    
    def _render_analyst_selection(self):
        """Render analyst selection checkboxes"""
        from cli.models import AnalystType
        
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
        
        return selected_analysts
    
    def _render_depth_selection(self):
        """Render research depth selection"""
        from streamlit_app import DEFAULT_RESEARCH_DEPTH
        
        depth_options = {
            "🌊 Shallow (1 round)": 1,
            "⛰️ Medium (3 rounds)": 3, 
            "🌋 Deep (5 rounds)": 5
        }
        current_depth = st.session_state.config.get("research_depth", DEFAULT_RESEARCH_DEPTH)
        depth_key = next((k for k, v in depth_options.items() if v == current_depth), "⛰️ Medium (3 rounds)")
        
        research_depth = st.selectbox(
            "Select research depth",
            options=list(depth_options.keys()),
            index=list(depth_options.keys()).index(depth_key),
            help="Number of debate rounds for research team"
        )
        
        return depth_options[research_depth]
    
    def _render_provider_selection(self):
        """Render LLM provider selection"""
        current_provider = st.session_state.config.get("llm_provider", "openai").title()
        if current_provider not in self.provider_urls:
            current_provider = "openai"
            
        llm_provider = st.selectbox(
            "Select LLM provider",
            options=list(self.provider_urls.keys()),
            index=list(self.provider_urls.keys()).index(current_provider)
        )
        
        return llm_provider.lower()
    
    def _render_model_selection(self, provider_key):
        """Render model selection for shallow and deep thinkers"""
        if provider_key in self.llm_options:
            shallow_options = self.llm_options[provider_key]["shallow"]
            deep_options = self.llm_options[provider_key]["deep"]
            
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
        
        return shallow_thinker, deep_thinker
    
    def _validate_and_save_config(self, config) -> bool:
        """Validate and save configuration"""
        from streamlit_app import validate_ticker, validate_date_input
        
        validation_errors = []
        
        if not config["ticker"] or not validate_ticker(config["ticker"]):
            validation_errors.append("Invalid ticker symbol")
        
        if not validate_date_input(config["analysis_date"]):
            validation_errors.append("Invalid analysis date")
        
        if not config["analysts"]:
            validation_errors.append("At least one analyst must be selected")
        
        if validation_errors:
            st.sidebar.error("❌ Configuration errors:\\n" + "\\n".join(f"• {error}" for error in validation_errors))
            return False
        
        # Store validated configuration
        st.session_state.config = config
        st.session_state.config_set = True
        return True
    
    def _render_config_status(self) -> bool:
        """Render current configuration status"""
        if st.session_state.config_set and st.session_state.config:
            st.sidebar.success("🎯 Configuration Ready")
            with st.sidebar.expander("📋 Current Settings", expanded=False):
                st.write(f"📊 **Ticker:** {st.session_state.config.get('ticker', 'N/A')}")
                config_date = st.session_state.config.get('analysis_date', 'N/A')
                if config_date != 'N/A':
                    config_date = f"{config_date} (KST)"
                st.write(f"📅 **Date:** {config_date}")
                st.write(f"👥 **Analysts:** {len(st.session_state.config.get('analysts', []))}")
                st.write(f"🔍 **Depth:** {st.session_state.config.get('research_depth', 'N/A')} rounds")
                st.write(f"🤖 **Provider:** {st.session_state.config.get('llm_provider', 'N/A').title()}")
        else:
            st.sidebar.warning("⚠️ Please configure and save settings")
        
        return st.session_state.config_set and len(st.session_state.config.get("analysts", [])) > 0
    
    def _get_provider_urls(self) -> Dict[str, str]:
        """Get provider URL mappings"""
        return {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/",
            "google": "https://generativelanguage.googleapis.com/v1",
            "Openrouter": "https://openrouter.ai/api/v1",
            "Ollama": "http://localhost:11434/v1",
        }
    
    def _get_llm_options(self) -> Dict:
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