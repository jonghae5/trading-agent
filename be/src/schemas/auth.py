"""Authentication-related Pydantic src.schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field, validator, EmailStr, ConfigDict
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    USER = "user"
    ANALYST = "analyst"
    ADMIN = "admin"


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=1, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower().strip()


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"
    session: "SessionInfo"


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer" 
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str = Field(..., description="Valid refresh token")


class UserCreate(BaseModel):
    """User creation schema."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: UserRole = UserRole.USER
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower().strip()
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        return v


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        
        return v


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SessionInfo(BaseModel):
    """Session information schema."""
    session_id: str
    username: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    """List of user sessions."""
    sessions: List[SessionInfo]
    total: int
    active_sessions: int


class LogoutRequest(BaseModel):
    """Logout request schema."""
    session_id: Optional[str] = None  # If not provided, logout current session
    all_sessions: bool = False  # Logout from all sessions


class UserPreferenceRequest(BaseModel):
    """User preference request schema."""
    key: str = Field(..., max_length=100)
    value: str = Field(..., max_length=10000)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)


class UserPreferenceResponse(BaseModel):
    """User preference response schema."""
    key: str
    value: str
    category: Optional[str] = None
    description: Optional[str] = None
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserPreferencesResponse(BaseModel):
    """User preferences list response."""
    preferences: List[UserPreferenceResponse]
    total: int


# Forward references for circular imports
LoginResponse.model_rebuild()
SessionInfo.model_rebuild()
UserResponse.model_rebuild()