# TradingAgents FastAPI Backend

A high-performance, production-ready FastAPI backend for the TradingAgents system, designed to replace the Streamlit backend and provide real-time trading analysis capabilities.

## Features

### 🔐 Authentication & Security

- JWT-based authentication with refresh tokens
- Session management with database persistence
- Rate limiting and CORS protection
- Input validation and sanitization
- Security headers middleware

### 🗄️ Database Integration

- SQLAlchemy 2.0+ with async support
- Support for PostgreSQL, MySQL, and SQLite
- Database migrations with Alembic
- Connection pooling and error handling

### 📊 Trading Analysis

- Integration with existing TradingAgentsGraph system
- Background task processing for analysis
- Real-time progress tracking
- Configuration validation and management

### ⚡ Real-time Communication

- WebSocket support for live streaming
- Real-time analysis updates
- Agent status broadcasting
- Connection management

### 🚀 Performance & Scalability

- Async/await patterns throughout
- Redis caching and session storage
- Connection pooling
- Horizontal scaling support

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (recommended) or SQLite
- Redis (optional, for caching)

### Installation

1. **Clone and navigate to the backend directory:**

```bash
cd fastapi_backend
```

2. **Create virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize the database:**

```bash
# For development (SQLite)
python -c "from core.database import init_database; import asyncio; asyncio.run(init_database())"

# For production (PostgreSQL)
alembic upgrade head
```

6. **Run the development server:**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:

- **Interactive API Docs:** http://localhost:8000/docs
- **ReDoc Documentation:** http://localhost:8000/redoc
- **OpenAPI Schema:** http://localhost:8000/openapi.json

## API Endpoints

### Authentication (`/api/v1/auth/`)

- `POST /login` - User authentication
- `POST /logout` - User logout
- `POST /refresh` - Refresh access token
- `GET /session/validate` - Validate current session
- `GET /session/info` - Get session information
- `GET /profile` - Get user profile
- `POST /register` - Register new user

### Analysis (`/api/v1/analysis/`)

- `POST /start` - Start new analysis
- `POST /control` - Control analysis (stop/pause/resume)
- `GET /status/{session_id}` - Get analysis status
- `GET /sessions` - List user's analysis sessions
- `GET /{session_id}` - Get specific analysis
- `DELETE /{session_id}` - Delete analysis
- `GET /metrics/summary` - Get analysis metrics
- `GET /config/validate` - Validate analysis configuration

### Reports (`/api/v1/reports/`)

- `GET /history` - Get analysis history
- `GET /{session_id}` - Get analysis report
- `GET /{session_id}/sections` - Get report sections
- `GET /{session_id}/export` - Export analysis report
- `GET /stats/summary` - Get analysis statistics
- `DELETE /{session_id}` - Delete analysis report

### Market Data (`/api/v1/market/`)

- `GET /quote/{ticker}` - Get stock quote
- `GET /quotes` - Get multiple quotes
- `GET /indices` - Get market indices
- `GET /summary` - Get market summary
- `GET /indicators/{ticker}` - Get technical indicators
- `GET /news` - Get financial news
- `GET /sectors` - Get sector performance
- `GET /economic-indicators` - Get economic indicators

### WebSocket (`/api/v1/ws/`)

- `WS /analysis/{session_id}` - Real-time analysis stream
- `WS /notifications` - General notifications
- `GET /stats` - WebSocket statistics

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
DATABASE_URL=postgresql://user:password@localhost/tradingagents

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# External APIs
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
FINNHUB_API_KEY=your-finnhub-key

# Performance
MAX_CONCURRENT_ANALYSES=5
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

### Database Configuration

#### SQLite (Development)

```bash
DATABASE_URL=sqlite:///./trading_agents.db
```

