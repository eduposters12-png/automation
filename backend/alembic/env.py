from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

project_root = Path(__file__).resolve().parents[2]
project_root_string = str(project_root)

if project_root_string not in sys.path:
    sys.path.insert(0, project_root_string)

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.sqlite_compat import patch_sqlite_alembic_operations, sqlite_sync_url
from backend.app import models  # noqa: F401

config = context.config
database_url = get_settings().database_url
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"}
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = sqlite_sync_url(url)
    poolclass = pool.StaticPool if url.startswith("sqlite") else pool.NullPool
    if url.startswith("sqlite"):
        patch_sqlite_alembic_operations()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=poolclass
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
