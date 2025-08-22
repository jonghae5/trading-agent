"""Logging middleware for request/response tracking."""

import time
import uuid
import logging
import json
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Utility class for structured logging."""
    
    @staticmethod
    def log_structured(
        logger: logging.Logger,
        level: int,
        message: str,
        **kwargs
    ) -> None:
        """Log structured data as JSON."""
        log_data = {
            "message": message,
            "timestamp": time.time(),
            **kwargs
        }
        
        # Format as JSON for production, human-readable for development
        try:
            from src.core.config import settings
            if settings.is_production:
                extra_msg = json.dumps(log_data, default=str)
            else:
                extra_msg = f"{message} | {json.dumps(kwargs, default=str)}"
        except:
            extra_msg = f"{message} | {kwargs}"
        
        logger.log(level, extra_msg)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(
        self,
        app,
        logger: logging.Logger = None,
        skip_paths: list[str] = None
    ):
        super().__init__(app)
        self.logger = logger or logging.getLogger("request")
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Skip logging for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        
        # Extract client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        StructuredLogger.log_structured(
            self.logger,
            logging.INFO,
            "HTTP Request Started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            user_agent=user_agent[:100],
            query_params=dict(request.query_params) if request.query_params else None
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            StructuredLogger.log_structured(
                self.logger,
                logging.INFO,
                "HTTP Request Completed",
                request_id=request_id,
                status_code=response.status_code,
                process_time_seconds=round(process_time, 3),
                method=request.method,
                path=request.url.path
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            
            StructuredLogger.log_structured(
                self.logger,
                logging.ERROR,
                "HTTP Request Failed",
                request_id=request_id,
                error_type=e.__class__.__name__,
                error_message=str(e),
                process_time_seconds=round(process_time, 3),
                method=request.method,
                path=request.url.path
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address considering proxy headers."""
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"