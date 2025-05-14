from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase  # Import DeclarativeBase
from app.core.config import settings
import redis.asyncio as aioredis  # For async Redis
from typing import AsyncGenerator


# Define the SQLAlchemy declarative base
class Base(DeclarativeBase):
    pass


# Async SQLAlchemy Engine
async_engine = create_async_engine(
    str(settings.DATABASE_URL),  # Ensure DATABASE_URL is a string
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=False,  # Set to True for SQL logging in development
    pool_pre_ping=True,  # Helps with stale connections
)

# Async Session Factory
AsyncSessionFactory = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Important for async usage
    autoflush=False,
    autocommit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an async database session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            # await session.commit() # Not committing here, services should handle transactions
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Async Redis Connection Pool
redis_pool = aioredis.ConnectionPool.from_url(
    str(settings.REDIS_URL), decode_responses=True
)


async def get_redis_client() -> aioredis.Redis:
    """FastAPI dependency to get an async Redis client."""
    return aioredis.Redis(connection_pool=redis_pool)