#### PostgreSQL (Production)

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/tradingagents
```

#### MySQL

```bash
DATABASE_URL=mysql://user:password@localhost:3306/tradingagents
```

## Deployment

### Docker Deployment

1. **Build and run with Docker Compose:**

```bash
docker-compose up -d
```

2. **Environment variables for Docker:**

```bash
# Create .env file with production values
SECRET_KEY=production-secret-key
OPENAI_API_KEY=your-key
```

### Production Deployment

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Set environment to production:**

```bash
export ENVIRONMENT=production
export DEBUG=false
```

3. **Run database migrations:**

```bash
alembic upgrade head
```

4. **Start with Gunicorn:**

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Health Checks

- **Basic Health:** `GET /health`
- **Detailed Metrics:** `GET /metrics`

## Architecture

### Project Structure

```
fastapi_backend/
├── main.py                 # FastAPI application entry point
├── core/                   # Core configuration and utilities
│   ├── config.py          # Pydantic settings
│   ├── database.py        # Database configuration
│   └── security.py        # Authentication utilities
├── models/                 # SQLAlchemy models
│   ├── base.py            # Base model class
│   ├── user.py            # User models
│   └── analysis.py        # Analysis models
├── schemas/                # Pydantic schemas
│   ├── auth.py            # Authentication schemas
│   ├── analysis.py        # Analysis schemas
│   └── market.py          # Market data schemas
├── api/                    # API route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── analysis.py        # Analysis endpoints
│   ├── reports.py         # Report endpoints
│   ├── market.py          # Market data endpoints
│   └── websocket.py       # WebSocket endpoints
├── services/               # Business logic services
│   ├── analysis_manager.py    # Analysis management
│   ├── websocket_manager.py   # WebSocket management
│   └── market_data_service.py # Market data service
├── middleware/             # Custom middleware
│   ├── auth.py            # Authentication middleware
│   ├── logging.py         # Logging middleware
│   ├── rate_limit.py      # Rate limiting middleware
│   └── security.py        # Security headers middleware
└── requirements.txt        # Python dependencies
```

### Key Components

#### Database Models

- **User Management:** Users, sessions, preferences
- **Analysis System:** Analysis sessions, reports, agent executions
- **Audit Trail:** Comprehensive logging and tracking

#### Authentication Flow

1. User login with credentials
2. JWT tokens generated (access + refresh)
3. Session stored in database
4. Middleware validates tokens on requests
5. Automatic session refresh

#### Analysis Pipeline

1. Configuration validation
2. Background task creation
3. TradingAgentsGraph integration
4. Real-time progress streaming
5. Results persistence

#### WebSocket Management

- Connection pooling and management
- Real-time message broadcasting
- Subscription-based updates
- Automatic reconnection handling

## Integration with React Frontend

The backend is designed to work seamlessly with the React frontend:

### API Compatibility

- RESTful endpoints matching frontend expectations
- Consistent error handling and response formats
- CORS configuration for local development

### Real-time Features

- WebSocket endpoints for live analysis streaming
- Server-sent events for notifications
- Automatic reconnection support

### State Management

- JWT tokens for stateless authentication
- Session persistence across browser refreshes
- Optimistic UI updates with rollback

## Testing

### Run Tests

```bash
pytest
```

### Test Coverage

```bash
pytest --cov=. --cov-report=html
```

### API Testing

Use the interactive docs at `/docs` or tools like:

- Postman
- curl
- httpx (Python)

## Performance Considerations

### Database Optimization

- Connection pooling
- Query optimization
- Proper indexing
- Async operations

### Caching Strategy

- Redis for session storage
- API response caching
- WebSocket message queuing

### Scalability

- Horizontal scaling support
- Load balancer configuration
- Background task distribution

## Security Features

### Authentication Security

- JWT with RS256 signing
- Refresh token rotation
- Session invalidation
- Rate limiting on login attempts

### API Security

- Input validation and sanitization
- SQL injection prevention
- XSS protection headers
- CORS configuration

### Production Security

- Environment variable management
- Secrets rotation
- Audit logging
- Error message sanitization

## Monitoring and Logging

### Logging

- Structured logging with contextual information
- Request/response logging
- Error tracking and alerting
- Performance metrics

### Health Monitoring

- Database connection health
- Redis connection health
- External API status
- System resource usage

### Metrics Collection

- Request latency and throughput
- Error rates and types
- WebSocket connection counts
- Analysis execution times

## Troubleshooting

### Common Issues

1. **Database Connection Errors**

   ```bash
   # Check database status
   pg_isready -h localhost -p 5432
   ```

2. **Authentication Errors**

   ```bash
   # Verify JWT secret key
   echo $SECRET_KEY
   ```

3. **WebSocket Connection Issues**

   ```bash
   # Check Redis connection
   redis-cli ping
   ```

4. **Analysis Failures**
   ```bash
   # Check trading system imports
   python -c "from tradingagents.graph.trading_graph import TradingAgentsGraph"
   ```

### Debugging

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Support

For issues and questions:

1. Check the logs in `/logs/` directory
2. Verify environment configuration
3. Test database connectivity
4. Check external API keys and quotas

## Contributing

1. Follow the existing code structure
2. Add type hints for all functions
3. Write tests for new features
4. Update documentation
5. Follow PEP 8 style guidelines

## License

This project is part of the TradingAgents system. See the main project LICENSE file for details.
