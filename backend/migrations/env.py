from alembic import context
from sqlalchemy import create_engine, pool

from app.audit.models import AuditLog  # noqa: F401
from app.auth.models import AdminSession, AdminUser  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base
from app.processes.models import (  # noqa: F401
    ClientProcess,
    ConsentRecord,
    RegistrationLink,
    VideoSubmission,
)

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(
        get_settings().database_url, poolclass=pool.NullPool, hide_parameters=True
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
