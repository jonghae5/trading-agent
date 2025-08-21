"""Rate limiting middleware."""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    기준(기준점, 기준값):
    - identifier(식별자)별로 제한을 둡니다. 즉, 각 클라이언트(식별자)마다 별도의 제한이 적용됩니다.
    - identifier는 기본적으로 IP + User-Agent 해시, 또는 인증된 사용자의 username입니다.
    - max_requests: 주어진 window_seconds(초) 동안 허용되는 최대 요청 수입니다.
    - window_seconds: 제한을 적용하는 시간 창(초)입니다.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, identifier: str) -> tuple[bool, Optional[float]]:
        """
        identifier(식별자) 기준으로 요청 허용 여부를 판단합니다.
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        request_times = self.requests[identifier]

        # window_seconds 기준으로 오래된 요청 제거
        while request_times and request_times[0] <= now - self.window_seconds:
            request_times.popleft()

        # max_requests 기준으로 허용 여부 판단
        if len(request_times) < self.max_requests:
            request_times.append(now)
            return True, None

        # 제한 초과 시, 다음 요청까지 남은 시간(retry_after) 계산
        oldest_request = request_times[0]
        retry_after = oldest_request + self.window_seconds - now

        return False, max(0, retry_after)

    def get_stats(self, identifier: str) -> Dict[str, int]:
        """
        identifier 기준으로 현재 rate limit 상태 반환.
        """
        now = time.time()
        request_times = self.requests[identifier]

        # 오래된 요청 정리
        while request_times and request_times[0] <= now - self.window_seconds:
            request_times.popleft()

        return {
            "requests_made": len(request_times),
            "requests_remaining": max(0, self.max_requests - len(request_times)),
            "window_seconds": self.window_seconds,
            "max_requests": self.max_requests
        }

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    API 엔드포인트에 대한 rate limiting 미들웨어.

    기준:
    - global_rate_limiter: 모든 요청에 대해 identifier별로 적용되는 전역 제한
    - endpoint_limiters: 특정 엔드포인트에 대해 별도의 제한 적용 (예: 로그인, 분석 시작 등)
    - skip_paths: 제한을 적용하지 않는 경로
    - get_identifier_func: 식별자 추출 함수 (기본값: IP + User-Agent 해시, 또는 인증된 사용자명)
    """

    def __init__(
        self,
        app,
        global_rate_limiter: Optional[RateLimiter] = None,
        per_endpoint_limits: Optional[Dict[str, RateLimiter]] = None,
        skip_paths: Optional[list[str]] = None,
        get_identifier_func: Optional[callable] = None
    ):
        super().__init__(app)

        # 전역 기준: 60초에 60회 (IP+UserAgent 또는 username 기준)
        self.global_limiter = global_rate_limiter or RateLimiter(500, 60)

        # 엔드포인트별 기준: 예시로 로그인/분석에 별도 제한
        self.endpoint_limiters = per_endpoint_limits or {
            "/api/v1/auth/login": RateLimiter(5, 300),      # 5분에 5회 (로그인)
            "/api/v1/analysis/start": RateLimiter(10, 300), # 5분에 10회 (분석 시작)
        }

        # 제한을 적용하지 않는 경로
        self.skip_paths = skip_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

        # 식별자 추출 함수 (기본: _get_default_identifier)
        self.get_identifier = get_identifier_func or self._get_default_identifier

    async def dispatch(self, request: Request, call_next):
        """
        요청마다 rate limit 기준 적용.
        기준: 식별자별로 전역/엔드포인트별 제한
        """
        # 제한 제외 경로
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # 식별자 추출 (IP+UserAgent 또는 username)
        identifier = self.get_identifier(request)

        # 전역 기준 체크
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

        # 엔드포인트별 기준 체크
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

        # 정상 처리
        response = await call_next(request)

        # 응답에 rate limit 정보 헤더 추가 (전역 기준)
        global_stats = self.global_limiter.get_stats(identifier)
        response.headers["X-RateLimit-Limit"] = str(global_stats["max_requests"])
        response.headers["X-RateLimit-Remaining"] = str(global_stats["requests_remaining"])
        response.headers["X-RateLimit-Window"] = str(global_stats["window_seconds"])
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + global_stats["window_seconds"]))

        return response

    def _get_default_identifier(self, request: Request) -> str:
        """
        rate limit 기준이 되는 식별자 추출.
        - 인증된 사용자는 username 기준
        - 비인증 사용자는 IP + User-Agent 해시 기준
        """
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        username = getattr(request.state, "username", None)
        if username:
            return f"user:{username}"
        ua_hash = str(hash(user_agent))[:8]
        return f"ip:{client_ip}:{ua_hash}"

    def _get_client_ip(self, request: Request) -> str:
        """
        클라이언트 IP 추출 (rate limit 기준).
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        if request.client:
            return request.client.host
        return "unknown"

# Utility functions for creating rate limiters

def create_login_rate_limiter() -> RateLimiter:
    """로그인 시도 기준 rate limiter 생성 (5분에 5회)."""
    return RateLimiter(max_requests=5, window_seconds=300)

def create_analysis_rate_limiter() -> RateLimiter:
    """분석 요청 기준 rate limiter 생성 (5분에 100회)."""
    return RateLimiter(max_requests=100, window_seconds=300)

def create_api_rate_limiter() -> RateLimiter:
    """일반 API 기준 rate limiter 생성 (1분에 1000회)."""
    return RateLimiter(max_requests=1000, window_seconds=60)