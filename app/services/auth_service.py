# app/services/auth_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Request, Response
from jose import jwt, JWTError

from app.db.schemas import user_schemas, token_schemas
from app.repositories.user_repository import UserRepository
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    clear_auth_cookies,
)
from app.db.models.user_model import User
from app.services.user_service import user_service
from app.core.config import settings
from datetime import datetime, timezone  # <--- UNCOMMENT OR ADD THIS

import logging

logger = logging.getLogger(__name__)


class AuthService:
    async def login_web(
        self, db: AsyncSession, *, form_data: user_schemas.UserLoginSchema
    ) -> tuple[User, str, str]:  # Return: User, access_token, refresh_token
        user_repo = UserRepository(db_session=db)
        user = await user_repo.get_by_email_or_username(
            username_or_email=form_data.username_or_email
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your account is inactive.",
            )
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last_login_at timestamp
        user.last_login_at = datetime.now(timezone.utc)
        db.add(user)  # Ensure the change is tracked by the session
        # The commit will be handled by the get_async_db dependency wrapper

        access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
        refresh_token = create_refresh_token(data={"sub": user.username, "user_id": user.id})

        return user, access_token, refresh_token

    async def register_web(self, db: AsyncSession, *, user_in: user_schemas.UserCreate) -> User:
        try:
            new_user = await user_service.create_user(db_session=db, user_in=user_in)
            logger.info(f"User {new_user.username} registered successfully.")
            return new_user
        except HTTPException as e:
            logger.warning(f"Registration failed for {user_in.username}: {e.detail}")
            raise e
        except Exception as e:
            logger.error(
                f"Unexpected error during registration for {user_in.username}: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during registration.",
            )

    async def refresh_access_token_web(
        self,
        request: Request,
        db: AsyncSession,
    ) -> tuple[str, str]:
        refresh_token_from_cookie = request.cookies.get("refresh_token")
        if not refresh_token_from_cookie:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
            )
        try:
            payload = jwt.decode(
                refresh_token_from_cookie,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )
            username: str | None = payload.get("sub")
            user_id: int | None = payload.get("user_id")
            if not username or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token payload",
                )
            user_repo = UserRepository(db_session=db)
            user = await user_repo.get_by_id(user_id=user_id)
            if not user or user.username != username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or token mismatch",
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="User is inactive"
                )

            # Optionally, update last_login_at on token refresh as well,
            # as it indicates activity.
            user.last_login_at = datetime.now(timezone.utc)
            db.add(user)

            new_access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
            new_refresh_token = create_refresh_token(
                data={"sub": user.username, "user_id": user.id}
            )
            return new_access_token, new_refresh_token
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while refreshing token.",
            )


auth_service_web = AuthService()
