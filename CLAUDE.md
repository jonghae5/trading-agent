# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingAgents is a multi-agent LLM framework for financial trading analysis, powered by LangGraph. The system uses multiple specialized AI agents (analysts, researchers, traders, risk managers, and portfolio managers) to analyze stocks and make trading decisions. The project consists of three main components:

1. **Core Trading Agents** (`tradingagents/`) - Multi-agent LLM system built with LangGraph
2. **FastAPI Backend** (`back/`) - Production API server for web interface
3. **React Frontend** (`front/`) - Modern dashboard for real-time analysis
4. **CLI** (`cli/`) - Interactive command-line interface

## Development Commands

### Root Project
- **Install dependencies**: `uv sync` (uses uv package manager)
- **Run CLI**: `make cli` or `uv run python -m cli.main`
- **Run Streamlit (legacy)**: `make streamlit`
- **Clean Python cache**: `make clean`

### Backend (`back/`)
- **Install dependencies**: `cd back && make install` (uses uv)
- **Run dev server**: `make run` (starts uvicorn on port 8000 with reload)
- **Deploy in background**: `make deploy`
- **Kill all Python processes**: `make killpy`
- **Database migrations**: `alembic upgrade head`

### Frontend (`front/`)
- **Install dependencies**: `pnpm install` (uses pnpm, not npm)
- **Run dev server**: `pnpm run dev` (Vite on port 5173)
- **Build for production**: `pnpm run build`
- **Lint**: `pnpm run lint`
- **Type check**: `pnpm run typecheck`
- **Run tests**: `pnpm run test`

## High-Level Architecture

### Multi-Agent Trading System Flow

The core system (`tradingagents/`) orchestrates a workflow of specialized agents:

1. **Analyst Team** (Phase I) - Parallel analysis from multiple perspectives:
   - `Market Analyst`: Technical indicators and price action (market_analyst.py)
   - `Social Analyst`: Reddit sentiment analysis (social_media_analyst.py)
   - `News Analyst`: News impact assessment (news_analyst.py)
   - `Fundamentals Analyst`: Financial statements and insider data (fundamentals_analyst.py)

2. **Research Team** (Phase II) - Debate-based decision making:
   - `Bull Researcher`: Generates bullish arguments (bull_researcher.py)
   - `Bear Researcher`: Generates bearish arguments (bear_researcher.py)
   - `Research Manager`: Judges debate and synthesizes decision (research_manager.py)

3. **Trading Team** (Phase III):
   - `Trader`: Creates specific trading plan from research (trader.py)

4. **Risk Management Team** (Phase IV) - Multi-perspective risk debate:
   - `Aggressive Analyst`: High-risk tolerance perspective (aggresive_debator.py)
   - `Conservative Analyst`: Low-risk tolerance perspective (conservative_debator.py)
   - `Neutral Analyst`: Balanced risk perspective (neutral_debator.py)

5. **Portfolio Management** (Phase V):
   - `Portfolio Manager`: Final trade decision and position sizing

### Graph Architecture (`tradingagents/graph/`)

The LangGraph workflow is built using several key components:

- `trading_graph.py`: Main orchestrator class that initializes all agents and creates the graph
- `setup.py`: Defines graph nodes and edges for the agent workflow
- `propagation.py`: Handles forward propagation through the graph
- `reflection.py`: Implements reflection/learning from past trades
- `signal_processing.py`: Extracts trading signals from agent outputs
- `conditional_logic.py`: Routing logic between agents based on state

### Agent State Management (`tradingagents/agents/utils/`)

- `agent_states.py`: Defines TypedDict states (AgentState, InvestDebateState, RiskDebateState)
- `memory.py`: ChromaDB-based memory for agents to learn from past decisions
- Key state fields: `company_of_interest`, `trade_date`, analyst reports, debate histories, and final decisions

### Data Flow Integration (`tradingagents/dataflows/`)

All market data tools are centralized in `interface.py` which provides a `Toolkit` class:
- **Online tools**: Real-time data from APIs (Yahoo Finance, Finnhub, Google News, etc.)
- **Offline tools**: Cached historical data for backtesting
- Individual utilities: `yfin_utils.py`, `finnhub_utils.py`, `reddit_utils.py`, `googlenews_utils.py`, etc.

### FastAPI Backend Architecture (`back/src/`)

Built as a production-ready replacement for the legacy Streamlit interface:

