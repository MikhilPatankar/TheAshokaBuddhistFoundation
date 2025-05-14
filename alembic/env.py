# In alembic/env.py, near the top:
import asyncio  # For run_migrations_online with async engine
from sqlalchemy.ext.asyncio import AsyncEngine  # For type hint
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

# Import your app's Base model and settings
from app.db.base_model import Base  # Adjust path as needed
from app.core.config import settings as app_settings  # Your app settings

config = context.config

# This is the crucial part: Set the sqlalchemy.url from your app_settings
# This will override the one in alembic.ini
config.set_main_option(
    "sqlalchemy.url", str(app_settings.DATABASE_URL)
)  # Ensure it's a string

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    # ... (rest of the function remains mostly the same)
    """
    # Use settings.DATABASE_URL for offline mode
    url = app_settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    # ... (rest of the function)


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Create an async engine from your app settings
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable: AsyncEngine = create_async_engine(
        str(app_settings.DATABASE_URL),  # Ensure it's a string
        poolclass=pool.NullPool,  # Use NullPool for Alembic operations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()  # Dispose of the engine


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Run the async function using asyncio.run()
    asyncio.run(run_migrations_online())
