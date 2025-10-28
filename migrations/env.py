"""Alembic environment configuration for database migrations.

Note: This file intentionally uses os.getenv() instead of centralized config
because Alembic migrations must be standalone and work independently from
the main application. Migrations run in a special context with minimal
dependencies.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment or use Supabase URL
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv(
    "SUPABASE_URL"
)  # noqa: CONST-II-001 - Alembic migrations require standalone configuration

if DATABASE_URL:
    # Convert Supabase URL format to SQLAlchemy format if needed
    if DATABASE_URL.startswith("https://"):
        # Extract the project ID from Supabase URL
        # Format: https://xxxxx.supabase.co -> postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
        import re

        match = re.search(r"https://([^.]+)\.supabase\.co", DATABASE_URL)
        if match:
            project_id = match.group(1)
            password = os.getenv(
                "SUPABASE_SERVICE_KEY", ""
            )  # noqa: CONST-II-001 - Alembic migrations require standalone configuration
            DATABASE_URL = f"postgresql://postgres.{project_id}:{password}@aws-0-us-west-1.pooler.supabase.com:5432/postgres"

    config.set_main_option("sqlalchemy.url", DATABASE_URL)
else:
    # Fallback to constructing URL from individual components
    DB_USER = os.getenv(
        "DB_USER", "postgres"
    )  # noqa: CONST-II-001 - Alembic migrations require standalone configuration
    DB_PASS = os.getenv(
        "DB_PASS", ""
    )  # noqa: CONST-II-001 - Alembic migrations require standalone configuration
    DB_HOST = os.getenv(
        "DB_HOST", "localhost"
    )  # noqa: CONST-II-001 - Alembic migrations require standalone configuration
    DB_PORT = os.getenv(
        "DB_PORT", "5432"
    )  # noqa: CONST-II-001 - Alembic migrations require standalone configuration
    DB_NAME = os.getenv(
        "DB_NAME", "postgres"
    )  # noqa: CONST-II-001 - Alembic migrations require standalone configuration

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Import your models here for autogenerate support
# from src.agentic_rag.storage.models import Base
# target_metadata = Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with (
        connectable.connect() as connection
    ):  # noqa: CONST-III-001 - Alembic migrations use SQLAlchemy engine
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