- `main.py`: FastAPI application entry point with middleware stack
- `api/`: Route handlers for auth, analysis, portfolio, stocks, economic data, reports
- `services/`: Business logic (analysis_manager.py orchestrates TradingAgentsGraph execution)
- `models/`: SQLAlchemy ORM models (User, Analysis, Portfolio, StockUniverse)
- `schemas/`: Pydantic models for request/response validation
- `core/`: Configuration (config.py), database (database.py), security (JWT/sessions)
- `middleware/`: Rate limiting, security headers, logging

Database: SQLite (dev) or PostgreSQL (prod) with async SQLAlchemy and Alembic migrations

### React Frontend Architecture (`front/src/`)

Modern dashboard built with React 18 + TypeScript + Vite:

- `pages/`: Route components (Analysis.tsx, Portfolio.tsx, Economics.tsx, News.tsx, etc.)
- `components/`: Reusable UI organized by feature (analysis/, portfolio/, economic/, news/)
- `api/`: HTTP client with axios-like interface (client.ts) and typed API calls
- `stores/`: Zustand state management (analysisStore.ts, authStore.ts, uiStore.ts)
- `types/`: TypeScript interfaces matching backend schemas

Key features: Real-time streaming analysis, Fear & Greed Index, portfolio optimization with efficient frontier, economic indicators, markdown rendering for agent reports

## Configuration

### Trading System Config (`tradingagents/default_config.py`)

```python
DEFAULT_CONFIG = {
    "llm_provider": "openai",  # or "anthropic", "google"
    "deep_think_llm": "gpt-4o",  # Model for complex reasoning
    "quick_think_llm": "gpt-4o",  # Model for fast operations
    "backend_url": "https://api.openai.com/v1",
    "max_debate_rounds": 1,  # Research team debate iterations
    "max_risk_discuss_rounds": 1,  # Risk team debate iterations
    "online_tools": True,  # Use real-time APIs vs cached data
}
```

### Backend Config (`back/src/core/config.py`)

Uses Pydantic Settings with environment variables:
- Security: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- Database: `DATABASE_URL` (supports SQLite, PostgreSQL, MySQL)
- APIs: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`, `FRED_API_KEY`
- Performance: `MAX_CONCURRENT_ANALYSES`, `RATE_LIMIT_REQUESTS_PER_MINUTE`

## Important Notes

### LLM Provider Configuration
When working with the trading system, always check which LLM provider is being used. The system supports OpenAI, Anthropic, Google, Ollama, and OpenRouter. The provider is configured via `config["llm_provider"]` and determines which ChatModel class is instantiated in `trading_graph.py:68-78`.

### Symbol Handling
Stock symbols with spaces (e.g., "Berkshire Hathaway") must be converted to valid ticker symbols before Finnhub API calls. See `back/src/utils/stock_utils.py` for the symbol normalization logic.

### Portfolio Optimization
The backend now uses EWMA (Exponentially Weighted Moving Average) for expected returns calculation instead of the previous mean_historical_return approach. The efficient frontier visualization has been removed from the optimization workflow. See `back/src/services/portfolio_service.py`.

### Memory and Learning
Agents can "remember" past decisions via ChromaDB vector storage (`tradingagents/agents/utils/memory.py`). Call `reflect_and_remember(returns_losses)` after a trade to store the outcome and reasoning for future retrieval.

### Frontend-Backend Integration
The frontend expects specific response formats from the backend API. When modifying backend endpoints, ensure response schemas match the TypeScript interfaces in `front/src/types/index.ts`.

### Database Seeding
The backend includes seeders for stock universe and sample portfolios:
- `back/src/services/stock_seeder.py`: Populates StockUniverse table with major indices
- `back/src/services/portfolio_seeder.py`: Creates sample portfolios for testing

### Economic Analysis Caching
Economic data analysis results are cached in `back/cache/economic_analysis/` to avoid redundant LLM calls. Check this directory if analysis seems stale.

## Testing and Quality

- **Backend**: No test framework currently configured (pytest dependencies in pyproject.toml but no tests/)
- **Frontend**: Vitest + Testing Library configured, run with `pnpm run test`
- **Type Safety**: Frontend uses TypeScript strict mode, backend uses type hints
- **Linting**: Backend uses black/isort/flake8/mypy (configured in pyproject.toml), frontend uses ESLint + Prettier

## Running the Full Stack

1. Start backend: `cd back && make run` (port 8000)
2. Start frontend: `cd front && pnpm run dev` (port 5173)
3. Or use CLI: `make cli` for terminal-based analysis

## Package Manager
This project uses **uv** (not pip/poetry) for Python dependency management and **pnpm** (not npm) for frontend dependencies. Always use `uv sync` and `pnpm install` respectively.
