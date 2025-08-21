"""Main FastAPI application entry point."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Static files serving (for production frontend)
from fastapi.staticfiles import StaticFiles

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
from src.core.config import get_settings
from src.core.database import init_database, close_database, health_checker, db_manager
from src.core.security import hash_password, SecurityHeaders
from src.api import api_router
from src.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware
)
from src.models.user import User, UserPreference

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE) if settings.LOG_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


async def run_seeder_if_needed():
    """Run database seeder if no admin users exist."""
    try:
        # Check if any admin users exist
        with db_manager.get_session() as session:
            admin_count = session.query(User).filter(User.is_admin == True).count()
            
            if admin_count > 0:
                logger.info(f"Found {admin_count} admin user(s), skipping seeder")
                return
        
        logger.info("No admin users found, running seeder...")
        
        # Create admin user from environment variables
        username = settings.ADMIN_USERNAME
        password = settings.ADMIN_PASSWORD
        if not password:
            # Generate secure random password if not provided
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            password = ''.join(secrets.choice(alphabet) for _ in range(16))
            logger.warning("No ADMIN_PASSWORD provided. Generated random password - SAVE THIS:")
            logger.warning(f"Admin credentials - Username: {username}, Password: {password}")
        
        email = os.getenv("ADMIN_EMAIL", f"{username}@admin.com")
        full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create admin user
        admin_user = User(
            username=username,
            password_hash=password_hash,
            email=email,
            full_name=full_name,
            is_active=True,
            is_admin=True
        )
        
        with db_manager.get_session() as session:
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            
            # Create default preferences
            default_prefs = [
                ("theme", "light", "string", "ui"),
                ("auto_refresh", "true", "boolean", "ui"),
                ("notifications", "true", "boolean", "ui"),
                ("default_ticker", "AAPL", "string", "analysis"),
                ("research_depth", "3", "number", "analysis"),
            ]
            
            for key, value, pref_type, category in default_prefs:
                preference = UserPreference(
                    user_id=admin_user.id,
                    username=admin_user.username,
                    preference_key=key,
                    preference_value=value,
                    preference_type=pref_type,
                    category=category
                )
                session.add(preference)
            
            session.commit()
            
            logger.info(f"✅ Created admin user: {username}")
            if os.getenv("ADMIN_PASSWORD"):
                logger.info("🔐 Admin user created with provided credentials")
            else:
                logger.info("🔐 Admin user created with generated password (see warning above)")
            
    except Exception as e:
        logger.error(f"Seeder failed: {e}")
        # Don't raise - let the app continue even if seeder fails


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    
    # Startup
    try:
        init_database()
        logger.info("Database initialized successfully")
        
        # Run database seeder if needed
        await run_seeder_if_needed()
        
        # Initialize other services here (Redis, external APIs, etc.)
        
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        close_database()
        logger.info("Database connections closed")
        
        # Clean up other services here
        
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Application shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESC,
    version=settings.VERSION,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan
)

# Security middleware

# CORS middleware - Secure configuration
allowed_origins = [
    "*"
]

# Add production origins from environment
production_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if production_origins and production_origins[0]:  # Check if not empty
    allowed_origins.extend([origin.strip() for origin in production_origins])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRFToken",
        "Cache-Control",
        "Pragma"
    ],
    expose_headers=["*"],
    max_age=3600,
)

# Compression middleware
if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Authentication now handled by FastAPI Depends in endpoints

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if settings.is_production:
    frontend_build_path = os.path.join(project_root, "front", "dist")
    frontend_build_path = os.path.abspath(frontend_build_path)

    if os.path.exists(frontend_build_path):
        # 1️⃣ Static 파일 서빙 (Vite는 assets 디렉토리 사용)
        app.mount("/assets", StaticFiles(directory=os.path.join(frontend_build_path, "assets")), name="assets")

        # 2️⃣ SPA fallback
        from fastapi.responses import FileResponse, JSONResponse
        from starlette.requests import Request

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            # API 경로 제외
            if full_path.startswith("api/v1") or full_path.startswith("api"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            
            # Vite index.html 경로
            index_path = os.path.join(frontend_build_path, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return JSONResponse({"detail": "Frontend index.html not found"}, status_code=404)

        logger.info(f"✅ Serving Vite SPA from: {frontend_build_path}")
    else:
        logger.warning(f"⚠️ Frontend build directory not found: {frontend_build_path}")
        
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not settings.HEALTH_CHECK_ENABLED:
        raise HTTPException(status_code=404, detail="Health check disabled")
    
    health_status = health_checker.check_health()
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(
        content={
            "status": health_status["status"],
            "timestamp": health_status["timestamp"],
            "database": {
                "connection": health_status.get("connection", False),
                "response_time": health_status.get("response_time_seconds", 0)
            },
            "version": settings.VERSION,
            "environment": "production" if settings.is_production else "development"
        },
        status_code=status_code
    )


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring."""
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    # This would integrate with Prometheus or similar monitoring system
    return {
        "requests_total": 0,  # Would be tracked by middleware
        
        "active_analysis_sessions": 0,  # Would be tracked by analysis manager
        "database_pool_size": settings.DATABASE_POOL_SIZE,
        "memory_usage_mb": 0,  # Would be tracked by system monitor
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path)
        },
        headers=SecurityHeaders.get_security_headers()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.is_production:
        message = "Internal server error"
        detail = None
    else:
        message = str(exc)
        detail = exc.__class__.__name__
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": message,
            "detail": detail,
            "path": str(request.url.path)
        },
        headers=SecurityHeaders.get_security_headers()
    )


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )