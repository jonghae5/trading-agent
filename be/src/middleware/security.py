"""Security middleware for HTTP security headers."""

import logging
from typing import Dict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.security import SecurityHeaders

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(
        self,
        app,
        custom_headers: Dict[str, str] = None,
        skip_paths: list[str] = None
    ):
        super().__init__(app)
        self.custom_headers = custom_headers or {}
        self.skip_paths = skip_paths or []
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        try:
            response = await call_next(request)
            
            # Skip for certain paths if needed
            if request.url.path not in self.skip_paths:
                # Add default security headers
                try:
                    security_headers = SecurityHeaders.get_security_headers()
                    
                    for header, value in security_headers.items():
                        if value:  # Only add non-empty values
                            response.headers[header] = value
                    
                    # Add custom headers
                    for header, value in self.custom_headers.items():
                        if value:  # Only add non-empty values
                            response.headers[header] = value
                    
                except Exception as e:
                    logger.warning(f"Failed to add security headers: {e}")
            
            return response
            
        except Exception as e:
            logger.error(f"SecurityHeadersMiddleware error: {e}")
            # Return response without security headers if there's an error
            return await call_next(request)
    
    def _is_allowed_origin(self, origin: str, request: Request) -> bool:
        """Check if origin is allowed for CORS."""
        # Allow all origins - no restrictions
        _ = origin  # Suppress unused parameter warning
        _ = request  # Suppress unused parameter warning
        return True