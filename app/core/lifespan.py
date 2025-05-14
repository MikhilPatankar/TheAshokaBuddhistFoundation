from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.database import async_engine, redis_pool
import redis.asyncio

# from app.tasks.celery_app import celery_app # If you want to control Celery from here (optional)
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup: Connecting to database and Redis...")
    try:
        # Test DB connection (optional, but good for early failure detection)
        async with async_engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: None)  # Minimal check
        logger.info("Database connection successful.")

        # Test Redis connection
        redis_client = redis.asyncio.Redis(connection_pool=redis_pool)
        await redis_client.ping()
        logger.info("Redis connection successful.")
        await redis_client.close()

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # Depending on severity, you might want to raise the error to stop FastAPI
        # Or proceed with caution if some services can run without all dependencies
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("Application shutdown: Disposing database engine and Redis pool...")
    await async_engine.dispose()
    await redis_pool.disconnect()
    logger.info("Resources disposed.")
