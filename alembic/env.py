import os
import yaml

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

def get_ed_bgs_config():
    """
    Get the application config.

    :return: yaml config object
    """
    __configfile_fd = os.open("ed-bgs_config.yaml", os.O_RDONLY)
    __configfile = os.fdopen(__configfile_fd)
    return yaml.load(__configfile, Loader=yaml.CLoader)

def get_configured_db_url():
    """
    Get the database URL from the application configuration.

    :returns: `str` - sqlalchemy DB URI
    """
    return ed_bgs_config['database']['url']

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None
import ed_bgs
ed_bgs_config = get_ed_bgs_config()
ed_bgs_db = ed_bgs.database(
  get_configured_db_url(),
  None,
)
target_metadata = ed_bgs_db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url")
    url = get_configured_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )
    connectable = ed_bgs_db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
