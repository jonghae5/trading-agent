"""Common Pydantic src.schemas used across the API."""

from typing import Generic, TypeVar, Optional, Any, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: bool = True
    status_code: int
    message: str
    detail: Optional[str] = None
    path: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T]
    total: int
    page: int = 1
    per_page: int = 50
    pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int = 1,
        per_page: int = 50
    ) -> "PaginatedResponse[T]":
        """Create paginated response."""
        pages = (total + per_page - 1) // per_page
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: float
    database: Dict[str, Any]
    version: str
    environment: str


class MetricsResponse(BaseModel):
    """Metrics response."""
    requests_total: int
    active_analysis_sessions: int
    database_pool_size: int
    memory_usage_mb: float


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    field: str
    message: str
    invalid_value: Optional[Any] = None


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""
    errors: List[ValidationErrorDetail]