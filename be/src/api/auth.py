"""Simple authentication API."""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from src.core.database import get_db
from src.core.security import verify_password, create_tokens, get_current_user, User, Token
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
    
    # Set HTTP-only cookie with access token
    # 7일 유효기간 설정 (한국 시간 기준으로 UTC로 변환)
    expire_date = datetime.now(timezone.utc) + timedelta(days=7) + timedelta(hours=9)
    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        expires=expire_date,
        httponly=True,
        secure=False,  # 개발환경에서는 False, 프로덕션에서는 True
        samesite="lax"
    )
    
    # Set refresh token cookie (30일 유효기간, 한국 시간 기준으로 UTC로 변환)
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=30) + timedelta(hours=9)
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