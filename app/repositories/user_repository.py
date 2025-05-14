# app/repositories/user_repository.py
from sqlalchemy import select, or_  # Import or_ for OR conditions
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.models.user_model import User  # Assuming this is your User model
from app.db.schemas import user_schemas  # For type hinting if needed, e.g. UserCreate


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
        This is the method that contained the error.
        """
        # The intent is to find a user if `username_or_email` matches EITHER the email OR the username field.
        # Construct a list of conditions to be ORed.
        conditions = [
            self.model.email == username_or_email,
            self.model.username == username_or_email,
        ]

        # The original problematic line (line 40 in your traceback) was:
        # statement = select(self.model).where(Union(*conditions) if len(conditions) > 1 else conditions[0])

        # Corrected line:
        # Use sqlalchemy.or_ to combine the conditions.
        # Since `conditions` list here will always have two elements, we can directly use or_(*conditions).
        statement = select(self.model).where(or_(*conditions))

        result = await self.db_session.execute(statement)
        return result.scalar_one_or_none()

    async def create_user(self, user_in: user_schemas.UserCreatePasswordHashing) -> User:
        """
        Create a new user.
        Expects user_in to have a hashed_password field.
        """
        db_user = self.model(
            username=user_in.username,
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=user_in.hashed_password,  # Ensure password is pre-hashed
            is_active=True,  # Default to active, or based on user_in
        )
        self.db_session.add(db_user)
        await self.db_session.flush()  # Flush to get ID and other defaults before commit
        await self.db_session.refresh(db_user)
        return db_user

    async def update_user(self, user: User, user_update_data: dict) -> User:
        """
        Update an existing user.
        """
        for field, value in user_update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        await self.db_session.flush()
        await self.db_session.refresh(user)
        return user
