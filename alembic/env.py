# alembic/env.py

from __future__ import annotations

import os
import pathlib
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# --- Try to load DATABASE_URL from environment first ---
DATABASE_URL = os.getenv("DATABASE_URL")

# --- If not found, load .env from project root ---
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
env_path = BASE_DIR / ".env"
if not DATABASE_URL and env_path.exists():
    load_dotenv(env_path)
    DATABASE_URL = os.getenv("DATABASE_URL")

# --- Validate DATABASE_URL ---
if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL is missing. Set it in env vars or .env file.")

# --- Import models ---
from app.database import Base
import app.models.user
import app.models.calculation

# --- Alembic config ---
config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# --- Metadata ---
target_metadata = Base.metadata


def _is_sqlite(url: str) -> bool:
    return url.strip().lower().startswith("sqlite")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=_is_sqlite(url),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=_is_sqlite(DATABASE_URL),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
