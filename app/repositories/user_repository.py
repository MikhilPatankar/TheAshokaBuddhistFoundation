from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List, Union
from app.db.models.user_model import User
from app.db.schemas import user_schemas
from app.repositories.base_repository import BaseRepository  # Ensure this is created


class UserRepository(
    BaseRepository[User, user_schemas.UserCreate, user_schemas.UserUpdate]
):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        statement = select(self.model).where(self.model.email == email)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_username(
        self, db: AsyncSession, *, username: str
    ) -> Optional[User]:
        statement = select(self.model).where(self.model.username == username)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email_or_username(
        self,
        db: AsyncSession,
        *,
        email: Optional[str] = None,
        username: Optional[str] = None
    ) -> Optional[User]:
        if not email and not username:
            return None

        conditions = []
        if email:
            conditions.append(self.model.email == email)
        if username:
            conditions.append(self.model.username == username)

        statement = select(self.model).where(Union(*conditions) if len(conditions) > 1 else conditions[0])  # type: ignore
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def update_user(
        self, db: AsyncSession, *, db_obj: User, obj_in: user_schemas.UserUpdate
    ) -> User:
        # Use the generic update from BaseRepository or customize if needed
        return await super().update(db=db, db_obj=db_obj, obj_in=obj_in)

    async def create_user(
        self, db: AsyncSession, *, obj_in: user_schemas.UserCreate
    ) -> User:
        # This method might seem redundant if BaseRepository.create uses UserCreate.
        # However, it allows for specific pre-create logic for users if needed.
        # For now, it can just call the parent or be directly used.
        return await super().create(db=db, obj_in=obj_in)


user_repository = UserRepository(User)
