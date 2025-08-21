"""Configuration management using Pydantic settings."""

import os
from functools import lru_cache
from typing import List, Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import secrets


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    PROJECT_NAME: str = "TradingAgents FastAPI Backend"
    PROJECT_DESC: str = "High-performance backend for trading analysis system"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT tokens"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password policy
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 100
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str = "sqlite:///./trading_agents.db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Background Tasks
    BACKGROUND_TASKS_ENABLED: bool = True
    MAX_CONCURRENT_ANALYSES: int = 5
    ANALYSIS_TIMEOUT_MINUTES: int = 30
    
    # Trading System Integration
    TRADING_GRAPH_TIMEOUT: int = 1800  # 30 minutes
    DEFAULT_RESEARCH_DEPTH: int = 3
    MAX_RESEARCH_DEPTH: int = 10
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [".json", ".csv", ".txt"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # Financial Data APIs
    FINNHUB_API_KEY: Optional[str] = None
    FRED_API_KEY: Optional[str] = None
    YAHOO_FINANCE_ENABLED: bool = True
    
    HEALTH_CHECK_ENABLED: bool = True
    
    # Performance
    ENABLE_GZIP: bool = True
    
    # Development
    DEV_MODE: bool = False
    MOCK_EXTERNAL_APIS: bool = False
    
    # Admin account settings
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "your-secure-admin-password-here"

    # JWT Configuration
    JWT_SECRET_KEY: str = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                # Handle string representation of a list
                import ast
                try:
                    return ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    pass
            # Handle comma-separated string
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        elif v is None:
            return ["*"]
        raise ValueError("CORS_ORIGINS must be a list or comma-separated string")
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        
        # Convert relative SQLite paths to absolute
        if v.startswith("sqlite:///./"):
            import os
            db_path = v.replace("sqlite:///./", "")
            abs_path = os.path.abspath(db_path)
            v = f"sqlite:///{abs_path}"
        
        return v
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @property
    def database_url_async(self) -> str:
        """Get async database URL."""
        url = self.DATABASE_URL
        if url.startswith("sqlite:"):
            return url.replace("sqlite:", "sqlite+aiosqlite:")
        elif url.startswith("postgresql:"):
            return url.replace("postgresql:", "postgresql+asyncpg:")
        elif url.startswith("mysql:"):
            return url.replace("mysql:", "mysql+aiomysql:")
        return url
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.DEBUG and not self.DEV_MODE
    
    @property
    def cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_credentials": self.CORS_CREDENTIALS,
            "allow_methods": self.CORS_METHODS,
            "allow_headers": self.CORS_HEADERS,
        }
    
    @property
    def jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration."""
        return {
            "secret_key": self.JWT_SECRET_KEY,
            "algorithm": self.JWT_ALGORITHM,
            "access_token_expire_minutes": self.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": self.REFRESH_TOKEN_EXPIRE_DAYS,
        }
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }


class DevelopmentSettings(Settings):
    """Development-specific settings."""
    DEBUG: bool = True
    DEV_MODE: bool = True
    DATABASE_ECHO: bool = False
    LOG_LEVEL: str = "DEBUG"
    RELOAD: bool = True
    MOCK_EXTERNAL_APIS: bool = True


class ProductionSettings(Settings):
    """Production-specific settings."""
    DEBUG: bool = False
    DEV_MODE: bool = False
    DATABASE_ECHO: bool = False
    LOG_LEVEL: str = "INFO"
    RELOAD: bool = False
    
    # Production security
    CORS_ORIGINS: List[str] = ["*"]  # Allow all origins
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 30
    
    # Production performance
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_production_secret_key(cls, v: str) -> str:
        """Ensure secret key is properly set in production."""
        if v == "your-super-secret-jwt-key-change-in-production-with-256-bits-minimum":
            raise ValueError("Must set a secure SECRET_KEY in production")
        return v


class TestSettings(Settings):
    """Test-specific settings."""
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./test_trading_agents.db"
    MOCK_EXTERNAL_APIS: bool = True
    BACKGROUND_TASKS_ENABLED: bool = False
    RATE_LIMIT_ENABLED: bool = False


@lru_cache()
def get_settings() -> Settings:
    """Get application settings with caching."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()