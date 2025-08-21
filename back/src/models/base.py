"""Base model class and database configuration."""

import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, func, JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, VARCHAR
import json
import pytz

# KST timezone
KST = pytz.timezone('Asia/Seoul')


class JSONType(TypeDecorator):
    """JSON type that ensures proper serialization."""
    
    impl = VARCHAR
    cache_ok = True
    
    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, default=str, ensure_ascii=False)
    
    def process_result_value(self, value: Optional[str], dialect) -> Any:
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


class Base(DeclarativeBase):
    """Base model class with common fields and utilities."""
    
    type_annotation_map = {
        dict: JSONType,
        Dict: JSONType,
        Dict[str, Any]: JSONType,
    }
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()
    
    # Common timestamp fields
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.datetime.now(KST),
        server_default=func.now()
    )
    
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.datetime.now(KST)
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime.datetime):
                # Convert to KST naive datetime for consistency
                if value.tzinfo is not None:
                    value = value.astimezone(KST).replace(tzinfo=None)
                result[column.name] = value.isoformat() if value else None
            else:
                result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Base':
        """Create model instance from dictionary."""
        # Filter out keys that don't exist as columns
        filtered_data = {
            key: value 
            for key, value in data.items() 
            if hasattr(cls, key)
        }
        return cls(**filtered_data)
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update model instance from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        attrs = []
        
        # Show primary key if exists
        for column in self.__table__.primary_key:
            value = getattr(self, column.name, None)
            if value is not None:
                attrs.append(f"{column.name}={value!r}")
        
        # Show a few other important fields
        for attr in ['username', 'ticker', 'status', 'name']:
            if hasattr(self, attr):
                value = getattr(self, attr, None)
                if value is not None:
                    attrs.append(f"{attr}={value!r}")
        
        attr_str = ", ".join(attrs[:3])  # Limit to 3 attributes
        return f"{class_name}({attr_str})"


def get_kst_now() -> datetime.datetime:
    """Get current KST time as naive datetime."""
    return datetime.datetime.now(KST).replace(tzinfo=None)


def kst_to_naive(dt: datetime.datetime) -> datetime.datetime:
    """Convert timezone-aware datetime to KST naive datetime."""
    if dt.tzinfo is None:
        return dt  # Already naive, assume it's KST
    return dt.astimezone(KST).replace(tzinfo=None)


def naive_to_kst(dt: datetime.datetime) -> datetime.datetime:
    """Convert naive datetime to KST timezone-aware datetime."""
    if dt.tzinfo is not None:
        return dt  # Already timezone-aware
    return KST.localize(dt)