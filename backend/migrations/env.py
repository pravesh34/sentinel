"""Alembic env — imports app models for autogenerate. Run: cd backend && alembic revision --autogenerate -m init && alembic upgrade head"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database.session import Base
from app.models import entities  # noqa: F401
from app.config import settings

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
