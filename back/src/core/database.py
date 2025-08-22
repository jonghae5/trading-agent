"""Database configuration and session management."""

from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Generator, AsyncGenerator
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
import logging
from pathlib import Path

from src.models.base import Base
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self._initialized = False
    
    def initialize_database(self, database_url: Optional[str] = None) -> None:
        """Initialize database engine and session factory."""
        if database_url is None:
            database_url = settings.DATABASE_URL
        
        # Create sync engine
        if database_url.startswith("sqlite"):
            # SQLite specific configuration
            self.engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.DATABASE_ECHO
            )
            
            # Enable foreign key constraints for SQLite
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        else:
            # PostgreSQL/MySQL configuration
            self.engine = create_engine(
                database_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=settings.DATABASE_ECHO
            )
        
        # Create async engine
        async_url = settings.database_url_async
        if async_url.startswith("sqlite+aiosqlite"):
            self.async_engine = create_async_engine(
                async_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.DATABASE_ECHO
            )
        else:
            self.async_engine = create_async_engine(
                async_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=settings.DATABASE_ECHO
            )
        
        # Create session factories
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        self.AsyncSessionLocal = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.async_engine,
            class_=AsyncSession
        )
        
        logger.info(f"Initialized database engines: sync={database_url}, async={async_url}")
    
    def initialize(self) -> None:
        """Initialize database engine."""
        if not self.engine:
            self.initialize_database()
        
        self._initialized = True
    
    def create_tables(self) -> None:
        """Create all database tables."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session context manager."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session context manager."""
        if not self.AsyncSessionLocal:
            raise RuntimeError("Async database not initialized")
        
        session = self.AsyncSessionLocal()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_session_raw(self):
        """Get raw database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        
        return self.SessionLocal()
    
    def get_async_session_raw(self):
        """Get raw async database session."""
        if not self.AsyncSessionLocal:
            raise RuntimeError("Async database not initialized")
        
        return self.AsyncSessionLocal()
    
    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
        
        logger.info("Database connections closed")
    
    async def async_close(self) -> None:
        """Close async database connections."""
        if self.async_engine:
            await self.async_engine.dispose()
        
        logger.info("Async database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


def get_db():
    """Dependency to get database session."""
    if not db_manager.SessionLocal:
        raise RuntimeError("Database not initialized")
    
    session = db_manager.SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def get_async_db():
    """Dependency to get async database session."""
    if not db_manager.AsyncSessionLocal:
        raise RuntimeError("Async database not initialized")
    
    session = db_manager.AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def init_database() -> None:
    """Initialize database on application startup."""
    logger.info("Initializing database...")
    
    # Initialize database manager
    db_manager.initialize()
    
    # Create tables if they don't exist
    try:
        db_manager.create_tables()
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise
    
    logger.info("Database initialization completed")


def close_database() -> None:
    """Close database connections on application shutdown."""
    logger.info("Closing database connections...")
    db_manager.close()
    logger.info("Database connections closed")


def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        with db_manager.get_session() as session:
            session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


class DatabaseHealthCheck:
    """Database health check utility."""
    
    def __init__(self):
        self.last_check = None
        self.is_healthy = False
    
    def check_health(self) -> dict:
        """Perform comprehensive database health check."""
        import time
        
        start_time = time.time()
        
        try:
            # Check database connection
            connection_healthy = check_database_connection()
            
            # Calculate response time
            response_time = time.time() - start_time
            
            self.is_healthy = connection_healthy
            self.last_check = time.time()
            
            return {
                "status": "healthy" if self.is_healthy else "unhealthy",
                "connection": connection_healthy,
                "response_time_seconds": round(response_time, 3),
                "timestamp": self.last_check
            }
            
        except Exception as e:
            self.is_healthy = False
            self.last_check = time.time()
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_seconds": time.time() - start_time,
                "timestamp": self.last_check
            }


# Global health checker
health_checker = DatabaseHealthCheck()