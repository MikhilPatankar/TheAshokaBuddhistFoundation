# app/services/auth_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Request, Response
from jose import jwt, JWTError  # Moved import to top level

from app.db.schemas import user_schemas, token_schemas
from app.repositories.user_repository import UserRepository  # Changed import
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    clear_auth_cookies,
    # get_password_hash, # Not used directly in this file anymore
)
from app.db.models.user_model import User
from app.services.user_service import user_service  # For user creation
from app.core.config import settings
# from datetime import datetime, timezone # Uncomment if you implement last_login

# import logging # Uncomment if you add logging
# logger = logging.getLogger(__name__) # Uncomment if you add logging


class AuthService:
    async def login_web(
        self, db: AsyncSession, response: Response, *, form_data: user_schemas.UserLoginSchema
    ) -> User:
        user_repo = UserRepository(db_session=db)  # Instantiate UserRepository
        user = await user_repo.get_by_email_or_username(
            username_or_email=form_data.username_or_email
        )  # Corrected call

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password.",
                headers={"WWW-Authenticate": "Bearer"},  # Good practice for 401
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

        access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
        refresh_token = create_refresh_token(data={"sub": user.username, "user_id": user.id})

        # set_auth_cookies(response, access_token, refresh_token)

        # Optional: Update last login time for user
        # user.last_login_at = datetime.now(timezone.utc) # Assuming you add this field to User model
        # db.add(user) # Add user to session if modified
        # await db.commit()
        # await db.refresh(user)
        # logger.info(f"User {user.username} logged in successfully.")

        return user

    async def register_web(self, db: AsyncSession, *, user_in: user_schemas.UserCreate) -> User:
        # This now directly calls user_service.create_user which handles checks and hashing
        # Assuming user_service.create_user correctly uses UserRepository
        try:
            new_user = await user_service.create_user(db_session=db, user_in=user_in)
            # logger.info(f"User {new_user.username} registered successfully.")
            # Potentially trigger welcome email task here if not done in user_service
            # from app.tasks.email_tasks import send_registration_email_task
            # send_registration_email_task.delay(new_user.email, new_user.username)
            return new_user
        except HTTPException as e:  # Propagate HTTPExceptions from user_service
            # logger.warning(f"Registration failed for {user_in.username}: {e.detail}")
            raise e
        except Exception as e:  # Catch other unexpected errors
            # logger.error(f"Unexpected error during registration for {user_in.username}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during registration.",
            )

    async def refresh_access_token_web(
        self,
        request: Request,
        db: AsyncSession,  # REMOVE 'response: Response'
    ) -> tuple[str, str]:  # Return new_access_token, new_refresh_token
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

            new_access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
            new_refresh_token = create_refresh_token(
                data={"sub": user.username, "user_id": user.id}
            )
            # DO NOT call set_auth_cookies here
            return new_access_token, new_refresh_token
        except JWTError:
            # DO NOT call clear_auth_cookies here
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        except HTTPException:
            raise
        except Exception:
            # DO NOT call clear_auth_cookies here
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while refreshing token.",
            )


auth_service_web = AuthService()
