from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.db.schemas import user_schemas
from app.repositories.user_repository import user_repository
from app.core.security import get_password_hash
from app.db.models.user_model import User


class UserService:
    async def create_user(
        self, db: AsyncSession, *, user_in: user_schemas.UserCreate
    ) -> User:
        existing_user_email = await user_repository.get_by_email(
            db, email=user_in.email
        )
        if existing_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists.",
            )
        existing_user_username = await user_repository.get_by_username(
            db, username=user_in.username
        )
        if existing_user_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username already exists.",
            )

        hashed_password = get_password_hash(user_in.password)

        # Create a new dictionary for db_user_in to avoid modifying user_in directly
        # and to include the hashed_password
        user_create_data = user_in.model_dump(exclude={"password"})
        user_create_data["hashed_password"] = hashed_password

        # The repository expects a schema that aligns with its CreateSchemaType.
        # If UserCreate directly has hashed_password, it's simpler.
        # Let's assume UserCreate is for input, and we build the DB model fields here.
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            full_name=user_in.full_name,
            hashed_password=hashed_password,
        )

        db.add(db_user)
        await db.commit()  # Service layer handles commit
        await db.refresh(db_user)

        # TODO: Send registration confirmation email via Celery task
        # from app.tasks.email_tasks import send_registration_email_task
        # send_registration_email_task.delay(user_email=db_user.email, username=db_user.username)

        return db_user

    async def get_user(self, db: AsyncSession, user_id: int) -> User | None:
        user = await user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user


user_service = UserService()
