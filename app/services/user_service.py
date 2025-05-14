# app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import Optional  # <--- Added this import

from app.db.schemas import user_schemas
from app.repositories.user_repository import UserRepository
from app.core.security import get_password_hash  # Ensure this utility exists and is imported
from app.db.models.user_model import User  # For return type hint
import logging

logger = logging.getLogger(__name__)


class UserService:
    async def create_user(
        self, db_session: AsyncSession, *, user_in: user_schemas.UserCreate
    ) -> User:
        """
        Handles the business logic for creating a new user.
        - Checks for existing username or email.
        - Hashes the password.
        - Calls the repository to save the user.
        """
        user_repo = UserRepository(db_session=db_session)

        # Check if username already exists
        existing_user_by_username = await user_repo.get_by_username(username=user_in.username)
        if existing_user_by_username:
            logger.warning(f"Attempt to register existing username: {user_in.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered.",
            )

        # Check if email already exists
        existing_user_by_email = await user_repo.get_by_email(email=user_in.email)
        if existing_user_by_email:
            logger.warning(f"Attempt to register existing email: {user_in.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered.",
            )

        hashed_password = get_password_hash(user_in.password)

        # Prepare data for repository, using the new schema
        user_create_internal = user_schemas.UserCreatePasswordHashing(
            username=user_in.username,
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=hashed_password,
            # is_active and is_superuser will use defaults from UserCreatePasswordHashing
            # (True and False respectively) unless UserCreate schema also includes them.
        )

        logger.info(f"Creating new user: {user_in.username} ({user_in.email})")
        new_user = await user_repo.create_user(user_in=user_create_internal)
        logger.info(f"User {new_user.username} created successfully with ID {new_user.id}.")

        # Here you could dispatch an event or task, e.g., send a welcome email
        # from app.tasks.email_tasks import send_registration_email_task
        # send_registration_email_task.delay(new_user.email, new_user.username)

        return new_user

    async def get_user_by_id(self, db_session: AsyncSession, user_id: int) -> Optional[User]:
        user_repo = UserRepository(db_session=db_session)
        return await user_repo.get_by_id(user_id)

    # Add other user-related service methods here (update, delete, get_by_email, etc.)


user_service = UserService()
