from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def import_models() -> None:
    from app.modules.auth import models as auth_models  # noqa: F401
    from app.modules.customers import models as customers_models  # noqa: F401
    from app.modules.deliveries import models as deliveries_models  # noqa: F401
    from app.modules.drivers import models as drivers_models  # noqa: F401
    from app.modules.load_planning import models as load_planning_models  # noqa: F401
    from app.modules.loading import models as loading_models  # noqa: F401
    from app.modules.occurrences import models as occurrences_models  # noqa: F401
    from app.modules.orders import models as orders_models  # noqa: F401
    from app.modules.products import models as products_models  # noqa: F401
    from app.modules.status_history import models as status_history_models  # noqa: F401
    from app.modules.trucks import models as trucks_models  # noqa: F401
    from app.modules.users import models as users_models  # noqa: F401


import_models()


def get_database_url() -> str:
    return settings.database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        configuration = {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
