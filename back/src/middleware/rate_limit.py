"""Rate limiting middleware."""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter using sliding window algorithm."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> tuple[bool, Optional[float]]:
        """
        Check if request is allowed for given identifier.
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        
        # Get request history for this identifier
        request_times = self.requests[identifier]
        
        # Remove old requests outside the window
        while request_times and request_times[0] <= now - self.window_seconds:
            request_times.popleft()
        
        # Check if under limit
        if len(request_times) < self.max_requests:
            request_times.append(now)
            return True, None
        
        # Calculate when oldest request will expire
        oldest_request = request_times[0]
        retry_after = oldest_request + self.window_seconds - now
        
        return False, max(0, retry_after)
    
    def get_stats(self, identifier: str) -> Dict[str, int]:
        """Get rate limit statistics for identifier."""
        now = time.time()
        request_times = self.requests[identifier]
        
        # Clean up old requests
        while request_times and request_times[0] <= now - self.window_seconds:
            request_times.popleft()
        
        return {
            "requests_made": len(request_times),
            "requests_remaining": max(0, self.max_requests - len(request_times)),
            "window_seconds": self.window_seconds,
            "max_requests": self.max_requests
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API endpoints."""
    
    def __init__(
        self,
        app,
        global_rate_limiter: Optional[RateLimiter] = None,
        per_endpoint_limits: Optional[Dict[str, RateLimiter]] = None,
        skip_paths: Optional[list[str]] = None,
        get_identifier_func: Optional[callable] = None
    ):
        super().__init__(app)
        
        # Default global rate limiter (60 requests per minute)
        self.global_limiter = global_rate_limiter or RateLimiter(60, 60)
        
        # Per-endpoint rate limiters
        self.endpoint_limiters = per_endpoint_limits or {
            "/api/v1/auth/login": RateLimiter(5, 300),  # 5 login attempts per 5 minutes
            "/api/v1/analysis/start": RateLimiter(10, 300),  # 10 analyses per 5 minutes
        }
        
        # Paths to skip rate limiting
        self.skip_paths = skip_paths or [
            "/health",
            "/metrics", 
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        
        # Function to get identifier (default uses IP)
        self.get_identifier = get_identifier_func or self._get_default_identifier
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests."""
        # Skip rate limiting for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Get client identifier
        identifier = self.get_identifier(request)
        
        # Check global rate limit
        allowed, retry_after = self.global_limiter.is_allowed(identifier)
        
        if not allowed:
            logger.warning(
                f"Global rate limit exceeded for {identifier} - "
                f"retry after {retry_after:.1f}s"
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={
                    "Retry-After": str(int(retry_after or 60)),
                    "X-RateLimit-Limit": str(self.global_limiter.max_requests),
                    "X-RateLimit-Window": str(self.global_limiter.window_seconds),
                }
            )
        
        # Check endpoint-specific rate limit
        endpoint_path = request.url.path
        if endpoint_path in self.endpoint_limiters:
            endpoint_limiter = self.endpoint_limiters[endpoint_path]
            allowed, retry_after = endpoint_limiter.is_allowed(identifier)
            
            if not allowed:
                logger.warning(
                    f"Endpoint rate limit exceeded for {identifier} on {endpoint_path} - "
                    f"retry after {retry_after:.1f}s"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests to {endpoint_path}",
                    headers={
                        "Retry-After": str(int(retry_after or 60)),
                        "X-RateLimit-Limit": str(endpoint_limiter.max_requests),
                        "X-RateLimit-Window": str(endpoint_limiter.window_seconds),
                    }
                )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        global_stats = self.global_limiter.get_stats(identifier)
        
        response.headers["X-RateLimit-Limit"] = str(global_stats["max_requests"])
        response.headers["X-RateLimit-Remaining"] = str(global_stats["requests_remaining"])
        response.headers["X-RateLimit-Window"] = str(global_stats["window_seconds"])
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + global_stats["window_seconds"]))
        
        return response
    
    def _get_default_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting (IP + User-Agent hash)."""
        # Start with IP address
        client_ip = self._get_client_ip(request)
        
        # Add user agent hash for more granular limiting
        user_agent = request.headers.get("user-agent", "")
        
        # For authenticated users, use username instead of IP
        # This would be set by authentication middleware
        username = getattr(request.state, "username", None)
        if username:
            return f"user:{username}"
        
        # Use IP + simplified user agent hash
        ua_hash = str(hash(user_agent))[:8]
        return f"ip:{client_ip}:{ua_hash}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        # Check forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to connection IP
        if request.client:
            return request.client.host
        
        return "unknown"


# Utility functions for creating rate limiters

def create_login_rate_limiter() -> RateLimiter:
    """Create rate limiter for login attempts."""
    return RateLimiter(max_requests=5, window_seconds=300)  # 5 attempts per 5 minutes


def create_analysis_rate_limiter() -> RateLimiter:
    """Create rate limiter for analysis requests."""
    return RateLimiter(max_requests=100, window_seconds=300)  # 10 analyses per 5 minutes


def create_api_rate_limiter() -> RateLimiter:
    """Create general API rate limiter."""
    return RateLimiter(max_requests=1000, window_seconds=60)  # 1000 requests per minute