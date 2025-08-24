"""Simple authentication API."""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from src.core.database import get_db
from src.core.security import verify_password, create_tokens, get_current_user, User, Token, SECRET_KEY, ALGORITHM
from src.core.config import settings
from src.models.user import User as UserModel

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Simple user login."""
    # Get user from database
    result = db.execute(
        select(UserModel).where(UserModel.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    tokens = create_tokens(user_id=user.id, username=user.username)
    
    # Set HTTP-only cookie with access token (30분 유효기간 - JWT와 동일)
    access_expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        expires=access_expire,
        httponly=True,
        secure=False,  # 프로덕션에서는 True, 개발환경에서는 False
        samesite="lax"
    )
    
    # Set refresh token cookie (7일 유효기간 - JWT와 동일)
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=7)
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        expires=refresh_expire,
        httponly=True,
        secure=False,
        samesite="lax"
    )
    
    return tokens


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )
    
    try:
        # Verify refresh token
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        token_type: str = payload.get("type")
        
        if username is None or user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Verify user still exists
        result = db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        
        # Create new tokens
        tokens = create_tokens(user_id=user.id, username=user.username)
        
        # Set new access token cookie (30분)
        access_expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        response.set_cookie(
            key="access_token",
            value=tokens.access_token,
            expires=access_expire,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        # Keep existing refresh token or set new one (7일)
        refresh_expire = datetime.now(timezone.utc) + timedelta(days=7)
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            expires=refresh_expire,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        return tokens
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing cookies."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=False,
        samesite="lax"
    )
    response.delete_cookie(
        key="refresh_token", 
        httponly=True,
        secure=False,
        samesite="lax"
    )
    return {"message": "Successfully logged out"}