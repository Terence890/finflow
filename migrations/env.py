"""Alembic environment configuration for PinkLedger database migrations.

This module sets up the SQLAlchemy ORM for Alembic to track database schema
changes and generate migration scripts automatically.
"""

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import create_app, db

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_engine():
    """Get SQLAlchemy engine from Flask app context."""
    app = create_app()
    return engine_from_config(
        app.config,
        prefix="SQLALCHEMY_",
        poolclass=pool.NullPool,
    )


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL, without the Engine,
    though an Engine is acceptable here as well.
    """
    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=db.metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=db.metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
