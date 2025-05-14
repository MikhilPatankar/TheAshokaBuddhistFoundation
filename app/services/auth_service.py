from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Request, Response
from app.db.schemas import user_schemas, token_schemas
from app.repositories.user_repository import user_repository
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    clear_auth_cookies,
    get_password_hash,
)
from app.db.models.user_model import User
from app.services.user_service import user_service  # For user creation
from app.core.config import settings


class AuthService:
    async def login_web(
        self,
        db: AsyncSession,
        response: Response,
        *,
        form_data: user_schemas.UserLoginSchema
    ) -> User:
        user = await user_repository.get_by_email_or_username(
            db, email=form_data.username_or_email, username=form_data.username_or_email
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password.",
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
            )

        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username, "user_id": user.id}
        )

        set_auth_cookies(response, access_token, refresh_token)

        # TODO: Update last login time for user (optional)
        # user.last_login = datetime.now(timezone.utc)
        # await db.commit()
        # await db.refresh(user)

        return user

    async def register_web(
        self, db: AsyncSession, *, user_in: user_schemas.UserCreate
    ) -> User:
        # This now directly calls user_service.create_user which handles checks and hashing
        try:
            new_user = await user_service.create_user(db, user_in=user_in)
            return new_user
        except HTTPException as e:  # Propagate HTTPExceptions from user_service
            raise e
        except Exception as e:  # Catch other unexpected errors
            # Log the error
            # logger.error(f"Unexpected error during registration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during registration.",
            )

    async def logout_web(self, response: Response):
        clear_auth_cookies(response)
        return {"message": "Successfully logged out"}

    async def refresh_access_token_web(
        self, request: Request, response: Response, db: AsyncSession
    ) -> token_schemas.Token:
        refresh_token_from_cookie = request.cookies.get("refresh_token")
        if not refresh_token_from_cookie:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
            )

        try:
            from jose import jwt, JWTError  # Local import for clarity

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

            user = await user_repository.get(db, id=user_id)  # Get user by ID
            if not user or user.username != username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or token mismatch",
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="User is inactive"
                )

            new_access_token = create_access_token(
                data={"sub": user.username, "user_id": user.id}
            )
            # Optionally, issue a new refresh token (for refresh token rotation)
            new_refresh_token = create_refresh_token(
                data={"sub": user.username, "user_id": user.id}
            )

            set_auth_cookies(
                response, new_access_token, new_refresh_token
            )  # Update cookies

            return token_schemas.Token(
                access_token=new_access_token, refresh_token=new_refresh_token
            )

        except JWTError:
            clear_auth_cookies(response)  # Clear cookies if refresh token is invalid
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )


auth_service_web = AuthService()
