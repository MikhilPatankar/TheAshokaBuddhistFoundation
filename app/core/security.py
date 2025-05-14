from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import database, schemas as db_schemas  # renamed to avoid conflict
from app.db.models.user_model import User as UserModel  # renamed to avoid conflict

# from app.repositories.user_repository import user_repository # Circular dependency risk, get user directly here

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Scheme for API documentation and dependency injection if using header-based tokens for APIs
oauth2_scheme_api = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})  # Add token type
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode.update({"exp": expire, "type": "refresh"})  # Add token type
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def get_user_by_id_for_auth(
    db: AsyncSession, user_id: int
) -> Optional[UserModel]:
    # Directly query user to avoid circular imports with repository/service
    from sqlalchemy.future import select  # For SQLAlchemy 2.0 style

    statement = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_username_for_auth(
    db: AsyncSession, username: str
) -> Optional[UserModel]:
    from sqlalchemy.future import select

    statement = select(UserModel).where(UserModel.username == username)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_current_user_from_cookie_web(
    request: Request, db: AsyncSession = Depends(database.get_async_db)
) -> Optional[UserModel]:
    token = request.cookies.get("access_token")
    if not token:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials from cookie",
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "access":  # Ensure it's an access token
            return None  # Or raise exception

        username: Optional[str] = payload.get("sub")
        user_id: Optional[int] = payload.get("user_id")

        if username is None or user_id is None:
            return None  # Or raise credentials_exception if strict

        # Fetch user by ID for better performance and consistency
        user = await get_user_by_id_for_auth(db, user_id=user_id)

        if user is None or user.username != username:  # Additional check
            return None  # Or raise credentials_exception if strict
        if not user.is_active:
            return (
                None  # Or raise HTTPException(status_code=400, detail="Inactive user")
            )
        return user
    except JWTError:
        return None  # Invalid token, treat as not logged in for web pages
    except Exception:
        return None


async def get_current_active_user_web(
    current_user: Optional[UserModel] = Depends(get_current_user_from_cookie_web),
) -> UserModel:
    if not current_user:
        # This dependency should be used on routes that REQUIRE authentication
        # Redirecting from here is tricky, better to handle in the route
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    if (
        not current_user.is_active
    ):  # Should have been checked in get_current_user_from_cookie_web too
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        samesite="lax",  # Consider "strict"
        secure=settings.ENVIRONMENT != "development",  # True in production
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth",  # Refresh token usually only sent to refresh endpoint
        samesite="lax",
        secure=settings.ENVIRONMENT != "development",
    )


def clear_auth_cookies(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        samesite="lax",
        secure=settings.ENVIRONMENT != "development",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        samesite="lax",
        secure=settings.ENVIRONMENT != "development",
    )
