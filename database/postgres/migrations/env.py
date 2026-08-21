"""
Alembic environment script.

Instead of hard-coding a database URL in alembic.ini, this pulls
`DATABASE_URL` from the same `Settings` object the app uses
(app/core/config.py), so migrations always target whatever database the
app itself is configured for — one source of truth, no drift between the
two.

Run migrations with (from the project root):
    alembic upgrade head
    alembic revision --autogenerate -m "add queries table"
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from database.postgres.session import Base

# Import model modules here as they're added, so Alembic's autogenerate can
# detect them.
from database.postgres.models import trust_score_log  # noqa: F401,E402

config = context.config
settings = get_settings()
# Escape % chars so ConfigParser does not treat URL-encoded characters
# (e.g. %40 for @) as interpolation syntax like %(key)s.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Apply migrations against a live async database connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=settings.DATABASE_URL,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
