# app/repositories/user_repository.py
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.models.user_model import User
from app.db.schemas import user_schemas  # This will now have UserCreatePasswordHashing


class UserRepository:
    """
    Repository for User related database operations.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session: AsyncSession = db_session
        self.model = User

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a user by their ID.
        """
        statement = select(self.model).where(self.model.id == user_id)
        result = await self.db_session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by their username.
        """
        statement = select(self.model).where(self.model.username == username)
        result = await self.db_session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by their email address.
        """
        statement = select(self.model).where(self.model.email == email)
        result = await self.db_session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, username_or_email: str) -> Optional[User]:
        """
        Get a user by their email address or username.
        """
        conditions = [
            self.model.email == username_or_email,
            self.model.username == username_or_email,
        ]
        statement = select(self.model).where(or_(*conditions))
        result = await self.db_session.execute(statement)
        return result.scalar_one_or_none()

    async def create_user(self, user_in: user_schemas.UserCreatePasswordHashing) -> User:
        """
        Create a new user.
        Expects user_in to have a hashed_password field, and potentially is_active/is_superuser.
        """
        db_user = self.model(
            username=user_in.username,
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=user_in.hashed_password,
            is_active=user_in.is_active,  # Use from the schema
            is_superuser=user_in.is_superuser,  # Use from the schema
        )
        self.db_session.add(db_user)
        await self.db_session.flush()  # Flush to get ID and other defaults before commit
        await self.db_session.refresh(db_user)
        return db_user

    async def update_user(
        self, user: User, user_update_data: user_schemas.UserUpdatePasswordHashing
    ) -> User:
        """
        Update an existing user.
        Expects user_update_data to be a schema containing fields to update,
        including potentially a new hashed_password.
        """
        update_data = user_update_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        self.db_session.add(user)  # Add to session to mark as dirty if changed
        await self.db_session.flush()
        await self.db_session.refresh(user)
        return user
